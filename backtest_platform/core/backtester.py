# backtest_platform/core/backtester.py

import pandas as pd
import numpy as np
from typing import Dict, Optional

class Backtester:
    def __init__(
        self,
        commission: Dict[str, float] = None,
        default_commission: float = 0.0,
        slippage: float = 0.0,
        use_slippage: bool = False,
        trade_time_filter: Optional[str] = None  # например, '12:00:00'
    ):
        self.commission = commission or {}
        self.default_commission = default_commission
        self.slippage = slippage
        self.use_slippage = use_slippage
        self.trade_time_filter = trade_time_filter

    def _apply_costs(self, price: float, ticker: str, is_buy: bool) -> float:
        comm = self.commission.get(ticker, self.default_commission)
        adj = (1 + comm) if is_buy else (1 - comm)
        if self.use_slippage:
            slip = self.slippage if is_buy else -self.slippage
            adj *= (1 + slip)
        return price * adj

    def _filter_by_time(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.trade_time_filter and 'TRADEDATE' in df.columns:
            if df['TRADEDATE'].dtype == 'object':
                df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
            # Предполагаем, что TRADEDATE содержит время
            df = df[df['TRADEDATE'].dt.time == pd.Timestamp(self.trade_time_filter).time()]
        return df

    def run(
        self,
        strategy,
        data_dict: Dict[str, pd.DataFrame],
        market_data: Optional[pd.DataFrame] = None,
        rvi_data: Optional[pd.DataFrame] = None,
        initial_capital: float = 100_000,
        price_col: str = 'CLOSE'
    ):
        # Фильтрация данных по времени
        filtered_data = {}
        all_dates = set()
        for ticker, df in data_dict.items():
            df = df.copy()
            if self.trade_time_filter:
                df = self._filter_by_time(df)
            filtered_data[ticker] = df
            all_dates.update(df['TRADEDATE'])

        if market_data is not None:
            market_data = self._filter_by_time(market_data)

        all_dates = sorted(all_dates)
        portfolio_values = []
        trades = []
        # Начинаем с кэша (LQDT)
        current_asset = 'LQDT'
        cash = initial_capital
        positions = {t: 0.0 for t in data_dict}

        for date in all_dates:
            # Сбор данных на дату
            daily_dfs = {}
            valid = True
            for ticker, df in filtered_data.items():
                row = df[df['TRADEDATE'] == date]
                if row.empty:
                    valid = False
                    break
                daily_dfs[ticker] = df[df['TRADEDATE'] <= date].copy()

            if not valid or len(daily_dfs) != len(data_dict):
                continue

            # RVI на текущую дату
            current_rvi = None
            if rvi_data is not None:
                rvi_row = rvi_data[rvi_data['TRADEDATE'] == date]
                if not rvi_row.empty:
                    current_rvi = rvi_row

            # Генерация сигнала
            signal = strategy.generate_signal(daily_dfs, market_data=market_data, rvi_data=current_rvi)
            selected = signal.get('selected', current_asset)

            # Смена актива
            if selected != current_asset:
                # Продажа старого
                if current_asset in positions and positions[current_asset] > 0:
                    sell_df = filtered_data[current_asset]
                    sell_row = sell_df[sell_df['TRADEDATE'] == date]
                    if not sell_row.empty:
                        sell_price = sell_row[price_col].iloc[0]
                        sell_price = self._apply_costs(sell_price, current_asset, is_buy=False)
                        cash = positions[current_asset] * sell_price
                        positions[current_asset] = 0.0
                        trades.append({'date': date, 'action': 'SELL', 'ticker': current_asset, 'price': sell_price})

                # Покупка нового
                if selected in filtered_data:
                    buy_df = filtered_data[selected]
                    buy_row = buy_df[buy_df['TRADEDATE'] == date]
                    if not buy_row.empty:
                        buy_price = buy_row[price_col].iloc[0]
                        buy_price = self._apply_costs(buy_price, selected, is_buy=True)
                        if buy_price > 0:
                            positions[selected] = cash / buy_price
                            cash = 0.0
                            trades.append({'date': date, 'action': 'BUY', 'ticker': selected, 'price': buy_price})

                current_asset = selected

            # Оценка стоимости портфеля
            current_value = cash
            for ticker, qty in positions.items():
                if qty > 0:
                    price_df = filtered_data[ticker]
                    price_row = price_df[price_df['TRADEDATE'] == date]
                    if not price_row.empty:
                        price = price_row[price_col].iloc[0]
                        current_value += qty * price
            portfolio_values.append({'date': date, 'value': current_value})

        # Расчёт метрик
        pv_df = pd.DataFrame(portfolio_values)
        if pv_df.empty:
            return {
                'portfolio_value': pv_df,
                'trades': pd.DataFrame(trades),
                'final_value': initial_capital,
                'cagr': 0.0,
                'sharpe': 0.0,
                'max_drawdown': 0.0
            }

        returns = pv_df['value'].pct_change().dropna()
        cagr = (pv_df['value'].iloc[-1] / pv_df['value'].iloc[0]) ** (252 / len(pv_df)) - 1 if len(pv_df) > 1 else 0.0
        sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() != 0 else 0.0
        dd = (pv_df['value'] / pv_df['value'].cummax() - 1).min()

        return {
            'portfolio_value': pv_df,
            'trades': pd.DataFrame(trades) if trades else pd.DataFrame(),
            'final_value': pv_df['value'].iloc[-1],
            'cagr': cagr,
            'sharpe': sharpe,
            'max_drawdown': dd
        }
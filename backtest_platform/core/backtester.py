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
            if 'TIME' in df.columns:
                df = df[df['TIME'] == self.trade_time_filter]
            else:
                # Предполагаем, что TRADEDATE содержит время
                df = df[df['TRADEDATE'].dt.time == pd.Timestamp(self.trade_time_filter).time()]
        return df

    def run(
        self,
        strategy,
        data_dict: Dict[str, pd.DataFrame],
        market_data: Optional[pd.DataFrame] = None,
        initial_capital: float = 100_000,
        price_col: str = 'CLOSE'
    ):
        # Фильтрация по времени (например, 12:00)
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
        current_asset = list(data_dict.keys())[0]  # начальное — можно заменить на LQDT
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

            # Сигнал
            signal = strategy.generate_signal(daily_dfs, market_data=market_data)
            selected = signal.get('selected', current_asset)

            if selected != current_asset:
                # Продажа текущего
                if current_asset in positions and positions[current_asset] > 0:
                    sell_price = filtered_data[current_asset]
                    sell_price = sell_price[sell_price['TRADEDATE'] == date][price_col].iloc[0]
                    sell_price = self._apply_costs(sell_price, current_asset, is_buy=False)
                    cash = positions[current_asset] * sell_price
                    positions[current_asset] = 0.0
                    trades.append({'date': date, 'action': 'SELL', 'ticker': current_asset, 'price': sell_price})

                # Покупка нового
                if selected in filtered_data:
                    buy_price = filtered_data[selected]
                    buy_price = buy_price[buy_price['TRADEDATE'] == date][price_col].iloc[0]
                    buy_price = self._apply_costs(buy_price, selected, is_buy=True)
                    positions[selected] = cash / buy_price
                    cash = 0.0
                    trades.append({'date': date, 'action': 'BUY', 'ticker': selected, 'price': buy_price})

                current_asset = selected

            # Оценка портфеля
            current_value = cash
            for ticker, qty in positions.items():
                if qty > 0:
                    price = filtered_data[ticker]
                    price = price[price['TRADEDATE'] == date][price_col].iloc[0]
                    current_value += qty * price
            portfolio_values.append({'date': date, 'value': current_value})

        # Метрики
        pv_df = pd.DataFrame(portfolio_values)
        if pv_df.empty:
            return {'final_value': initial_capital, 'portfolio_value': pv_df, 'trades': pd.DataFrame(trades)}

        returns = pv_df['value'].pct_change().dropna()
        cagr = (pv_df['value'].iloc[-1] / pv_df['value'].iloc[0]) ** (252 / len(pv_df)) - 1
        sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() != 0 else 0
        dd = (pv_df['value'] / pv_df['value'].cummax() - 1).min()

        return {
            'portfolio_value': pv_df,
            'trades': pd.DataFrame(trades),
            'final_value': pv_df['value'].iloc[-1],
            'cagr': cagr,
            'sharpe': sharpe,
            'max_drawdown': dd
        }

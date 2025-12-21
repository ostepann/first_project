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
        trade_time_filter: Optional[str] = None
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
            if df['TRADEDATE'].dt.time.dtype == 'object':
                df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
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
        # Сбор всех дат
        all_dates = set()
        for df in data_dict.values():
            all_dates.update(df['TRADEDATE'])
        all_dates = sorted(all_dates)
        
        # Фильтрация данных по времени (например, 12:00)
        filtered_data = {}
        for ticker, df in data_dict.items():
            df = df.copy()
            if self.trade_time_filter:
                df = self._filter_by_time(df)
            filtered_data[ticker] = df

        portfolio_values = []
        trades = []
        # Начинаем с кэша
        current_asset = 'LQDT'
        cash = initial_capital
        positions = {t: 0.0 for t in data_dict}

        print(f"\n[BACKTESTER] Начало бэктеста. Даты: {len(all_dates)} шт.")
        print(f"[BACKTESTER] Начальный капитал: {cash:.2f}, актив: {current_asset}")

        for date in all_dates:
            # Сбор данных на дату
            daily_dfs = {}
            valid = True
            rvi_on_date = None

            for ticker, df in filtered_data.items():
                row = df[df['TRADEDATE'] == date]
                if row.empty:
                    valid = False
                    break
                # Все данные до текущей даты
                daily_dfs[ticker] = df[df['TRADEDATE'] <= date].copy()

            if not valid:
                print(f"[DEBUG] Пропущена дата {date} (не все активы доступны)")
                continue

            # RVI на дату
            if rvi_data is not None:
                rvi_row = rvi_data[rvi_data['TRADEDATE'] == date]
                if not rvi_row.empty:
                    rvi_on_date = rvi_row

            # Генерация сигнала
            signal = strategy.generate_signal(daily_dfs, market_data=market_data, rvi_data=rvi_on_date)
            selected = signal.get('selected', current_asset)

            print(f"\n[DEBUG] Дата: {date}")
            print(f"  Текущий актив: {current_asset}, Выбранный: {selected}")
            print(f"  Данные: {[f'{t}({len(daily_dfs[t])})' for t in daily_dfs]}")

            # Смена актива
            if selected != current_asset:
                print(f"  ⚠️ СМЕНА АКТИВА: {current_asset} → {selected}")

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
                        print(f"    Продано {current_asset} по {sell_price:.2f}, кэш: {cash:.2f}")

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
                            print(f"    Куплено {positions[selected]:.4f} шт {selected} по {buy_price:.2f}")
                        else:
                            print(f"    ❌ Ошибка: цена покупки <= 0")
                    else:
                        print(f"    ❌ Нет данных для покупки {selected} на {date}")
                else:
                    print(f"    ❌ Актив {selected} не найден в данных")

                current_asset = selected

            # Оценка портфеля
            current_value = cash
            for ticker, qty in positions.items():
                if qty > 0:
                    price_df = filtered_data[ticker]
                    price_row = price_df[price_df['TRADEDATE'] == date]
                    if not price_row.empty:
                        price = price_row[price_col].iloc[0]
                        current_value += qty * price
            portfolio_values.append({'date': date, 'value': current_value})
            print(f"  💹 Стоимость портфеля: {current_value:.2f}")

        # Расчёт метрик
        pv_df = pd.DataFrame(portfolio_values)
        if pv_df.empty:
            return {'final_value': initial_capital, 'portfolio_value': pv_df, 'trades': pd.DataFrame(trades)}

        returns = pv_df['value'].pct_change().dropna()
        cagr = (pv_df['value'].iloc[-1] / pv_df['value'].iloc[0]) ** (252 / len(pv_df)) - 1 if len(pv_df) > 1 else 0.0
        sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() != 0 else 0.0
        dd = (pv_df['value'] / pv_df['value'].cummax() - 1).min()

        print(f"\n[BACKTESTER] Итоги:")
        print(f"  Финальная стоимость: {pv_df['value'].iloc[-1]:.2f}")
        print(f"  CAGR: {cagr:.2%}, Sharpe: {sharpe:.2f}, Max DD: {dd:.2%}")
        print(f"  Сделок: {len(trades)}")

        return {
            'portfolio_value': pv_df,
            'trades': pd.DataFrame(trades) if trades else pd.DataFrame(),
            'final_value': pv_df['value'].iloc[-1],
            'cagr': cagr,
            'sharpe': sharpe,
            'max_drawdown': dd
        }
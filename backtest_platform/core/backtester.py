# backtest_platform\core\backtester.py

"""
Модуль бэктестера для оценки торговых стратегий на исторических данных.

Версия: 1.3.0
Изменения:
- Возврат диагностического поля used_market_vol_window как МАКСИМАЛЬНОГО значения за период (а не последнего)
- Это значение напрямую зависит от rvi_low_multiplier: max_window = market_vol_window * rvi_low_multiplier
- Устранена проблема с постоянным значением 15 для всех комбинаций параметров
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Union

# Метаданные модуля
__version__ = "1.3.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-08"

class Backtester:
    """
    Класс для проведения бэктеста торговых стратегий на исторических данных.
    
    Поддерживает:
    - Расчёт комиссий и проскальзывания
    - Фильтрацию по времени торговли (для интрадей-данных)
    - Сбор диагностической информации из сигналов стратегии
    - Расчёт ключевых метрик эффективности (CAGR, Sharpe, Max Drawdown)
    """
    
    def __init__(
        self,
        commission: Union[Dict[str, float], float] = 0.0,
        default_commission: float = 0.0,
        slippage: Union[Dict[str, float], float] = 0.0,
        use_slippage: bool = False,
        trade_time_filter: Optional[str] = None
    ):
        """
        Инициализация бэктестера.
        
        Аргументы:
            commission: комиссия в процентах (словарь по тикерам или единое значение)
            default_commission: комиссия по умолчанию для тикеров, не указанных в словаре
            slippage: проскальзывание в базисных пунктах (словарь или единое значение)
            use_slippage: флаг применения проскальзывания
            trade_time_filter: строка времени в формате 'HH:MM:SS' для фильтрации интрадей-данных
        """
        self.commission = commission
        self.default_commission = default_commission
        self.slippage = slippage
        self.use_slippage = use_slippage
        self.trade_time_filter = trade_time_filter

    def _get_commission(self, ticker: str) -> float:
        """Возвращает комиссию в долях (не %!)."""
        if isinstance(self.commission, dict):
            return self.commission.get(ticker, self.default_commission) / 100.0
        else:
            return self.commission / 100.0

    def _get_slippage(self, ticker: str) -> float:
        """Возвращает проскальзывание в долях (не bps!)."""
        if not self.use_slippage:
            return 0.0
        if isinstance(self.slippage, dict):
            return self.slippage.get(ticker, 0.0) / 10_000.0
        else:
            return self.slippage / 10_000.0

    def _apply_costs(self, price: float, ticker: str, is_buy: bool) -> float:
        """
        Применяет комиссию и проскальзывание к цене.
        
        Аргументы:
            price: цена актива
            ticker: тикер актива
            is_buy: True для покупки, False для продажи
        
        Возвращает:
            Скорректированную цену с учётом издержек
        """
        comm_frac = self._get_commission(ticker)
        slip_frac = self._get_slippage(ticker)
        total_cost = comm_frac + slip_frac

        if is_buy:
            return price * (1 + total_cost)
        else:
            return price * (1 - total_cost)

    def _filter_by_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Фильтрация данных по времени торговли.
        
        Использует прямое сравнение компонентов времени (hour/minute/second) с подавлением
        ошибок типизации через # type: ignore — это известная проблема типизации в pandas,
        но код корректно работает при выполнении.
        
        Аргументы:
            df: DataFrame с колонкой 'TRADEDATE' типа datetime64
        
        Возвращает:
            Отфильтрованный DataFrame с записями только в указанное время
        """
        if self.trade_time_filter and 'TRADEDATE' in df.columns:
            if df['TRADEDATE'].dtype == 'object':
                df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
            
            # Парсим целевое время
            target_parts = self.trade_time_filter.split(':')
            target_hour = int(target_parts[0])
            target_minute = int(target_parts[1])
            target_second = int(target_parts[2]) if len(target_parts) > 2 else 0
            
            # Фильтрация через прямое сравнение компонентов времени
            # ⚠️ # type: ignore требуется из-за известной проблемы типизации в pandas stubs
            mask = (
                (df['TRADEDATE'].dt.hour == target_hour) &  # type: ignore
                (df['TRADEDATE'].dt.minute == target_minute) &  # type: ignore
                (df['TRADEDATE'].dt.second == target_second)  # type: ignore
            )
            df = df[mask]
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
        """
        Запуск бэктеста торговой стратегии на исторических данных.
        
        Аргументы:
            strategy: экземпляр стратегии с методом generate_signal()
            data_dict: словарь данных по активам {тикер: DataFrame}
            market_data: данные рыночного индекса (опционально)
            rvi_data: данные индекса волатильности RVI (опционально)
            initial_capital: начальный капитал в рублях
            price_col: колонка с ценой для расчётов ('CLOSE' по умолчанию)
        
        Возвращает:
            Словарь с результатами:
            - 'portfolio_value': DataFrame с динамикой портфеля
            - 'trades': DataFrame со всеми сделками
            - 'final_value': финальная стоимость портфеля
            - 'cagr': годовая доходность (252 торговых дня)
            - 'sharpe': коэффициент Шарпа (годовой)
            - 'max_drawdown': максимальная просадка
            - 'used_market_vol_window': МАКСИМАЛЬНОЕ использованное окно за период (ключевой показатель влияния rvi_low_multiplier)
            - 'rvi_low_days': количество дней с низким RVI (уровень 'low')
        """
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
        current_asset = 'LQDT'
        cash = initial_capital
        positions = {t: 0.0 for t in data_dict}
        
        # 🔑 КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: собираем МАКСИМАЛЬНОЕ окно за период
        max_vol_window = None
        rvi_low_days = 0

        for date in all_dates:
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

            current_rvi = None
            if rvi_data is not None:
                rvi_row = rvi_data[rvi_data['TRADEDATE'] == date]
                if not rvi_row.empty:
                    current_rvi = rvi_row

            signal = strategy.generate_signal(daily_dfs, market_data=market_data, rvi_data=current_rvi)
            selected = signal.get('selected', current_asset)
            
            # 🔑 СОБИРАЕМ МАКСИМАЛЬНОЕ ОКНО ЗА ПЕРИОД
            used_window = signal.get('used_market_vol_window')
            if used_window is not None:
                if max_vol_window is None or used_window > max_vol_window:
                    max_vol_window = used_window
            
            # Считаем дни с низким RVI
            if signal.get('rvi_level') == 'low':
                rvi_low_days += 1

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

            current_value = cash
            for ticker, qty in positions.items():
                if qty > 0:
                    price_df = filtered_data[ticker]
                    price_row = price_df[price_df['TRADEDATE'] == date]
                    if not price_row.empty:
                        price = price_row[price_col].iloc[0]
                        current_value += qty * price
            portfolio_values.append({'date': date, 'value': current_value})

        pv_df = pd.DataFrame(portfolio_values)
        if pv_df.empty:
            return {
                'portfolio_value': pv_df,
                'trades': pd.DataFrame(trades),
                'final_value': initial_capital,
                'cagr': 0.0,
                'sharpe': 0.0,
                'max_drawdown': 0.0,
                # 🔑 КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: возвращаем МАКСИМАЛЬНОЕ окно
                'used_market_vol_window': None,
                'rvi_low_days': rvi_low_days
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
            'max_drawdown': dd,
            # 🔑 КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: возвращаем МАКСИМАЛЬНОЕ окно за период
            'used_market_vol_window': max_vol_window,
            'rvi_low_days': rvi_low_days
        }
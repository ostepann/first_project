# backtest_platform/validation/validation_strategy.py

# === ФИКС ПУТИ: гарантируем доступ к core ===
import os
import sys

# Путь к backtest_platform (родительская папка текущей)
_backtest_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backtest_root not in sys.path:
    sys.path.insert(0, _backtest_root)

from core.base_strategy import BaseStrategy
import pandas as pd

class ValidationDualMomentumStrategy(BaseStrategy):
    """
    Стратегия БЕЗ адаптации окон и БЕЗ фильтра по волатильности — только для валидации.
    Выбирает актив с наибольшим momentum.
    """
    def __init__(self, lookback_period=2, risk_free_ticker='LQDT'):
        self.lookback = lookback_period
        self.risk_free = risk_free_ticker

    def generate_signal(self, data_dict, market_data=None, rvi_data=None, **kwargs):
        best_score = -1e10
        best_ticker = self.risk_free

        for ticker, df in data_dict.items():
            if ticker == self.risk_free:
                continue
            # Пропускаем, если данных меньше lookback
            if len(df) < self.lookback:
                continue

            # Расчёт momentum: (текущая цена - цена lookback дней назад) / цена lookback дней назад
            lookback_price = df['CLOSE'].iloc[-self.lookback]
            current_price = df['CLOSE'].iloc[-1]
            momentum = (current_price - lookback_price) / lookback_price

            # Используем momentum напрямую (без волатильности)
            score = momentum

            if score > best_score:
                best_score = score
                best_ticker = ticker

        return {'selected': best_ticker}
# backtest_platform/validation/test01/test01_validation_strategy.py

import os
import sys
_backtest_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backtest_root not in sys.path:
    sys.path.insert(0, _backtest_root)

from core.base_strategy import BaseStrategy
import pandas as pd

class Test01ValidationStrategy(BaseStrategy):
    """Тест 1: выбор самого прибыльного актива (без волатильности)."""
    def __init__(self, lookback_period=2, risk_free_ticker='LQDT'):
        self.lookback = lookback_period
        self.risk_free = risk_free_ticker

    def generate_signal(self, data_dict, **kwargs):
        best_score = -1e10
        best_ticker = self.risk_free

        for ticker, df in data_dict.items():
            if ticker == self.risk_free:
                continue
            if len(df) < self.lookback:
                continue

            lookback_price = df['CLOSE'].iloc[-self.lookback]
            current_price = df['CLOSE'].iloc[-1]
            momentum = (current_price - lookback_price) / lookback_price

            if momentum > best_score:
                best_score = momentum
                best_ticker = ticker

        return {'selected': best_ticker}
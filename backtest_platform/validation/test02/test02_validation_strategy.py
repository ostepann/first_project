# backtest_platform/validation/test02/test02_validation_strategy.py

import os
import sys
_backtest_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backtest_root not in sys.path:
    sys.path.insert(0, _backtest_root)

from core.base_strategy import BaseStrategy
from indicators.volatility import rolling_volatility
import pandas as pd

class Test02ValidationStrategy(BaseStrategy):
    """Тест 2: проверка фильтра по волатильности."""
    def __init__(self, lookback_period=5, vol_window=10, max_vol_threshold=0.5):
        self.lookback = lookback_period
        self.vol_window = vol_window
        self.max_vol = max_vol_threshold
        self.risk_free = 'LQDT'

    def generate_signal(self, data_dict, **kwargs):
        best_score = -1e10
        best_ticker = self.risk_free

        for ticker, df in data_dict.items():
            if ticker == self.risk_free:
                continue
            if len(df) < max(self.lookback, self.vol_window):
                continue

            # Momentum
            lookback_price = df['CLOSE'].iloc[-self.lookback]
            current_price = df['CLOSE'].iloc[-1]
            momentum = (current_price - lookback_price) / lookback_price

            # Волатильность
            returns = df['CLOSE'].pct_change()
            vol_series = rolling_volatility(returns, self.vol_window)
            vol = vol_series.iloc[-1] if not vol_series.empty else 0.0

            # Фильтр по волатильности
            if pd.isna(vol) or vol > self.max_vol:
                continue  # пропускаем высоковолатильный актив

            score = momentum / vol if vol > 0 else -1e10
            if score > best_score:
                best_score = score
                best_ticker = ticker

        return {'selected': best_ticker}
from core.base_strategy import BaseStrategy
from indicators.volatility import rolling_volatility, market_volatility
import pandas as pd
import numpy as np

class DualMomentumStrategy(BaseStrategy):
    def __init__(
        self,
        lookback_period: int = 126,
        vol_window: int = 20,
        max_vol_threshold: float = 0.35,
        market_vol_mult: float = 2.0,
        risk_free_ticker: str = 'LQDT'
    ):
        self.lookback = lookback_period
        self.vol_window = vol_window
        self.max_vol = max_vol_threshold
        self.market_vol_mult = market_vol_mult
        self.risk_free = risk_free_ticker

    def generate_signal(self, data_dict, market_data=None, **kwargs):
        # Рыночная волатильность (глобальный фильтр)
        if market_data is not None and len(market_data) >= self.vol_window:
            mkt_vol = market_volatility(market_data, self.vol_window).iloc[-1]
            if mkt_vol > self.max_vol * self.market_vol_mult:
                return {'selected': self.risk_free}

        best_score = -1e10
        best_ticker = self.risk_free

        for ticker, df in data_dict.items():
            if ticker == self.risk_free:
                continue
            if len(df) < self.lookback:
                continue

            # Momentum
            lookback_price = df['CLOSE'].iloc[-self.lookback]
            current_price = df['CLOSE'].iloc[-1]
            momentum = (current_price - lookback_price) / lookback_price

            # Индивидуальная волатильность
            returns = df['CLOSE'].pct_change()
            vol_series = rolling_volatility(returns, self.vol_window)
            vol = vol_series.iloc[-1]

            if pd.isna(vol) or vol > self.max_vol:
                continue

            # Score = momentum / volatility
            score = momentum / vol if vol > 0 else -1e10
            if score > best_score:
                best_score = score
                best_ticker = ticker

        return {'selected': best_ticker}

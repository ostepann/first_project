# backtest_platform/strategies/dual_momentum.py

from backtest_platform.core.base_strategy import BaseStrategy
from backtest_platform.indicators.volatility import rolling_volatility
import pandas as pd

class DualMomentumStrategy(BaseStrategy):
    def __init__(
        self,
        base_lookback=20,
        base_vol_window=20,
        max_vol_threshold=0.3,
        risk_free_ticker='LQDT',
        use_rvi_adaptation=True,
        bare_mode=False
    ):
        self.base_lookback = base_lookback
        self.base_vol_window = base_vol_window
        self.max_vol = max_vol_threshold
        self.risk_free = risk_free_ticker
        self.use_rvi_adaptation = use_rvi_adaptation
        self.bare_mode = bare_mode

    def _get_rvi_level(self, rvi_value):
        if rvi_value < 15:
            return 'low'
        elif rvi_value < 25:
            return 'medium'
        else:
            return 'high'

    def _get_adaptive_windows(self, rvi_level):
        lookback = self.base_lookback
        vol_window = self.base_vol_window
        if self.use_rvi_adaptation:
            if rvi_level == 'low':
                lookback = int(lookback * 1.2)
                vol_window = int(vol_window * 1.2)
            elif rvi_level == 'high':
                lookback = int(lookback * 0.7)
                vol_window = int(vol_window * 0.7)
        return {'lookback_period': lookback, 'vol_window': vol_window}

    def generate_signal(self, data_dict, market_data=None, rvi_data=None, **kwargs):
        # === Режим минимальной логики: только momentum ===
        if self.bare_mode:
            best_mom = -1e10
            best_ticker = self.risk_free
            for ticker, df in data_dict.items():
                if ticker == self.risk_free:
                    continue
                if len(df) < self.base_lookback:
                    continue
                mom = (df['CLOSE'].iloc[-1] - df['CLOSE'].iloc[-self.base_lookback]) / df['CLOSE'].iloc[-self.base_lookback]
                if mom > best_mom:
                    best_mom = mom
                    best_ticker = ticker
            return {'selected': best_ticker}

        # === Полная логика (с адаптацией и фильтрами) ===
        rvi_level = 'medium'
        if rvi_data is not None and not rvi_data.empty:
            rvi_value = rvi_data['CLOSE'].iloc[-1]
            rvi_level = self._get_rvi_level(rvi_value)

        windows = self._get_adaptive_windows(rvi_level)
        lookback = windows['lookback_period']
        vol_window = windows['vol_window']

        best_score = -1e10
        best_ticker = self.risk_free

        for ticker, df in data_dict.items():
            if ticker == self.risk_free:
                continue
            if len(df) < max(lookback, vol_window):
                continue

            # Momentum
            lookback_price = df['CLOSE'].iloc[-lookback]
            current_price = df['CLOSE'].iloc[-1]
            momentum = (current_price - lookback_price) / lookback_price

            # Волатильность
            returns = df['CLOSE'].pct_change()
            vol_series = rolling_volatility(returns, vol_window)
            vol = vol_series.iloc[-1] if not vol_series.empty else 0.0

            if pd.isna(vol) or vol > self.max_vol:
                continue

            score = momentum / vol if vol > 0 else -1e10
            if score > best_score:
                best_score = score
                best_ticker = ticker

        return {'selected': best_ticker}
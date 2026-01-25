# backtest_platform/strategies/dual_momentum.py

from backtest_platform.core.base_strategy import BaseStrategy
from backtest_platform.indicators.volatility import rolling_volatility
import pandas as pd
import numpy as np


class DualMomentumStrategy(BaseStrategy):
    def __init__(
        self,
        base_lookback=20,
        base_vol_window=20,
        max_vol_threshold=0.3,
        risk_free_ticker='LQDT',
        use_rvi_adaptation=True,
        bare_mode=False,
        rvi_high_threshold=35,          # ← НОВЫЙ параметр
        market_vol_threshold=None,      # ← НОВЫЙ параметр (если None — использовать max_vol_threshold)
        use_trend_filter=False,         # ← ВКЛЮЧЕНИЕ/ВЫКЛЮЧЕНИЕ трендового фильтра
        trend_window=60                 # ← ДЛИНА окна для анализа тренда
    ):
        self.base_lookback = base_lookback
        self.base_vol_window = base_vol_window
        self.max_vol_threshold = max_vol_threshold
        self.risk_free_ticker = risk_free_ticker
        self.use_rvi_adaptation = use_rvi_adaptation
        self.bare_mode = bare_mode
        self.rvi_high_threshold = rvi_high_threshold
        self.market_vol_threshold = market_vol_threshold or max_vol_threshold
        self.use_trend_filter = use_trend_filter
        self.trend_window = trend_window

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

    def _is_uptrend(self, prices: pd.Series, window: int) -> bool:
        """
        Проверяет, находится ли актив в восходящем тренде на основе наклона линейной регрессии.
        Возвращает True, если наклон положительный.
        """
        if len(prices) < window:
            # Если данных меньше, чем окно — считаем, что тренд не определён.
            # Возвращаем True, чтобы не блокировать актив по умолчанию.
            return True
        x = np.arange(window)
        y = prices.iloc[-window:].values
        # Защита от некорректных данных
        if np.any(np.isnan(y)) or np.any(np.isinf(y)):
            return True
        slope, _ = np.polyfit(x, y, 1)
        return slope > 0

    def generate_signal(self, data_dict, market_data=None, rvi_data=None, **kwargs):
        # === Рыночный фильтр: если рыночная волатильность или RVI слишком высоки → выход в кэш ===
        market_filter_triggered = False

        # Проверка RVI
        if rvi_data is not None and not rvi_data.empty:
            rvi_value = rvi_data['CLOSE'].iloc[-1]
            if rvi_value >= self.rvi_high_threshold:
                market_filter_triggered = True

        # Проверка волатильности рыночного индекса (например, MOEX)
        if not market_filter_triggered and market_data is not None:
            if len(market_data) >= self.base_vol_window:
                market_returns = market_data['CLOSE'].pct_change().dropna()
                if len(market_returns) >= self.base_vol_window:
                    market_vol_series = rolling_volatility(market_returns, self.base_vol_window)
                    if not market_vol_series.empty:
                        market_vol = market_vol_series.iloc[-1]
                        if market_vol > self.market_vol_threshold:
                            market_filter_triggered = True

        if market_filter_triggered:
            return {'selected': self.risk_free_ticker}

        # === Режим минимальной логики: только momentum ===
        if self.bare_mode:
            best_mom = -1e10
            best_ticker = self.risk_free_ticker
            for ticker, df in data_dict.items():
                if ticker == self.risk_free_ticker:
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
        best_ticker = self.risk_free_ticker

        for ticker, df in data_dict.items():
            if ticker == self.risk_free_ticker:
                continue

            # Минимальная длина данных для всех используемых окон
            min_required_length = max(lookback, vol_window)
            if self.use_trend_filter:
                min_required_length = max(min_required_length, self.trend_window)

            if len(df) < min_required_length:
                continue

            # === Трендовый фильтр (опционально) ===
            if self.use_trend_filter:
                if not self._is_uptrend(df['CLOSE'], self.trend_window):
                    continue  # Пропускаем актив, если он не в uptrend

            # Momentum
            lookback_price = df['CLOSE'].iloc[-lookback]
            current_price = df['CLOSE'].iloc[-1]
            momentum = (current_price - lookback_price) / lookback_price

            # Волатильность актива
            returns = df['CLOSE'].pct_change().dropna()
            if len(returns) < vol_window:
                continue
            vol_series = rolling_volatility(returns, vol_window)
            vol = vol_series.iloc[-1] if not vol_series.empty else 0.0

            if pd.isna(vol) or vol > self.max_vol_threshold:
                continue

            score = momentum / vol if vol > 0 else -1e10
            if score > best_score:
                best_score = score
                best_ticker = ticker

        return {'selected': best_ticker}
# backtest_platform/strategies/dual_momentum.py
from core.base_strategy import BaseStrategy
from indicators.volatility import rolling_volatility
from indicators.trend import detect_trend, get_trend_strength
import pandas as pd
import numpy as np

class DualMomentumStrategy(BaseStrategy):
    def __init__(
        self,
        base_lookback: int = 126,
        base_vol_window: int = 20,
        max_vol_threshold: float = 0.35,
        risk_free_ticker: str = 'LQDT'
    ):
        self.base_lookback = base_lookback
        self.base_vol_window = base_vol_window
        self.max_vol = max_vol_threshold
        self.risk_free = risk_free_ticker

    def _get_rvi_level(self, rvi_value: float) -> str:
        """Классификация RVI по уровням (настройте пороги под MOEX)"""
        if rvi_value < 15:
            return 'low'
        elif rvi_value < 25:
            return 'medium'
        else:
            return 'high'

    def _get_adaptive_windows(self, rvi_level: str, trend: str) -> dict:
        """
        Возвращает адаптивные окна в зависимости от RVI и тренда.
        Правила можно оптимизировать.
        """
        # Базовые значения
        lookback = self.base_lookback
        vol_window = self.base_vol_window

        # Адаптация под RVI
        if rvi_level == 'low':
            lookback = int(lookback * 1.2)   # длиннее — меньше шума
            vol_window = int(vol_window * 1.2)
        elif rvi_level == 'high':
            lookback = int(lookback * 0.7)   # короче — быстрее реагируем
            vol_window = int(vol_window * 0.7)

        # Адаптация под тренд
        if trend == 'sideways':
            lookback = int(lookback * 1.3)   # избегаем ложных пробоев
        elif trend in ('uptrend', 'downtrend'):
            lookback = int(lookback * 0.9)   # ловим импульс

        return {
            'lookback_period': max(10, lookback),
            'vol_window': max(5, vol_window)
        }

    def generate_signal(self, data_dict, market_data=None, rvi_data=None, **kwargs):
        """
        data_dict: данные по активам
        rvi_data: pd.DataFrame с колонкой 'CLOSE' = RVI
        """
        if rvi_data is None or rvi_data.empty:
            rvi_level = 'medium'
        else:
            current_rvi = rvi_data['CLOSE'].iloc[-1]
            rvi_level = self._get_rvi_level(current_rvi)

        # Определяем тренд на рынке (по EQMX)
        market_trend = 'sideways'
        if market_data is not None and len(market_data) > 20:
            market_trend = detect_trend(market_data['CLOSE'], window=20)

        # Получаем адаптивные окна
        windows = self._get_adaptive_windows(rvi_level, market_trend)
        lookback = windows['lookback_period']
        vol_window = windows['vol_window']

        # Рыночная волатильность (глобальный фильтр)
        if market_data is not None and len(market_data) >= vol_window:
            mkt_vol = rolling_volatility(market_data['CLOSE'].pct_change(), vol_window).iloc[-1]
            if mkt_vol > self.max_vol * 2.0:
                return {'selected': self.risk_free, 'windows': windows, 'rvi_level': rvi_level}

        best_score = -1e10
        best_ticker = self.risk_free

        for ticker, df in data_dict.items():
            if ticker == self.risk_free:
                continue
            if len(df) < lookback:
                continue

            # Momentum
            lookback_price = df['CLOSE'].iloc[-lookback]
            current_price = df['CLOSE'].iloc[-1]
            momentum = (current_price - lookback_price) / lookback_price

            # Индивидуальная волатильность
            returns = df['CLOSE'].pct_change()
            vol_series = rolling_volatility(returns, vol_window)
            vol = vol_series.iloc[-1]

            if pd.isna(vol) or vol > self.max_vol:
                continue

            # Тренд по активу (доп. фильтр)
            asset_trend = detect_trend(df['CLOSE'], window=20)
            if asset_trend == 'downtrend' and momentum > 0:
                continue  # игнорируем ложные сигналы

            score = momentum / vol if vol > 0 else -1e10
            if score > best_score:
                best_score = score
                best_ticker = ticker

        return {
            'selected': best_ticker,
            'windows': windows,
            'rvi_level': rvi_level,
            'market_trend': market_trend
        }

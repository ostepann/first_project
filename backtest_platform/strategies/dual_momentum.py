# backtest_platform/strategies/dual_momentum.py

"""
Файл содержит определение класса DualMomentumStrategy для применения двойной 
стратегии момента в бэктестере.
"""
from backtest_platform.core.base_strategy import BaseStrategy
from backtest_platform.indicators.volatility import rolling_volatility
import pandas as pd
import numpy as np


class DualMomentumStrategy(BaseStrategy):
    """
    Двойная стратегия момента, которая выбирает активы на основе их момента
    роста, фильтруя их по волатильности и тренду, и использует рыночный фильтр
    для защиты капитала.
    
    КРИТИЧЕСКИЕ УЛУЧШЕНИЯ:
    1. Все "магические числа" вынесены в параметры (RVI thresholds, multipliers).
    2. Введено разделение параметров волатильности:
       - base_vol_window: окно для расчета волатильности отдельных активов
       - market_vol_window: окно для расчета волатильности рыночного индекса (фильтр)
    3. Трендовый фильтр теперь использует адаптированное окно lookback при use_rvi_adaptation=True.
    """
    
    def __init__(
        self,
        base_lookback=20,
        base_vol_window=20,
        market_vol_window=None,           # ← Окно волатильности рыночного индекса
        max_vol_threshold=0.3,
        risk_free_ticker='LQDT',
        use_rvi_adaptation=True,
        bare_mode=False,
        rvi_high_exit_threshold=35,       # ← Переименовано для ясности
        rvi_low_threshold=15,             # ← НОВЫЙ ПАРАМЕТР
        rvi_medium_threshold=25,          # ← НОВЫЙ ПАРАМЕТР
        rvi_low_multiplier=1.2,           # ← НОВЫЙ ПАРАМЕТР
        rvi_high_multiplier=0.7,          # ← НОВЫЙ ПАРАМЕТР
        market_vol_threshold=None,
        use_trend_filter=False,
        trend_window=60
    ):
        """
        Инициализирует стратегию двойного момента.
        
        Args:
            base_lookback (int): Период для расчета момента (в днях).
            base_vol_window (int): Базовое окно для расчета волатильности актива.
            market_vol_window (int, optional): Окно для расчета волатильности рыночного индекса.
                                             По умолчанию равно base_vol_window.
            max_vol_threshold (float): Максимально допустимая волатильность актива.
            risk_free_ticker (str): Тикер активного денежного рынка (кэш).
            use_rvi_adaptation (bool): Включает адаптацию окон на основе RVI.
            bare_mode (bool): Только момент, без фильтров.
            rvi_high_exit_threshold (float): Порог RVI для перехода в кэш.
            rvi_low_threshold (float): Порог для уровня "низкой" волатильности.
            rvi_medium_threshold (float): Порог для уровня "средней" волатilities.
            rvi_low_multiplier (float): Множитель для увеличения окон при низкой воле.
            rvi_high_multiplier (float): Множитель для сокращения окон при высокой воле.
            market_vol_threshold (float, optional): Порог волатильности для рыночного фильтра.
            use_trend_filter (bool): Включает трендовый фильтр.
            trend_window (int): Базовое окно для анализа тренда (используется, если адаптация отключена).
        """
        self.base_lookback = base_lookback
        self.base_vol_window = base_vol_window
        self.market_vol_window = market_vol_window or base_vol_window
        self.max_vol_threshold = max_vol_threshold
        self.risk_free_ticker = risk_free_ticker
        self.use_rvi_adaptation = use_rvi_adaptation
        self.bare_mode = bare_mode
        self.rvi_high_exit_threshold = rvi_high_exit_threshold
        self.rvi_low_threshold = rvi_low_threshold
        self.rvi_medium_threshold = rvi_medium_threshold
        self.rvi_low_multiplier = rvi_low_multiplier
        self.rvi_high_multiplier = rvi_high_multiplier
        self.market_vol_threshold = market_vol_threshold or max_vol_threshold
        self.use_trend_filter = use_trend_filter
        self.trend_window = trend_window

    def _get_rvi_level(self, rvi_value):
        """Определяет текущий уровень RVI (низкий, средний, высокий) на основе конфигурируемых порогов."""
        if rvi_value < self.rvi_low_threshold:
            return 'low'
        elif rvi_value < self.rvi_medium_threshold:
            return 'medium'
        else:
            return 'high'

    def _get_adaptive_windows(self, rvi_level):
        """
        Централизованная функция для получения адаптированных размеров окон
        на основе уровня RVI. Обеспечивает согласованную адаптацию для:
        - окна расчета момента (lookback)
        - окна волатильности актива (vol_window_asset)
        - окна волатильности рынка (vol_window_market)
        
        Args:
            rvi_level (str): Уровень RVI ('low', 'medium', 'high').
            
        Returns:
            dict: Словарь с ключами:
                - 'lookback_period': адаптированное окно момента
                - 'vol_window_asset': адаптированное окно волатильности актива
                - 'vol_window_market': адаптированное окно волатильности рынка
        """
        # Инициализируем окна базовыми значениями
        lookback = self.base_lookback
        vol_window_asset = self.base_vol_window
        vol_window_market = self.market_vol_window
        
        # Применяем множитель для адаптации, если включен режим
        if self.use_rvi_adaptation:
            if rvi_level == 'low':
                multiplier = self.rvi_low_multiplier
            elif rvi_level == 'high':
                multiplier = self.rvi_high_multiplier
            else:
                multiplier = 1.0
            
            lookback = int(lookback * multiplier)
            vol_window_asset = int(vol_window_asset * multiplier)
            vol_window_market = int(vol_window_market * multiplier)
        
        return {
            'lookback_period': lookback,
            'vol_window_asset': vol_window_asset,
            'vol_window_market': vol_window_market
        }

    def _is_uptrend(self, prices: pd.Series, window: int) -> bool:
        """Проверяет, находится ли актив в восходящем тренде."""
        if len(prices) < window:
            return True  # Защита от ошибок, считаем, что тренд есть по умолчанию
        x = np.arange(window)
        y = prices.iloc[-window:].values
        if np.any(np.isnan(y)) or np.any(np.isinf(y)):
            return True
        slope, _ = np.polyfit(x, y, 1)
        return slope > 0

    def generate_signal(self, data_dict, market_data=None, rvi_data=None, **kwargs):
        """
        Генерирует сигнал для выбора актива или денежного рынка.
        Стратегия включает:
        1. Глобальный рыночный фильтр (на основе RVI и волатильности индекса)
        2. Локальные фильтры по каждому активу (волатильность, тренд)
        3. Выбор актива с наилучшим отношением момента к волатильности
        
        ВАЖНО: Использует СЕМАНТИЧЕСКИ РАЗДЕЛЕННЫЕ параметры:
        - vol_window_asset для фильтрации отдельных активов
        - vol_window_market для рыночного фильтра
        """
        market_filter_triggered = False
        
        # --- 1. Глобальный рыночный фильтр --
        # Проверка по RVI
        if rvi_data is not None and not rvi_data.empty:
            rvi_value = rvi_data['CLOSE'].iloc[-1]
            if rvi_value >= self.rvi_high_exit_threshold:
                market_filter_triggered = True
        
        # Определяем уровень RVI для адаптации окон
        rvi_level = 'medium'
        if rvi_data is not None and not rvi_data.empty:
            rvi_value = rvi_data['CLOSE'].iloc[-1]
            rvi_level = self._get_rvi_level(rvi_value)
        
        # Получаем ВСЕ адаптированные окна в одном месте (централизованная логика)
        windows = self._get_adaptive_windows(rvi_level)
        lookback = windows['lookback_period']
        vol_window_asset = windows['vol_window_asset']
        vol_window_market = windows['vol_window_market']
        
        # 🔧 ОПРЕДЕЛЕНИЕ ОКНА ДЛЯ ТРЕНДОВОГО ФИЛЬТРА:
        # Если включена адаптация через RVI — используем адаптированное lookback.
        # Иначе — используем базовое trend_window.
        trend_analysis_window = lookback if self.use_rvi_adaptation else self.trend_window
        
        # Проверка по волатильности рыночного индекса (используем ТОЛЬКО vol_window_market)
        if not market_filter_triggered and market_data is not None:
            if len(market_data) >= vol_window_market:
                market_returns = market_data['CLOSE'].pct_change().dropna()
                if len(market_returns) >= vol_window_market:
                    market_vol_series = rolling_volatility(market_returns, vol_window_market)
                    if not market_vol_series.empty:
                        market_vol = market_vol_series.iloc[-1]
                        if market_vol > self.market_vol_threshold:
                            market_filter_triggered = True
        
        if market_filter_triggered:
            return {'selected': self.risk_free_ticker}
        
        # --- 2. Минимальный режим (только момент) --
        if self.bare_mode:
            best_mom = -1e10
            best_ticker = self.risk_free_ticker
            for ticker, df in data_dict.items():
                if ticker == self.risk_free_ticker:
                    continue
                if len(df) < lookback:
                    continue
                mom = (df['CLOSE'].iloc[-1] - df['CLOSE'].iloc[-lookback]) / df['CLOSE'].iloc[-lookback]
                if mom > best_mom:
                    best_mom = mom
                    best_ticker = ticker
            return {'selected': best_ticker}
        
        # --- 3. Полная логика (с фильтрами) --
        best_score = -1e10
        best_ticker = self.risk_free_ticker
        for ticker, df in data_dict.items():
            if ticker == self.risk_free_ticker:
                continue
            
            min_required_length = max(lookback, vol_window_asset)
            if self.use_trend_filter:
                min_required_length = max(min_required_length, trend_analysis_window)
            
            if len(df) < min_required_length:
                continue
            
            # Трендовый фильтр (опционально) — используем согласованное окно
            if self.use_trend_filter:
                if not self._is_uptrend(df['CLOSE'], trend_analysis_window):
                    continue
            
            # Расчет момента
            lookback_price = df['CLOSE'].iloc[-lookback]
            current_price = df['CLOSE'].iloc[-1]
            momentum = (current_price - lookback_price) / lookback_price
            
            # Расчет волатильности актива (используем ТОЛЬКО vol_window_asset)
            returns = df['CLOSE'].pct_change().dropna()
            if len(returns) < vol_window_asset:
                continue
            
            vol_series = rolling_volatility(returns, vol_window_asset)
            vol = vol_series.iloc[-1] if not vol_series.empty else 0.0
            
            if pd.isna(vol) or vol > self.max_vol_threshold:
                continue
            
            score = momentum / vol if vol > 0 else -1e10
            if score > best_score:
                best_score = score
                best_ticker = ticker
        
        return {'selected': best_ticker}
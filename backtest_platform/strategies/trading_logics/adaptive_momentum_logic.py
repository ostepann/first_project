# backtest_platform/strategies/trading_logics/adaptive_momentum_logic.py

"""
Конкретная реализация торговой логики: Адаптивная стратегия двойного момента.

Это основная, полная логика стратегии, которая включает в себя:
- Фильтрацию активов по их волатильности.
- Опциональную проверку на наличие восходящего тренда.
- Выбор актива на основе отношения момента к волатильности (Risk-Adjusted Return).

ОСОБЕННОСТИ:
- Более надёжна, чем "голый момент", благодаря фильтрам.
- Учитывает риск (волатильность) при выборе актива.
- Может быть адаптирована под текущие рыночные условия через внешние параметры.
"""

from .base_logic import TradingLogic
from backtest_platform.indicators.volatility import rolling_volatility
import pandas as pd
import numpy as np

class AdaptiveMomentumLogic(TradingLogic):
    """
    Полная адаптивная логика торговли с фильтрами.

    Эта реализация инкапсулирует всю сложную логику выбора актива, которая ранее
    была размещена внутри монолитного метода `generate_signal`.
    """

    def __init__(
        self,
        lookback_period: int,
        vol_window_asset: int,
        max_vol_threshold: float,
        use_trend_filter: bool,
        trend_analysis_window: int,
        trend_filter_on_insufficient_data: str,
        **kwargs
    ):
        """
        Инициализирует адаптивную логику.

        Args:
            lookback_period (int): Окно для расчёта момента.
            vol_window_asset (int): Окно для расчёта волатильности актива.
            max_vol_threshold (float): Максимально допустимая волатильность актива.
            use_trend_filter (bool): Флаг, включающий проверку тренда.
            trend_analysis_window (int): Окно для анализа тренда.
            trend_filter_on_insufficient_data (str): Поведение при недостатке данных ('allow'/'block').
            **kwargs: Дополнительные параметры для базового класса.
        """
        super().__init__(**kwargs)
        self.lookback_period = lookback_period
        self.vol_window_asset = vol_window_asset
        self.max_vol_threshold = max_vol_threshold
        self.use_trend_filter = use_trend_filter
        self.trend_analysis_window = trend_analysis_window
        self.trend_filter_on_insufficient_data = trend_filter_on_insufficient_data

    def _is_uptrend(self, prices: pd.Series, window: int) -> bool:
        """
        Внутренний метод для проверки восходящего тренда.

        Использует линейную регрессию для определения наклона цены.
        Является копией метода из `DualMomentumStrategy` для полной изоляции логики.

        Args:
            prices (pd.Series): Серия цен закрытия.
            window (int): Количество точек для анализа.

        Returns:
            bool: True, если тренд восходящий или данных недостаточно (в зависимости от настроек).
        """
        # Проверка достаточности данных
        if len(prices) < window:
            if self.trend_filter_on_insufficient_data == 'allow':
                return True
            else:
                return False
        
        x = np.arange(window)
        y = prices.iloc[-window:].values
        # Защита от некорректных числовых значений
        if np.any(np.isnan(y)) or np.any(np.isinf(y)):
            if self.trend_filter_on_insufficient_data == 'allow':
                return True
            else:
                return False
                
        slope, _ = np.polyfit(x, y, 1)
        return slope > 0

    def select_best_asset(self, data_dict: dict[str, pd.DataFrame]) -> str:
        """
        Выбирает актив с наилучшим Risk-Adjusted Moment (момент / волатильность).

        Алгоритм:
        1. Проходит по всем активам.
        2. Проверяет минимальные требования к длине данных.
        3. (Опционально) Применяет трендовый фильтр.
        4. Рассчитывает момент и волатильность.
        5. Отсеивает активы с волатильностью выше порога.
        6. Выбирает актив с максимальным отношением момент/волатильность.

        Args:
            data_dict (dict[str, pd.DataFrame]): Данные по активам.

        Returns:
            str: Тикер лучшего актива или `risk_free_ticker`.
        """
        best_score = -float('inf')
        best_ticker = self.risk_free_ticker
        
        for ticker, df in data_dict.items():
            if ticker == self.risk_free_ticker:
                continue
            
            # Определяем минимальное количество данных, необходимое для всех расчётов
            min_required_length = max(self.lookback_period, self.vol_window_asset)
            if self.use_trend_filter:
                min_required_length = max(min_required_length, self.trend_analysis_window)
            
            if len(df) < min_required_length:
                continue
            
            # Применение трендового фильтра, если он включён
            if self.use_trend_filter:
                if not self._is_uptrend(df['CLOSE'], self.trend_analysis_window):
                    continue
            
            # --- Расчёт момента ---
            lookback_price = df['CLOSE'].iloc[-self.lookback_period]
            current_price = df['CLOSE'].iloc[-1]
            momentum = (current_price - lookback_price) / lookback_price
            
            # --- Расчёт волатильности ---
            returns = df['CLOSE'].pct_change().dropna()
            if len(returns) < self.vol_window_asset:
                continue
            
            vol_series = rolling_volatility(returns, self.vol_window_asset)
            vol = vol_series.iloc[-1] if not vol_series.empty else 0.0
            
            # Фильтрация по волатильности
            if pd.isna(vol) or vol > self.max_vol_threshold:
                continue
            
            # Расчёт итогового скоринга (Risk-Adjusted Return)
            score = momentum / vol if vol > 0 else -float('inf')
            if score > best_score:
                best_score = score
                best_ticker = ticker
                
        return best_ticker
# backtest_platform/strategies/dual_momentum.py

"""
Файл содержит определение класса DualMomentumStrategy для применения двойной 
стратегии момента в бэктестере.

ОСНОВНОЕ ИЗМЕНЕНИЕ:
Класс был рефакторингован с использованием паттерна "Стратегия". Теперь он 
выступает в роли **легковесного фасада**, который:
1. Управляет глобальным рыночным фильтром.
2. На основе флагов (`bare_mode`, `use_rvi_adaptation`) выбирает подходящую 
   конкретную реализацию торговой логики (`BareMomentumLogic` или `AdaptiveMomentumLogic`).
3. Делегирует всю работу по выбору актива этой конкретной логике.

Это значительно упрощает поддержку, тестирование и расширение кода.
"""

from backtest_platform.core.base_strategy import BaseStrategy
from backtest_platform.indicators.volatility import rolling_volatility
# Импортируем новые модули с логикой
from .trading_logics.bare_momentum_logic import BareMomentumLogic
from .trading_logics.adaptive_momentum_logic import AdaptiveMomentumLogic
# 🔑 КЛЮЧЕВОЙ ИМПОРТ для устранения ошибки Pylance
from .trading_logics.base_logic import TradingLogic  # ← ЭТОТ ИМПОРТ ОБЯЗАТЕЛЕН
import pandas as pd
import numpy as np
import warnings

class DualMomentumStrategy(BaseStrategy):
    """
    Фасад для стратегии двойного момента.

    Этот класс больше не содержит сложной вложенной логики выбора актива. 
    Его единственная задача — координация: применить рыночный фильтр и 
    передать управление соответствующей "стратегии" (логике).
    
    КРИТИЧЕСКИЕ УЛУЧШЕНИЯ:
    1. Все "магические числа" вынесены в параметры (RVI thresholds, multipliers).
    2. Введено разделение параметров волатильности:
       - base_vol_window: окно для расчета волатильности отдельных активов
       - market_vol_window: окно для расчета волатильности рыночного индекса (фильтр)
    3. Трендовый фильтр теперь использует адаптированное окно lookback при use_rvi_adaptation=True.
    4. Явное управление поведением при недостатке данных через параметр trend_filter_on_insufficient_data.
    5. 🔧 ИСПРАВЛЕНО: Рыночный фильтр теперь использует ТОЛЬКО market_vol_window (не base_vol_window).
    6. 🔧 ИСПРАВЛЕНО: Устранено дублирование логики извлечения RVI. Значение RVI извлекается ОДИН раз в методе market_filter и переиспользуется.
    7. 🔧 СТАНДАРТИЗАЦИЯ: Все расчёты тренда используют numpy.polyfit для максимальной производительности.
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
        trend_window=60,
        trend_filter_on_insufficient_data='allow',  # ← НОВЫЙ ПАРАМЕТР
        trend_r_squared_threshold=0.2      # ← НОВЫЙ ПАРАМЕТР для совместимости с detect_trend
    ):
        """
        Инициализирует фасад стратегии двойного момента.
        
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
            rvi_medium_threshold (float): Порог для уровня "средней" волатильности.
            rvi_low_multiplier (float): Множитель для увеличения окон при низкой воле.
            rvi_high_multiplier (float): Множитель для сокращения окон при высокой воле.
            market_vol_threshold (float, optional): Порог волатильности для рыночного фильтра.
            use_trend_filter (bool): Включает трендовый фильтр.
            trend_window (int): Базовое окно для анализа тренда (используется, если адаптация отключена).
            trend_filter_on_insufficient_data (str): Поведение при недостатке данных для трендового фильтра.
                                                   'allow' — разрешить вход (доверие по умолчанию),
                                                   'block' — запретить вход (консервативный подход).
            trend_r_squared_threshold (float): Порог R² для определения силы тренда (для совместимости с detect_trend).
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
        self.trend_filter_on_insufficient_data = trend_filter_on_insufficient_data
        # self.trend_r_squared_threshold = trend_r_squared_threshold
        
        # 🔧 ИСПРАВЛЕНО: Валидация критического разделения окон
        if self.market_vol_window == self.base_vol_window and market_vol_window is None:
            warnings.warn(
                f"Внимание: market_vol_window ({self.market_vol_window}) совпадает с base_vol_window ({self.base_vol_window}). "
                "Рекомендуется использовать разные окна для рыночной и активной волатильности. "
                "Установите market_vol_window явно при инициализации стратегии.",
                UserWarning
            )

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
        """
            ⚡ БЫСТРАЯ ПРОВЕРКА ВОСХОДЯЩЕГО ТРЕНДА (для фильтрации в стратегии).
            
            Возвращает булево значение для использования в условиях `if`.
            Оптимизирована для скорости: использует только расчёт наклона (без R²).
            
            ⚠️ ЭТО НЕ АНАЛОГ `detect_trend` из indicators/trend.py!
            - `detect_trend` — для детального анализа и отчётов (возвращает строку, считает R²).
            - `_is_uptrend` — для быстрого принятия решений в стратегии (возвращает bool, только наклон).
            
            Поведение при недостатке данных контролируется параметром 
            `trend_filter_on_insufficient_data`:
                - 'allow': возвращает True (разрешает вход, текущее поведение по умолчанию).
                - 'block': возвращает False (блокирует вход, консервативный подход).
        """
        if len(prices) < window:
            # Недостаточно данных для анализа тренда
            if self.trend_filter_on_insufficient_data == 'allow':
                return True   # Доверие по умолчанию: разрешаем вход
            else:  # 'block' или любое другое значение
                return False  # Консервативный подход: блокируем вход
        
        x = np.arange(window)
        y = prices.iloc[-window:].values
        
        # Защита от некорректных данных, которые могли возникнуть 
        # несмотря на предварительную очистку в load_market_data 
        # (например, бесконечности или NaN из-за ошибок в расчётах).
        if np.any(np.isnan(y)) or np.any(np.isinf(y)):
            if self.trend_filter_on_insufficient_data == 'allow':
                return True
            else:
                return False
                
        # 🔧 СТАНДАРТИЗАЦИЯ: Используем numpy.polyfit для производительности
        slope, _ = np.polyfit(x, y, 1)
        return slope > 0
    
    def market_filter(self, market_data: pd.DataFrame, rvi_data: pd.DataFrame) -> dict:
        """
        ДВУХЭТАПНЫЙ рыночный фильтр с корректным использованием окон волатильности.
        
        Логика:
        1. Этап RVI: Если RVI ≥ rvi_high_exit_threshold → БЛОКИРОВКА (режим кэша)
        2. Этап волатильности: Только если этап 1 НЕ сработал → проверка волатильности рынка
           с использованием ТОЛЬКО market_vol_window (НЕ base_vol_window!)
        
        ⚠️ КРИТИЧЕСКИ ВАЖНО: Этот метод является ЕДИНСТВЕННЫМ местом в коде,
        где извлекается последнее значение RVI. Это устраняет дублирование
        и обеспечивает согласованность данных.
        
        Args:
            market_data: DataFrame с рыночным индексом (столбец 'CLOSE')
            rvi_data: DataFrame с RVI индикатором (столбец 'CLOSE')
            
        Returns:
            dict с ключами:
                - 'triggered': bool — сработал ли фильтр
                - 'stage': str | None — этап срабатывания ('rvi', 'volatility', None)
                - 'rvi_value': float | None — значение RVI (всегда возвращается, если данные есть)
                - 'market_vol': float | None — волатильность рынка
                - 'rationale': str — обоснование решения
        """
        result = {
            'triggered': False,
            'stage': None,
            'rvi_value': None, # ← ЕДИНСТВЕННОЕ МЕСТО ИЗВЛЕЧЕНИЯ RVI
            'market_vol': None,
            'rationale': ''
        }
        
        # ===== ЦЕНТРАЛИЗОВАННОЕ ИЗВЛЕЧЕНИЕ ЗНАЧЕНИЯ RVI =====
        # Это ключевое изменение для устранения дублирования.
        if rvi_data is not None and not rvi_data.empty:
            result['rvi_value'] = float(rvi_data['CLOSE'].iloc[-1])
        
        # ===== ЭТАП 1: Проверка RVI =====
        if result['rvi_value'] is not None:
            if result['rvi_value'] >= self.rvi_high_exit_threshold:
                result.update({
                    'triggered': True,
                    'stage': 'rvi',
                    'rationale': (
                        f"RVI={result['rvi_value']:.2f} ≥ порога {self.rvi_high_exit_threshold} → "
                        "блокировка торговли (высокая относительная волатильность)"
                    )
                })
                return result
        
        # ===== ЭТАП 2: Проверка волатильности РЫНКА (ТОЛЬКО market_vol_window!) =====
        vol_window_market = self.market_vol_window
        
        if market_data is not None and len(market_data) >= vol_window_market + 1:
            market_returns = market_data['CLOSE'].pct_change().dropna()
            
            if len(market_returns) >= vol_window_market:
                market_vol_series = rolling_volatility(market_returns, vol_window_market)
                
                if not market_vol_series.empty and not pd.isna(market_vol_series.iloc[-1]):
                    market_vol = float(market_vol_series.iloc[-1])
                    result['market_vol'] = market_vol
                    
                    if market_vol >= self.market_vol_threshold:
                        result.update({
                            'triggered': True,
                            'stage': 'volatility',
                            'rationale': (
                                f"Волатильность рынка={market_vol:.4f} ({market_vol:.2%}) ≥ "
                                f"порога {self.market_vol_threshold:.4f} ({self.market_vol_threshold:.2%}) "
                                f"(окно={vol_window_market} дн.) → блокировка торговли"
                            )
                        })
                        return result
        
        # ===== ФИЛЬТР НЕ СРАБОТАЛ =====
        rvi_info = f"RVI={result['rvi_value']:.2f} < {self.rvi_high_exit_threshold}" if result['rvi_value'] is not None else "RVI недоступен"
        vol_info = f"волатильность={result['market_vol']:.2%} < {self.market_vol_threshold:.2%}" if result['market_vol'] is not None else "волатильность недоступна"
        
        result['rationale'] = f"Фильтр пройден: {rvi_info}, {vol_info} → разрешена торговля активами"
        return result

    def _get_trading_logic(self, windows: dict) -> TradingLogic:
        """
        Фабричный метод для создания нужной торговой логики.

        На основе флага `bare_mode` решает, какую конкретную реализацию логики 
        следует использовать, и инициализирует её с необходимыми параметрами.

        Args:
            windows (dict): Словарь с адаптированными окнами 
                            ('lookback_period', 'vol_window_asset' и т.д.).

        Returns:
            TradingLogic: Экземпляр конкретной логики (Bare или Adaptive).
        """
        # Общие параметры, которые нужны любой логике
        common_params = {
            'risk_free_ticker': self.risk_free_ticker,
            'trend_filter_on_insufficient_data': self.trend_filter_on_insufficient_data
        }
        
        if self.bare_mode:
            # Возвращаем простую логику "голого момента"
            return BareMomentumLogic(
                lookback_period=windows['lookback_period'],
                **common_params
            )
        else:
            # Определяем окно для анализа тренда (адаптивное или фиксированное)
            trend_analysis_window = windows['lookback_period'] if self.use_rvi_adaptation else self.trend_window
            # Возвращаем полную адаптивную логику
            return AdaptiveMomentumLogic(
                lookback_period=windows['lookback_period'],
                vol_window_asset=windows['vol_window_asset'],
                max_vol_threshold=self.max_vol_threshold,
                use_trend_filter=self.use_trend_filter,
                trend_analysis_window=trend_analysis_window,
                **common_params
            )

    def generate_signal(self, data_dict, market_data=None, rvi_data=None, **kwargs):
        """
        Генерирует торговый сигнал.

        Это основной публичный метод стратегии. Он стал коротким и читаемым, 
        так как вся сложная логика делегирована другим компонентам.

        Поток выполнения:
        1. Применить глобальный рыночный фильтр (защита капитала).
        2. Если фильтр сработал — немедленно вернуть кэш-актив.
        3. Определить текущий уровень RVI и получить адаптированные окна.
        4. Выбрать подходящую торговую логику через фабричный метод.
        5. Делегировать выбор актива этой логике.
        6. Вернуть результат.

        Args:
            data_dict: Данные по торгуемым активам.
            market_ Данные по рыночному индексу (для фильтра).
            rvi_ Данные по индикатору RVI (для фильтра и адаптации).
            **kwargs: Дополнительные аргументы.

        Returns:
            dict: Словарь с результатом, содержащий выбранный тикер и информацию о фильтре.
        """
        # Шаг 1: Применяем рыночный фильтр для защиты капитала
        market_filter_result = self.market_filter(market_data, rvi_data)
        if market_filter_result['triggered']:
            return { 
                'selected': self.risk_free_ticker,
                'market_filter_triggered': True,
                'market_filter_stage': market_filter_result['stage'],
                'market_filter_rationale': market_filter_result['rationale']
            }

        # Шаг 2: Получаем уровень RVI и адаптированные окна для анализа активов
        rvi_value = market_filter_result.get('rvi_value')
        rvi_level = self._get_rvi_level(rvi_value) if rvi_value is not None else 'medium'
        windows = self._get_adaptive_windows(rvi_level)

        # Шаг 3: ДЕЛЕГИРОВАНИЕ — выбираем и используем конкретную логику
        trading_logic = self._get_trading_logic(windows)
        selected_ticker = trading_logic.select_best_asset(data_dict)

        # Шаг 4: Возвращаем результат
        return {
            'selected': selected_ticker,
            'market_filter_triggered': False,
            'market_filter_rationale': market_filter_result['rationale']
        }
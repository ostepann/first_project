# backtest_platform\strategies\dual_momentum.py

"""
Файл содержит определение класса DualMomentumStrategy для применения двойной 
стратегии момента в бэктестере.

Версия: 1.1.0 (адаптация окон ПЕРЕД рыночным фильтром)
КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ:
1. Адаптация окон под RVI теперь применяется ДО рыночного фильтра.
2. Рыночный фильтр принимает адаптированное окно через параметр vol_window_override.
3. Параметр rvi_low_multiplier теперь влияет как на выбор актива, так и на срабатывание рыночного фильтра.

Версия: 1.2.0 (внедрение абсолютного импульса по Гэри Антончи)
Автор: Oleg Dev
Дата: 2026-02-09

ОСНОВНОЕ ИЗМЕНЕНИЕ В ВЕРСИИ 1.2.0:
Добавлена поддержка абсолютного импульса (absolute momentum)

Версия: 1.2.1 (улучшение диагностичности рыночного фильтра)
КРИТИЧЕСКОЕ УЛУЧШЕНИЕ:
Поля 'market_vol' и 'used_vol_window' теперь ВСЕГДА заполняются при наличии данных,
даже если фильтр срабатывает по RVI. Это позволяет корректно отображать диагностическую
информацию в тестах и отчётах.
"""

from backtest_platform.core.base_strategy import BaseStrategy
from backtest_platform.indicators.volatility import rolling_volatility
from .trading_logics.bare_momentum_logic import BareMomentumLogic
from .trading_logics.adaptive_momentum_logic import AdaptiveMomentumLogic
from .trading_logics.base_logic import TradingLogic
import pandas as pd
import numpy as np
import warnings
from typing import Optional, Dict

__version__ = "1.2.1"
__author__ = "Oleg Dev"
__date__ = "2026-02-14"

class DualMomentumStrategy(BaseStrategy):
    """
    Фасад для стратегии двойного момента с корректной реализацией адаптации под RVI.
    
    КЛЮЧЕВОЕ ИЗМЕНЕНИЕ:
    Адаптация окон под RVI применяется ДО рыночного фильтра, что позволяет
    параметрам rvi_low_multiplier/rvi_high_multiplier влиять на оба этапа:
    1) Расчёт рыночной волатильности (через vol_window_override)
    2) Выбор актива (через адаптированные lookback и vol_window_asset)
    """
    
    def __init__(
        self,
        base_lookback=20,
        base_vol_window=20,
        market_vol_window=None,
        max_vol_threshold=0.3,
        risk_free_ticker='LQDT',
        use_rvi_adaptation=True,
        bare_mode=False,
        rvi_high_exit_threshold=35,
        rvi_low_threshold=15,
        rvi_medium_threshold=25,
        rvi_low_multiplier=1.2,
        rvi_high_multiplier=0.7,
        market_vol_threshold=None,
        use_trend_filter=False,
        trend_window=60,
        trend_filter_on_insufficient_data='allow',
        debug=False
    ):
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
        self.debug = debug
        
        if self.market_vol_window == self.base_vol_window and market_vol_window is None:
            warnings.warn(
                f"Внимание: market_vol_window ({self.market_vol_window}) совпадает с base_vol_window ({self.base_vol_window}). "
                "Рекомендуется использовать разные окна для рыночной и активной волатильности.",
                UserWarning
            )

    def _get_rvi_level(self, rvi_value: Optional[float]) -> str:
        """Определяет уровень волатильности на основе значения RVI."""
        if rvi_value is None:
            return 'medium'
        if rvi_value < self.rvi_low_threshold:
            return 'low'
        elif rvi_value < self.rvi_medium_threshold:
            return 'medium'
        else:
            return 'high'

    def _get_adaptive_windows(self, rvi_level: str) -> Dict[str, int]:
        """Возвращает адаптированные окна в зависимости от уровня RVI."""
        lookback = self.base_lookback
        vol_window_asset = self.base_vol_window
        vol_window_market = self.market_vol_window
        
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
        """Проверяет наличие восходящего тренда через линейную регрессию."""
        if len(prices) < window:
            return self.trend_filter_on_insufficient_data == 'allow'
        
        x = np.arange(window)
        y = prices.iloc[-window:].values
        
        if np.any(np.isnan(y)) or np.any(np.isinf(y)):
            return self.trend_filter_on_insufficient_data == 'allow'
                
        # 🔑 ИСПРАВЛЕНИЕ ТИПИЗАЦИИ: явное преобразование в float для совместимости с np.polyfit
        y_float = np.asarray(y, dtype=np.float64)
        slope, _ = np.polyfit(x, y_float, 1)
        return slope > 0

    def market_filter(
        self,
        market_data: Optional[pd.DataFrame],
        rvi_data: Optional[pd.DataFrame],
        vol_window_override: Optional[int] = None
    ) -> Dict:
        """
        ДВУХЭТАПНЫЙ рыночный фильтр с поддержкой адаптированного окна волатильности.
        
        КРИТИЧЕСКОЕ УЛУЧШЕНИЕ ВЕРСИИ 1.2.1:
        Поля 'market_vol' и 'used_vol_window' ВСЕГДА заполняются при наличии рыночных данных,
        даже если фильтр срабатывает по RVI. Это обеспечивает полную диагностическую информацию
        в тестах и отчётах.
        
        Параметры:
            market_data: Данные рыночного индекса (например, IMOEX)
            rvi_data: Данные индекса волатильности RVI
            vol_window_override: Если задан, используется вместо self.market_vol_window
                                 для расчёта рыночной волатильности (позволяет адаптацию под RVI).
        
        Возвращает:
            Словарь с результатами фильтрации:
            - 'triggered': bool — сработал ли фильтр
            - 'stage': str — этап срабатывания ('rvi' или 'volatility' или None)
            - 'rvi_value': float — текущее значение RVI (None если недоступно)
            - 'market_vol': float — рассчитанная волатильность рынка (None если недоступна)
            - 'used_vol_window': int — фактически использованное окно (None если расчёт невозможен)
            - 'rationale': str — пояснение решения
        """
        result = {
            'triggered': False,
            'stage': None,
            'rvi_value': None,
            'market_vol': None,
            'used_vol_window': None,
            'rationale': ''
        }
        
        # ===== ШАГ 1: Извлечение значения RVI =====
        if rvi_data is not None and not rvi_data.empty:
            result['rvi_value'] = float(rvi_data['CLOSE'].iloc[-1])
        
        # ===== ШАГ 2: Расчёт волатильности РЫНКА (ВСЕГДА выполняется при наличии данных) =====
        vol_window_requested = vol_window_override if vol_window_override is not None else self.market_vol_window
        vol_window_effective = vol_window_requested
        
        if market_data is not None and len(market_data) > 1:
            market_returns = market_data['CLOSE'].pct_change().dropna()
            available_data_points = len(market_returns)
            
            # "Падение" на максимально доступное окно при недостатке данных
            if available_data_points < vol_window_requested:
                vol_window_effective = max(5, available_data_points)
                
                if self.debug:
                    print(f"⚠️  Недостаток данных: запрошено окно={vol_window_requested}, "
                          f"доступно={available_data_points} → используем окно={vol_window_effective}")
            else:
                vol_window_effective = vol_window_requested
            
            # Расчёт волатильности с ЭФФЕКТИВНЫМ окном (выполняется ВСЕГДА при возможности)
            if vol_window_effective >= 5:
                market_vol_series = rolling_volatility(market_returns, vol_window_effective)
                
                if not market_vol_series.empty and not pd.isna(market_vol_series.iloc[-1]):
                    market_vol = float(market_vol_series.iloc[-1])
                    result['market_vol'] = market_vol
                    result['used_vol_window'] = vol_window_effective
        
        # ===== ШАГ 3: Проверка условия срабатывания по RVI =====
        if result['rvi_value'] is not None and result['rvi_value'] >= self.rvi_high_exit_threshold:
            result.update({
                'triggered': True,
                'stage': 'rvi',
                'rationale': (
                    f"RVI={result['rvi_value']:.2f} ≥ порога {self.rvi_high_exit_threshold} → "
                    "блокировка торговли"
                )
            })
            return result
        
        # ===== ШАГ 4: Проверка условия срабатывания по волатильности =====
        if result['market_vol'] is not None and result['market_vol'] >= self.market_vol_threshold:
            result.update({
                'triggered': True,
                'stage': 'volatility',
                'rationale': (
                    f"Волатильность рынка={result['market_vol']:.4f} ({result['market_vol']:.2%}) ≥ "
                    f"порога {self.market_vol_threshold:.4f} "
                    f"(запрошено окно={vol_window_requested}, использовано={result['used_vol_window']}) → "
                    "блокировка торговли"
                )
            })
            return result
        
        # ===== ШАГ 5: ФИЛЬТР НЕ СРАБОТАЛ =====
        rvi_info = f"RVI={result['rvi_value']:.2f} < {self.rvi_high_exit_threshold}" if result['rvi_value'] is not None else "RVI недоступен"
        vol_info = f"волатильность={result['market_vol']:.2%} < {self.market_vol_threshold:.2%}" if result['market_vol'] is not None else "волатильность недоступна"
        
        result['rationale'] = f"Фильтр пройден: {rvi_info}, {vol_info} → разрешена торговля"
        return result

# _get_trading_logic
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _get_trading_logic(self, windows: Dict[str, int]) -> TradingLogic:
        """Возвращает объект логики торговли с адаптированными параметрами."""
        common_params = {
            'risk_free_ticker': self.risk_free_ticker,
            'trend_filter_on_insufficient_data': self.trend_filter_on_insufficient_data
        }

        if self.bare_mode:
            base_logic = BareMomentumLogic(
                lookback_period=windows['lookback_period'],
                **common_params
            )
        else:
            trend_analysis_window = int(windows['lookback_period'] * 0.7) if self.use_rvi_adaptation else self.trend_window
#            trend_analysis_window = self.trend_window
#            print ("trend_analysis_window =", trend_analysis_window)
            base_logic = AdaptiveMomentumLogic(
                lookback_period=windows['lookback_period'],
                vol_window_asset=windows['vol_window_asset'],
                max_vol_threshold=self.max_vol_threshold,
                use_trend_filter=self.use_trend_filter,
                trend_analysis_window=trend_analysis_window,
                **common_params
            )

        # 🔑 ДОБАВЛЕНИЕ АБСОЛЮТНОГО ИМПУЛЬСА
        from .trading_logics.absolute_momentum_wrapper import AbsoluteMomentumWrapper
        wrapped_logic = AbsoluteMomentumWrapper(
            base_logic=base_logic,
            lookback_period=windows['lookback_period'],
            risk_free_ticker=self.risk_free_ticker
        )
        return wrapped_logic
# -----------------------------------------------------------------------------

    # def _get_trading_logic(self, windows: Dict[str, int]) -> TradingLogic:
    #     """Возвращает объект логики торговли с адаптированными параметрами."""
    #     common_params = {
    #         'risk_free_ticker': self.risk_free_ticker,
    #         'trend_filter_on_insufficient_data': self.trend_filter_on_insufficient_data
    #     }
        
    #     if self.bare_mode:
    #         return BareMomentumLogic(
    #             lookback_period=windows['lookback_period'],
    #             **common_params
    #         )
    #     else:
    #         trend_analysis_window = windows['lookback_period'] if self.use_rvi_adaptation else self.trend_window
    #         return AdaptiveMomentumLogic(
    #             lookback_period=windows['lookback_period'],
    #             vol_window_asset=windows['vol_window_asset'],
    #             max_vol_threshold=self.max_vol_threshold,
    #             use_trend_filter=self.use_trend_filter,
    #             trend_analysis_window=trend_analysis_window,
    #             **common_params
    #         )

    def generate_signal(
        self,
        data_dict: Dict[str, pd.DataFrame],
        market_data: Optional[pd.DataFrame] = None,
        rvi_data: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> Dict:
        """
        Генерирует торговый сигнал с ПОСЛЕДОВАТЕЛЬНОСТЬЮ:
        1. Извлечение значения RVI
        2. Определение уровня волатильности и адаптация окон
        3. Применение рыночного фильтра с адаптированным окном
        4. Выбор актива (если фильтр не сработал)
        
        КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: Адаптация окон теперь происходит ДО рыночного фильтра,
        что позволяет rvi_low_multiplier влиять на расчёт рыночной волатильности.
        """
        # 🔑 ШАГ 1: Извлечение значения RVI
        rvi_value = None
        if rvi_data is not None and not rvi_data.empty:
            rvi_value = float(rvi_data['CLOSE'].iloc[-1])
        
        # 🔑 ШАГ 2: Определение уровня RVI и адаптация окон
        rvi_level = self._get_rvi_level(rvi_value)
        windows = self._get_adaptive_windows(rvi_level)
        
        # 🔑 ШАГ 3: Рыночный фильтр с адаптированным окном волатильности
        market_filter_result = self.market_filter(
            market_data, 
            rvi_data,
            vol_window_override=windows['vol_window_market']  # ← КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ
        )
        
        # Диагностика срабатывания фильтра (опционально)
        if self.debug and market_filter_result['triggered']:
            print(f"[DEBUG] Рыночный фильтр сработал на этапе '{market_filter_result['stage']}': "
                  f"{market_filter_result['rationale']}")
        
        if market_filter_result['triggered']:
            return { 
                'selected': self.risk_free_ticker,
                'market_filter_triggered': True,
                'market_filter_stage': market_filter_result['stage'],
                'market_filter_rationale': market_filter_result['rationale'],
                'used_market_vol_window': market_filter_result.get('used_vol_window'),
                'rvi_level': rvi_level,
                'rvi_value': rvi_value
            }
        
        # 🔑 ШАГ 4: Выбор актива с адаптированными окнами
        trading_logic = self._get_trading_logic(windows)
        selected_ticker = trading_logic.select_best_asset(data_dict)
        
        return {
            'selected': selected_ticker,
            'market_filter_triggered': False,
            'market_filter_rationale': market_filter_result['rationale'],
            'used_market_vol_window': market_filter_result.get('used_vol_window'),
            'rvi_level': rvi_level,
            'rvi_value': rvi_value
        }
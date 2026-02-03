# backtest_platform/strategies/dual_momentum.py

"""
Файл содержит определение класса DualMomentumStrategy для применения двойной 
стратегии момента в бэктестере.

Версия: 1.0.0 (с поддержкой диагностики рыночного фильтра)
КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
1. Рыночный фильтр теперь КОРРЕКТНО использует market_vol_window (не base_vol_window).
2. Добавлена логика "падения" на максимально доступное окно при недостатке данных.
3. Устранена ошибка: фильтр по волатильности теперь срабатывает даже при больших окнах.
4. Добавлено диагностическое логгирование для отладки (опционально включается через debug=True).
"""

from backtest_platform.core.base_strategy import BaseStrategy
from backtest_platform.indicators.volatility import rolling_volatility
from .trading_logics.bare_momentum_logic import BareMomentumLogic
from .trading_logics.adaptive_momentum_logic import AdaptiveMomentumLogic
from .trading_logics.base_logic import TradingLogic
import pandas as pd
import numpy as np
import warnings

__version__ = "1.0.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-02"

class DualMomentumStrategy(BaseStrategy):
    """
    Фасад для стратегии двойного момента с корректной реализацией рыночного фильтра.
    
    КЛЮЧЕВОЕ ИЗМЕНЕНИЕ:
    Рыночная волатильность рассчитывается ТОЛЬКО через market_vol_window с защитой
    от недостатка данных (используется максимально доступное окно, минимум 5 дней).
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
        debug=False  # ← НОВЫЙ ПАРАМЕТР ДЛЯ ДИАГНОСТИКИ
    ):
        self.base_lookback = base_lookback
        self.base_vol_window = base_vol_window
        self.market_vol_window = market_vol_window or base_vol_window
        
        # 🔍 ДИАГНОСТИКА ШАГ 1.1 — ДОБАВИТЬ ЭТУ СТРОКУ:
        # print(f"INIT: market_vol_window={self.market_vol_window}, base_vol_window={self.base_vol_window}")
        
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
        self.debug = debug  # ← ВКЛЮЧАЕТ ДИАГНОСТИЧЕСКОЕ ЛОГГИРОВАНИЕ
        
        if self.market_vol_window == self.base_vol_window and market_vol_window is None:
            warnings.warn(
                f"Внимание: market_vol_window ({self.market_vol_window}) совпадает с base_vol_window ({self.base_vol_window}). "
                "Рекомендуется использовать разные окна для рыночной и активной волатильности.",
                UserWarning
            )

    def _get_rvi_level(self, rvi_value):
        if rvi_value is None:
            return 'medium'
        if rvi_value < self.rvi_low_threshold:
            return 'low'
        elif rvi_value < self.rvi_medium_threshold:
            return 'medium'
        else:
            return 'high'

    def _get_adaptive_windows(self, rvi_level):
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
        if len(prices) < window:
            return self.trend_filter_on_insufficient_data == 'allow'
        
        x = np.arange(window)
        y = prices.iloc[-window:].values
        
        if np.any(np.isnan(y)) or np.any(np.isinf(y)):
            return self.trend_filter_on_insufficient_data == 'allow'
                
        slope, _ = np.polyfit(x, y, 1)
        return slope > 0

    def market_filter(self, market_data: pd.DataFrame, rvi_data: pd.DataFrame) -> dict:

        # 🔍 РАСШИРЕННАЯ ДИАГНОСТИКА — ЗАМЕНИТЕ СТАРЫЙ ПРИНТ НА ЭТОТ:
        # if not hasattr(self, '_filter_debug_count'):
        #     self._filter_debug_count = 0
        # self._filter_debug_count += 1
        # if self._filter_debug_count <= 5 or self._filter_debug_count % 100 == 0:  # Первые 5 + каждый 100-й день
        #     print(f"FILTER[{self._filter_debug_count:4d}]: market_vol_window={self.market_vol_window}, "
        #         f"market_data_len={len(market_data) if market_data is not None else 0}")

        """
        ДВУХЭТАПНЫЙ рыночный фильтр с КОРРЕКТНЫМ использованием market_vol_window.
        
        КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ:
        При недостатке данных для расчёта с запрошенным окном используется
        максимально доступное окно (но не менее 5 дней), чтобы фильтр не отключался.
        """
        result = {
            'triggered': False,
            'stage': None,
            'rvi_value': None,
            'market_vol': None,
            'used_vol_window': None,  # ← НОВОЕ ПОЛЕ ДЛЯ ДИАГНОСТИКИ
            'rationale': ''
        }
        
        # ===== ИЗВЛЕЧЕНИЕ RVI =====
        if rvi_data is not None and not rvi_data.empty:
            result['rvi_value'] = float(rvi_data['CLOSE'].iloc[-1])
        
        # ===== ЭТАП 1: Проверка RVI =====
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
        
        # ===== ЭТАП 2: Проверка волатильности РЫНКА (ТОЛЬКО market_vol_window!) =====
        vol_window_requested = self.market_vol_window
        vol_window_effective = vol_window_requested
        
        if market_data is not None and len(market_data) > 1:
            market_returns = market_data['CLOSE'].pct_change().dropna()
            available_data_points = len(market_returns)
            
            # 🔑 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: "ПАДЕНИЕ" НА МАКСИМАЛЬНО ДОСТУПНОЕ ОКНО
            if available_data_points < vol_window_requested:
                vol_window_effective = max(5, available_data_points)  # Минимум 5 дней для стабильности
                
                if self.debug:
                    print(f"⚠️  Недостаток данных: запрошено окно={vol_window_requested}, "
                          f"доступно={available_data_points} → используем окно={vol_window_effective}")
            else:
                vol_window_effective = vol_window_requested
            
            # Расчёт волатильности с ЭФФЕКТИВНЫМ окном
            if vol_window_effective >= 5:  # Минимальное разумное окно
                market_vol_series = rolling_volatility(market_returns, vol_window_effective)
                
                if not market_vol_series.empty and not pd.isna(market_vol_series.iloc[-1]):
                    market_vol = float(market_vol_series.iloc[-1])
                    result['market_vol'] = market_vol
                    result['used_vol_window'] = vol_window_effective  # ← Для диагностики
                    
                    if market_vol >= self.market_vol_threshold:
                        result.update({
                            'triggered': True,
                            'stage': 'volatility',
                            'rationale': (
                                f"Волатильность рынка={market_vol:.4f} ({market_vol:.2%}) ≥ "
                                f"порога {self.market_vol_threshold:.4f} "
                                f"(запрошено окно={vol_window_requested}, использовано={vol_window_effective}) → "
                                "блокировка торговли"
                            )
                        })
                        return result
        
        # ===== ФИЛЬТР НЕ СРАБОТАЛ =====
        rvi_info = f"RVI={result['rvi_value']:.2f} < {self.rvi_high_exit_threshold}" if result['rvi_value'] is not None else "RVI недоступен"
        vol_info = f"волатильность={result['market_vol']:.2%} < {self.market_vol_threshold:.2%}" if result['market_vol'] is not None else "волатильность недоступна"
        
        result['rationale'] = f"Фильтр пройден: {rvi_info}, {vol_info} → разрешена торговля"
     
         # ДОБАВИТЬ ПЕРЕД ВОЗВРАТОМ РЕЗУЛЬТАТА:
        # if self._filter_debug_count <= 5 or self._filter_debug_count % 100 == 0:
        #     print(f"  → triggered={result['triggered']}, stage={result['stage']}, "
        #         f"market_vol={result['market_vol']:.4f} if available, "
        #         f"used_window={result.get('used_vol_window', 'N/A')}")
     
        return result

    def _get_trading_logic(self, windows: dict) -> TradingLogic:
        common_params = {
            'risk_free_ticker': self.risk_free_ticker,
            'trend_filter_on_insufficient_data': self.trend_filter_on_insufficient_data
        }
        
        if self.bare_mode:
            return BareMomentumLogic(
                lookback_period=windows['lookback_period'],
                **common_params
            )
        else:
            trend_analysis_window = windows['lookback_period'] if self.use_rvi_adaptation else self.trend_window
            return AdaptiveMomentumLogic(
                lookback_period=windows['lookback_period'],
                vol_window_asset=windows['vol_window_asset'],
                max_vol_threshold=self.max_vol_threshold,
                use_trend_filter=self.use_trend_filter,
                trend_analysis_window=trend_analysis_window,
                **common_params
            )

    def generate_signal(self, data_dict, market_data=None, rvi_data=None, **kwargs):
        market_filter_result = self.market_filter(market_data, rvi_data)
        
        # 🔑 ДИАГНОСТИКА: Логгирование срабатывания фильтра (опционально)
        if self.debug and market_filter_result['triggered']:
            print(f"[DEBUG] Рыночный фильтр сработал на этапе '{market_filter_result['stage']}': "
                  f"{market_filter_result['rationale']}")
        
        if market_filter_result['triggered']:
            return { 
                'selected': self.risk_free_ticker,
                'market_filter_triggered': True,
                'market_filter_stage': market_filter_result['stage'],
                'market_filter_rationale': market_filter_result['rationale'],
                'used_market_vol_window': market_filter_result.get('used_vol_window')  # ← Для отладки
            }

        rvi_value = market_filter_result.get('rvi_value')
        rvi_level = self._get_rvi_level(rvi_value)
        windows = self._get_adaptive_windows(rvi_level)

        trading_logic = self._get_trading_logic(windows)
        selected_ticker = trading_logic.select_best_asset(data_dict)

        return {
            'selected': selected_ticker,
            'market_filter_triggered': False,
            'market_filter_rationale': market_filter_result['rationale'],
            'used_market_vol_window': market_filter_result.get('used_vol_window')
        }
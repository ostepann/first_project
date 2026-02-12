"""
ЕДИНАЯ ТОЧКА ВХОДА ДЛЯ КОНФИГУРАЦИИ СТРАТЕГИИ DUAL MOMENTUM

Версия: 1.0.0
Дата обновления: 2026-02-13
Автор: Oleg Dev

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА КОНФИГУРАЦИИ: ЧЁТКОЕ РАЗДЕЛЕНИЕ ОТВЕТСТВЕННОСТИ
═══════════════════════════════════════════════════════════════════════════════
┌──────────────────────┬──────────────────────────────────────────────────────┐
│ Файл                 │ Ответственность                                      │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ common_cfg.py        │ Инфраструктура: пути, тикеры, комиссии, данные       │
│                      │ → Не зависит от логики стратегии                     │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ strategy_defaults.py │ Базовая архитектура стратегии: пороги RVI, флаги     │
│                      │ → Определяет структуру, но не конкретные значения    │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ production_cfg.py    │ Итоговые параметры для реальной торговли             │
│                      │ → Результат финальной оптимизации                    │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ optimization_cfg.py  │ Сетки значений для поиска оптимума                   │
│                      │ → Используется только в процессе оптимизации         │
└──────────────────────┴──────────────────────────────────────────────────────┘

ПРЕИМУЩЕСТВА АРХИТЕКТУРЫ:
  ✓ Единая точка правды — все параметры в одном месте
  ✓ Защита от случайного изменения продакшн-параметров при оптимизации
  ✓ Чёткая документация каждого параметра с экономическим обоснованием
  ✓ Предотвращение критических ошибок (разделение окон волатильности)
  ✓ Простая миграция между окружениями (тест → продакшен)

РЕКОМЕНДУЕМЫЙ СПОСОБ ИМПОРТА:
  # Для бэктеста с продакшн-параметрами:
  from config import production_params, tickers, commission, initial_capital

  # Для оптимизации:
  from config import param_grid, quick_optimization_grid, optimization_settings

  # Для доступа ко всем параметрам:
  from config import *
"""

__version__ = "1.0.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-13"

# ======================
# ИМПОРТ ИЗ ОБЩЕЙ КОНФИГУРАЦИИ
# ======================

from .common_cfg import (
    # Системные параметры
    data_dir, results_dir, cache_dir,
    
    # Тикеры и рыночные инструменты
    tickers, market_ticker, rvi_ticker, risk_free_ticker,
    
    # Временные параметры
    start_date, end_date, initial_capital,
    rebalance_frequency, time_filter_enabled,
    trading_start_time, trading_end_time,
    
    # Издержки торговли
    commission, default_commission, commission_rate,
    slippage, default_slippage, use_slippage,
    use_variable_commission,
    
    # Конвертеры волатильности
    ANNUAL_TO_DAILY, DAILY_TO_ANNUAL,
    
    # Метаданные и предупреждения
    config_version, last_updated,
    CRITICAL_WARNING_COMMON
)

# ======================
# ИМПОРТ БАЗОВОЙ ЛОГИКИ СТРАТЕГИИ
# ======================

from .strategy_defaults import (
    # Пороги RVI для адаптации режимов
    rvi_low_threshold, rvi_medium_threshold, rvi_high_exit_threshold,
    
    # Множители адаптации окон
    rvi_low_multiplier, rvi_high_multiplier,
    
    # Параметры трендового фильтра
    trend_window, trend_r_squared_threshold,
    trend_filter_on_insufficient_data,
    
    # Флаги режимов работы
    use_rvi_adaptation, use_trend_filter, bare_mode,
    
    # Сборка базовой конфигурации
    strategy_defaults,
    
    # Метаданные и предупреждения
    STRATEGY_ARCHITECTURE_VERSION, LAST_CALIBRATED, CALIBRATION_PERIOD,
    CRITICAL_WARNING_STRATEGY
)

# ======================
# ИМПОРТ ПРОИЗВОДСТВЕННЫХ ПАРАМЕТРОВ
# ======================

from .production_cfg import (
    # Оптимизированные параметры
    BASE_LOOKBACK, BASE_VOL_WINDOW, MARKET_VOL_WINDOW,
    MAX_VOL_THRESHOLD, MARKET_VOL_THRESHOLD,
    
    # Итоговая конфигурация для продакшена
    production_params,
    
    # Метаданные для аудита
    production_metadata,
    
    # Практические рекомендации и предупреждения
    TRADING_RECOMMENDATIONS, CRITICAL_WARNING_PRODUCTION
)

# ======================
# ИМПОРТ СЕТОК ОПТИМИЗАЦИИ
# ======================

from .optimization_cfg import (
    # Сетки параметров
    param_grid, quick_optimization_grid,
    
    # Настройки алгоритма оптимизации
    optimization_settings,
    
    # Диагностические параметры
    sensitivity_analysis_params,
    
    # Метаданные оптимизации
    OPTIMIZATION_METADATA, OPTIMIZATION_GUIDELINES
)

# ======================
# ЕДИНЫЙ ИНТЕРФЕЙС ДЛЯ ИМПОРТА
# ======================

__all__ = [
    # common_cfg.py
    'data_dir', 'results_dir', 'cache_dir',
    'tickers', 'market_ticker', 'rvi_ticker', 'risk_free_ticker',
    'start_date', 'end_date', 'initial_capital',
    'rebalance_frequency', 'time_filter_enabled',
    'trading_start_time', 'trading_end_time',
    'commission', 'default_commission', 'commission_rate',
    'slippage', 'default_slippage', 'use_slippage',
    'use_variable_commission',
    'ANNUAL_TO_DAILY', 'DAILY_TO_ANNUAL',
    'config_version', 'last_updated',
    'CRITICAL_WARNING_COMMON',
    
    # strategy_defaults.py
    'rvi_low_threshold', 'rvi_medium_threshold', 'rvi_high_exit_threshold',
    'rvi_low_multiplier', 'rvi_high_multiplier',
    'trend_window', 'trend_r_squared_threshold',
    'trend_filter_on_insufficient_data',
    'use_rvi_adaptation', 'use_trend_filter', 'bare_mode',
    'strategy_defaults',
    'STRATEGY_ARCHITECTURE_VERSION', 'LAST_CALIBRATED', 'CALIBRATION_PERIOD',
    'CRITICAL_WARNING_STRATEGY',
    
    # production_cfg.py
    'BASE_LOOKBACK', 'BASE_VOL_WINDOW', 'MARKET_VOL_WINDOW',
    'MAX_VOL_THRESHOLD', 'MARKET_VOL_THRESHOLD',
    'production_params',
    'production_metadata',
    'TRADING_RECOMMENDATIONS', 'CRITICAL_WARNING_PRODUCTION',
    
    # optimization_cfg.py
    'param_grid', 'quick_optimization_grid',
    'optimization_settings',
    'sensitivity_analysis_params',
    'OPTIMIZATION_METADATA', 'OPTIMIZATION_GUIDELINES',
]

# ======================
# ГЛОБАЛЬНЫЕ ПРЕДУПРЕЖДЕНИЯ ПРИ ИМПОРТЕ
# ======================

import warnings

# Критическое предупреждение о разделении окон волатильности
warnings.warn(
    "⚠️  КРИТИЧЕСКИ ВАЖНО: Параметры base_vol_window и market_vol_window "
    "ДОЛЖНЫ иметь разные значения (короткое окно для активов, длинное для рынка). "
    "Нарушение этого правила приводит к деградации рыночного фильтра. "
    "Рекомендуемые значения: base_vol_window=9, market_vol_window=21",
    UserWarning,
    stacklevel=2
)

# Предупреждение о годовых порогах волатильности
warnings.warn(
    "⚠️  ПОРОГИ ВОЛАТИЛЬНОСТИ (market_vol_threshold, max_vol_threshold) "
    "указаны в ГОДОВЫХ значениях, а не ежедневных. "
    "Пример: 0.35 = 35% годовой волатильности ≈ 2.2% дневной.",
    UserWarning,
    stacklevel=2
)

# ======================
# ВЕРСИОННАЯ ИНФОРМАЦИЯ
# ======================

CONFIG_SYSTEM_VERSION = "1.0.0"
CONFIG_SYSTEM_DATE = "2026-02-13"
CONFIG_SYSTEM_AUTHOR = "Oleg Dev"

print(f"✅ Загружена система конфигурации v{CONFIG_SYSTEM_VERSION} ({CONFIG_SYSTEM_DATE})")
print(f"   Автор: {CONFIG_SYSTEM_AUTHOR}")
print(f"   Архитектура: Единая точка правды с разделением ответственности")
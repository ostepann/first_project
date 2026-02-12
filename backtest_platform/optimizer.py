"""
ОПТИМИЗАТОР ДЛЯ СТРАТЕГИИ DUAL MOMENTUM НА МОСБИРЖЕ

Версия: 1.3.1 (исправление синтаксической ошибки в аннотации типа)
Дата обновления: 2026-02-13
Автор: Oleg Dev

═══════════════════════════════════════════════════════════════════════════════
ИСПРАВЛЕНИЕ КРИТИЧЕСКОЙ ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════
Строка 109 содержала синтаксическую ошибку в аннотации типа:
  ❌ Было:  market_ pd.DataFrame
  ✅ Стало: market_data: pd.DataFrame

Ошибка вызывала сбой статического анализатора (Pylance) и потенциальный
крах при выполнении из-за некорректного синтаксиса аннотаций типов.
"""

__version__ = "1.3.1"
__author__ = "Oleg Dev"
__date__ = "2026-02-13"

import itertools
import pandas as pd
import warnings
from typing import Dict, Optional, List, Callable

from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy

# 🔑 ИМПОРТ ИЗДЕРЖЕК ИЗ МОДУЛЬНОЙ КОНФИГУРАЦИИ
from config import (
    commission as DEFAULT_COMMISSION,
    default_commission as DEFAULT_COMMISSION_FALLBACK,
    slippage as DEFAULT_SLIPPAGE,
    default_slippage as DEFAULT_SLIPPAGE_FALLBACK,
    use_slippage as DEFAULT_USE_SLIPPAGE,
    ANNUAL_TO_DAILY,
    CRITICAL_WARNING_COMMON
)


def _validate_volatility_windows(param_combo: Dict) -> bool:
    """
    Валидация критического правила: разделение окон волатильности.
    
    Правило: base_vol_window ДОЛЖЕН быть строго меньше market_vol_window
    (минимальный разрыв 5 дней для семантического разделения).
    """
    base_win = param_combo.get('base_vol_window')
    market_win = param_combo.get('market_vol_window')
    
    if base_win is not None and market_win is not None:
        if base_win >= market_win:
            return False
        if market_win - base_win < 5:
            warnings.warn(
                f"⚠️  Малый разрыв между окнами: base_vol_window={base_win}, "
                f"market_vol_window={market_win} (разрыв <5 дней). "
                "Рекомендуется разрыв ≥12 дней для стабильной работы фильтров.",
                UserWarning,
                stacklevel=3
            )
    return True


def _format_error_context(params: Dict, error: Exception) -> str:
    """Форматирование контекста ошибки для логирования."""
    param_str = ", ".join([f"{k}={v}" for k, v in params.items() if v is not None])
    return f"Параметры: {{{param_str}}} | Ошибка: {str(error)[:100]}"


def optimize_dual_momentum(
    data_dict: Dict[str, pd.DataFrame],
    market_data: pd.DataFrame,  # ✅ ИСПРАВЛЕНО: добавлено двоеточие после имени параметра
    rvi_data: Optional[pd.DataFrame] = None,
    param_grid: Optional[Dict[str, List]] = None,
    commission: Optional[float] = None,
    default_commission: Optional[float] = None,
    slippage: Optional[float] = None,
    use_slippage: Optional[bool] = None,
    initial_capital: float = 100_000,
    trade_time_filter: Optional[str] = None,
    skip_invalid_windows: bool = True,
    progress_callback: Optional[Callable] = None
) -> pd.DataFrame:
    """
    Оптимизация стратегии Dual Momentum через перебор комбинаций параметров.
    
    КРИТИЧЕСКИ ВАЖНО:
      • Все пороги волатильности указываются в ГОДОВЫХ значениях
      • Для конвертации: дневная_вол = годовая_вол × √252
    
    Аргументы:
        data_dict: Словарь данных по активам {тикер: DataFrame}
        market_data: pd.DataFrame — ДАННЫЕ РЫНОЧНОГО ИНДЕКСА (исправлено)
        rvi_data: Данные индекса волатильности РТС (опционально)
        ... остальные параметры без изменений ...
    
    Возвращает:
        pd.DataFrame: Отсортированный по Sharpe Ratio
    """
    # === ВАЛИДАЦИЯ ВХОДНЫХ ДАННЫХ ===
    if not data_dict:
        raise ValueError("data_dict не может быть пустым")
    if market_data is None or market_data.empty:
        raise ValueError("market_data обязателен и не может быть пустым")
    
    # === НАСТРОЙКА ИЗДЕРЖЕК ===
    commission = commission if commission is not None else DEFAULT_COMMISSION
    default_commission = default_commission if default_commission is not None else DEFAULT_COMMISSION_FALLBACK
    slippage = slippage if slippage is not None else DEFAULT_SLIPPAGE
    use_slippage = use_slippage if use_slippage is not None else DEFAULT_USE_SLIPPAGE
    
    # === СЕТКА ПАРАМЕТРОВ ПО УМОЛЧАНИЮ ===
    if param_grid is None:
        param_grid = {
            'base_lookback': [20, 25, 30],
            'base_vol_window': [8, 10, 12],
            'market_vol_window': [21, 30, 40],
            'max_vol_threshold': [0.30, 0.35, 0.40],
            'market_vol_threshold': [0.30, 0.35, 0.40]
        }
    
    # === ПОДГОТОВКА К ПЕРЕБОРУ ===
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    total_combinations = len(list(itertools.product(*values)))
    
    print(f"\n🔍 НАЧАЛО ОПТИМИЗАЦИИ")
    print(f"   Количество комбинаций: {total_combinations:,}")
    print(f"   Издержки: комиссия={commission:.2%}, проскальзывание={slippage:.2%} (использовать={use_slippage})")
    print(f"   Капитал: {initial_capital:,.0f} ₽")
    print(f"   ⚠️  {CRITICAL_WARNING_COMMON}")
    
    # Проверка потенциальных нарушений правила окон
    if 'base_vol_window' in param_grid and 'market_vol_window' in param_grid:
        min_base = min(param_grid['base_vol_window'])
        max_market = max(param_grid['market_vol_window'])
        if min_base >= max_market:
            warning_msg = (
                f"⚠️  ПОТЕНЦИАЛЬНОЕ НАРУШЕНИЕ ПРАВИЛА: "
                f"min(base_vol_window)={min_base} ≥ max(market_vol_window)={max_market}\n"
                f"   Рекомендуется: base_vol_window < market_vol_window (мин. разрыв 5 дней)"
            )
            print(f"   {warning_msg}")
            if not skip_invalid_windows:
                raise ValueError(warning_msg)
    
    results = []
    invalid_count = 0
    error_count = 0
    
    # === ПЕРЕБОР КОМБИНАЦИЙ ===
    for idx, combo in enumerate(itertools.product(*values), 1):
        params = dict(zip(keys, combo))
        
        # 🔑 ВАЛИДАЦИЯ КРИТИЧЕСКОГО ПРАВИЛА
        if skip_invalid_windows and not _validate_volatility_windows(params):
            invalid_count += 1
            continue
        
        strategy = DualMomentumStrategy(**params)
        
        bt = Backtester(
            commission=commission,
            default_commission=default_commission,
            slippage=slippage,
            use_slippage=use_slippage,
            trade_time_filter=trade_time_filter
        )
        
        try:
            res = bt.run(
                strategy,
                data_dict,
                market_data=market_data,  # ✅ Корректная передача параметра
                rvi_data=rvi_data,
                initial_capital=initial_capital
            )
            
            # 🔑 ЯВНОЕ СОХРАНЕНИЕ параметров адаптации под RVI + диагностических полей
            result_row = {
                **params,
                'rvi_low_multiplier': getattr(strategy, 'rvi_low_multiplier', None),
                'rvi_high_multiplier': getattr(strategy, 'rvi_high_multiplier', None),
                'rvi_low_threshold': getattr(strategy, 'rvi_low_threshold', None),
                'rvi_medium_threshold': getattr(strategy, 'rvi_medium_threshold', None),
                'rvi_high_exit_threshold': getattr(strategy, 'rvi_high_exit_threshold', None),
                'use_rvi_adaptation': getattr(strategy, 'use_rvi_adaptation', None),
                'use_trend_filter': getattr(strategy, 'use_trend_filter', None),
                'used_market_vol_window': res.get('used_market_vol_window', None),
                'total_trades': res.get('total_trades', None),
                'time_in_cash_pct': res.get('time_in_cash_pct', None),
                'final_value': res['final_value'],
                'cagr': res['cagr'],
                'sharpe': res['sharpe'],
                'max_drawdown': res['max_drawdown'],
                'calmar': res.get('calmar', None),
                'sortino': res.get('sortino', None),
                'volatility': res.get('volatility', None)
            }
            results.append(result_row)
            
            if progress_callback:
                progress_callback(idx, total_combinations, params, result_row)
            
        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"   ⚠️  Ошибка при комбинации {idx}/{total_combinations}: {_format_error_context(params, e)}")
            continue
    
    # === ПОСТ-ОБРАБОТКА РЕЗУЛЬТАТОВ ===
    if invalid_count > 0:
        print(f"   ⚠️  Пропущено комбинаций из-за нарушения правила окон: {invalid_count:,} ({invalid_count/total_combinations:.1%})")
    
    if error_count > 0:
        print(f"   ⚠️  Ошибок при бэктесте: {error_count:,} ({error_count/total_combinations:.1%})")
    
    if not results:
        if invalid_count == total_combinations:
            raise RuntimeError(
                f"Все {total_combinations:,} комбинаций отфильтрованы из-за нарушения правила "
                "разделения окон волатильности (base_vol_window ≥ market_vol_window). "
                "Измените сетку параметров или установите skip_invalid_windows=False."
            )
        raise ValueError(
            f"Ни одна комбинация параметров не прошла бэктест успешно "
            f"(всего попыток: {total_combinations:,}, ошибок: {error_count:,}). "
            "Проверьте корректность данных и параметров стратегии."
        )
    
    df = pd.DataFrame(results)
    
    # Гарантируем наличие критических колонок
    for col in ['rvi_low_multiplier', 'used_market_vol_window', 'sharpe']:
        if col not in df.columns:
            df[col] = None
    
    df = df.sort_values('sharpe', ascending=False).reset_index(drop=True)
    
    print(f"✅ ОПТИМИЗАЦИЯ ЗАВЕРШЕНА: {len(df):,} успешных комбинаций из {total_combinations:,} попыток")
    print(f"   Лучший Sharpe: {df['sharpe'].max():.4f} | Худший Sharpe: {df['sharpe'].min():.4f}")
    print(f"   Медианный Sharpe: {df['sharpe'].median():.4f}")
    
    return df


# ======================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ======================

def analyze_parameter_sensitivity(results_df: pd.DataFrame, parameter: str) -> pd.DataFrame:
    """Анализ чувствительности метрик к изменению конкретного параметра."""
    if parameter not in results_df.columns:
        raise ValueError(f"Параметр '{parameter}' отсутствует в результатах")
    
    grouped = results_df.groupby(parameter).agg({
        'sharpe': ['mean', 'median', 'max', 'min', 'std'],
        'cagr': ['mean', 'max'],
        'max_drawdown': ['mean', 'min'],
        'final_value': 'count'
    }).round(4)
    
    grouped.columns = ['_'.join(col).strip() for col in grouped.columns.values]
    grouped = grouped.rename(columns={'final_value_count': 'combinations'})
    grouped = grouped.sort_values('sharpe_mean', ascending=False)
    
    return grouped


def filter_optimal_parameters(
    results_df: pd.DataFrame,
    max_drawdown_limit: float = 0.25,
    min_sharpe: float = 0.7,
    min_cagr: float = 0.10
) -> pd.DataFrame:
    """Фильтрация результатов оптимизации по риск-ограничениям."""
    filtered = results_df[
        (results_df['max_drawdown'] <= max_drawdown_limit) &
        (results_df['sharpe'] >= min_sharpe) &
        (results_df['cagr'] >= min_cagr)
    ].copy()
    
    print(f"Фильтрация результатов:")
    print(f"  Исходное количество: {len(results_df):,}")
    print(f"  После фильтрации: {len(filtered):,} ({len(filtered)/len(results_df):.1%})")
    print(f"  Ограничения: max_dd ≤ {max_drawdown_limit:.0%}, sharpe ≥ {min_sharpe:.2f}, cagr ≥ {min_cagr:.0%}")
    
    return filtered.sort_values('sharpe', ascending=False)


# ======================
# МЕТАДАННЫЕ МОДУЛЯ
# ======================

OPTIMIZER_METADATA = {
    'version': __version__,
    'author': __author__,
    'date': __date__,
    'critical_rules': [
        'base_vol_window < market_vol_window (мин. разрыв 5 дней)',
        'Пороги волатильности указываются в ГОДОВЫХ значениях',
        'Рекомендуемый разрыв окон: 12+ дней (9 дней для активов, 21 день для рынка)'
    ],
    'default_costs': {
        'commission': DEFAULT_COMMISSION,
        'slippage': DEFAULT_SLIPPAGE,
        'use_slippage': DEFAULT_USE_SLIPPAGE
    }
}
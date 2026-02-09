"""
Оптимизатор для стратегии Dual Momentum.
Версия: 1.2.0
Изменения:
- Явное сохранение параметров адаптации под RVI (rvi_low_multiplier и др.)
- Сохранение диагностического поля used_market_vol_window для верификации влияния адаптации на рыночный фильтр
- Импорт настроек из optimization_config для единой точки управления издержками
"""

import itertools
import pandas as pd
from core.backtester import Backtester
import optimization_config as cfg

# Метаданные модуля
__version__ = "1.2.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-08"

def optimize_dual_momentum(
    data_dict,
    market_data,
    rvi_data=None,
    param_grid=None,
    commission=None,
    initial_capital=100_000,
    trade_time_filter=None
):
    """
    Оптимизация Dual Momentum стратегии с поддержкой RVI и адаптивных окон.
    
    Args:
        data_dict: dict, данные по активам
        market_data: pd.DataFrame, рыночные данные (например, EQMX)
        rvi_data: pd.DataFrame, данные RVI (опционально)
        param_grid: dict, параметры для оптимизации
        commission: dict, комиссия по инструментам (если None, берётся из конфига)
        initial_capital: float, стартовый капитал
        trade_time_filter: str, например '12:00:00'
    
    Returns:
        pd.DataFrame, отсортированный по Sharpe с сохранёнными параметрами адаптации RVI
    """
    from strategies.dual_momentum import DualMomentumStrategy

    # Сетка параметров по умолчанию (если не передана)
    if param_grid is None:
        param_grid = {
            'base_lookback': [3, 5, 10, 20, 50, 100],
            'base_vol_window': [3, 5, 15, 20, 25],
            'max_vol_threshold': [0.3, 0.35, 0.4]
        }

    results = []
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        strategy = DualMomentumStrategy(**params)
        
        bt = Backtester(
            commission=commission or cfg.commission,
            default_commission=cfg.default_commission,
            slippage=cfg.slippage,
            use_slippage=cfg.use_slippage,
            trade_time_filter=trade_time_filter
        )
        try:
            res = bt.run(
                strategy,
                data_dict,
                market_data=market_data,
                rvi_data=rvi_data,
                initial_capital=initial_capital
            )
            
            # 🔑 ЯВНОЕ СОХРАНЕНИЕ параметров адаптации под RVI + диагностического поля
            # Даже если параметр не был в param_grid (использовалось значение по умолчанию),
            # он будет сохранён из экземпляра стратегии
            result_row = {
                **params,
                # Параметры адаптации RVI (гарантированно сохраняются)
                'rvi_low_multiplier': getattr(strategy, 'rvi_low_multiplier', None),
                'rvi_high_multiplier': getattr(strategy, 'rvi_high_multiplier', None),
                'rvi_low_threshold': getattr(strategy, 'rvi_low_threshold', None),
                'rvi_medium_threshold': getattr(strategy, 'rvi_medium_threshold', None),
                'rvi_high_exit_threshold': getattr(strategy, 'rvi_high_exit_threshold', None),
                'use_rvi_adaptation': getattr(strategy, 'use_rvi_adaptation', None),
                # Диагностическое поле: подтверждает влияние мультипликатора на рыночный фильтр
                'used_market_vol_window': res.get('used_market_vol_window', None),
                # Метрики эффективности
                'final_value': res['final_value'],
                'cagr': res['cagr'],
                'sharpe': res['sharpe'],
                'max_drawdown': res['max_drawdown']
            }
            results.append(result_row)
            
        except Exception as e:
            continue

    if not results:
        raise ValueError("Ни одна комбинация параметров не прошла бэктест успешно.")
    
    df = pd.DataFrame(results)
    
    # 🔑 Гарантируем наличие колонки rvi_low_multiplier в результатах даже при пустом param_grid
    if 'rvi_low_multiplier' not in df.columns:
        df['rvi_low_multiplier'] = None
    
    return df.sort_values('sharpe', ascending=False)
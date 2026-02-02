# backtest_platform/optimizer.py

"""
Оптимизатор для стратегии Dual Momentum.
Версия: 1.1.0
Изменения:
- Импорт настроек из optimization_config для единой точки управления издержками.
- Поддержка полной конфигурации проскальзывания и комиссий.
"""

import itertools
import pandas as pd
from core.backtester import Backtester
import optimization_config as cfg  # ← ДОБАВЛЕН ИМПОРТ

# Метаданные модуля
__version__ = "1.1.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-01"

def optimize_dual_momentum(
    data_dict,
    market_data,
    rvi_data=None,
    param_grid=None,
    commission=None,  # ← Этот аргумент всё ещё можно передавать для гибкости
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
        pd.DataFrame, отсортированный по Sharpe
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
        
        # 🔑 Теперь все настройки издержек берутся из единого источника — cfg
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
            results.append({
                **params,
                'final_value': res['final_value'],
                'cagr': res['cagr'],
                'sharpe': res['sharpe'],
                'max_drawdown': res['max_drawdown']
            })
        except Exception as e:
            continue

    if not results:
        raise ValueError("Ни одна комбинация параметров не прошла бэктест успешно.")
    
    df = pd.DataFrame(results)
    return df.sort_values('sharpe', ascending=False)
# backtest_platform/optimizer.py

import itertools
import pandas as pd
from core.backtester import Backtester

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
        commission: dict, комиссия по инструментам
        initial_capital: float, стартовый капитал
        trade_time_filter: str, например '12:00:00'
    
    Returns:
        pd.DataFrame, отсортированный по Sharpe
    """
    from strategies.dual_momentum import DualMomentumStrategy

    # Сетка параметров по умолчанию (если не передана)
    if param_grid is None:
        param_grid = {
            'base_lookback': [100, 126, 150],
            'base_vol_window': [15, 20, 25],
            'max_vol_threshold': [0.3, 0.35, 0.4]
        }

    results = []
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        strategy = DualMomentumStrategy(**params)
        bt = Backtester(
            commission=commission or {},
            default_commission=0.0,
            slippage=0.001,
            use_slippage=True,
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
            # Для отладки можно раскомментировать:
            # print(f"Пропущена комбинация {params}: {str(e)}")
            continue

    if not results:
        raise ValueError("Ни одна комбинация параметров не прошла бэктест успешно.")
    
    df = pd.DataFrame(results)
    return df.sort_values('sharpe', ascending=False)

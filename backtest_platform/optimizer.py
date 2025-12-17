import itertools
import pandas as pd
from core.backtester import Backtester

def optimize_dual_momentum(
    data_dict,
    market_data,
    param_grid,
    commission=None,
    initial_capital=100_000,
    trade_time_filter=None
):
    from strategies.dual_momentum import DualMomentumStrategy

    results = []
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        strategy = DualMomentumStrategy(**params)
        bt = Backtester(
            commission=commission or {},
            trade_time_filter=trade_time_filter
        )
        try:
            res = bt.run(strategy, data_dict, market_data, initial_capital)
            results.append({
                **params,
                'final_value': res['final_value'],
                'cagr': res['cagr'],
                'sharpe': res['sharpe'],
                'max_drawdown': res['max_drawdown']
            })
        except Exception as e:
            continue

    df = pd.DataFrame(results)
    return df.sort_values('sharpe', ascending=False)

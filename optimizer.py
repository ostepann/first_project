import itertools
import pandas as pd
import numpy as np
from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy

def optimize_dual_momentum(
    data,
    market_data,
    lookback_range=(60, 180, 10),
    vol_window_range=(10, 30, 5),
    vol_threshold_range=(0.2, 0.5, 0.05),
    commission=None
):
    results = []
    for lb in range(*lookback_range) if isinstance(lookback_range, tuple) else lookback_range:
        for vw in range(*vol_window_range) if isinstance(vol_window_range, tuple) else vol_window_range:
            for vt in np.arange(*vol_threshold_range):
                strategy = lambda df_dict, market_df: DualMomentumStrategy(
                    lookback_period=lb,
                    vol_window=vw,
                    max_vol_threshold=vt
                ).generate_signal(df_dict, market_df)

                bt = Backtester(commission=commission or {})
                res = bt.run(strategy, data, market_data)

                # Метрики
                pv = res['portfolio_value']
                returns = pv['value'].pct_change().dropna()
                sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() != 0 else 0
                dd = (pv['value'] / pv['value'].cummax() - 1).min()
                cagr = (pv['value'].iloc[-1] / pv['value'].iloc[0]) ** (252 / len(pv)) - 1

                results.append({
                    'lookback': lb,
                    'vol_window': vw,
                    'vol_threshold': round(vt, 3),
                    'cagr': cagr,
                    'sharpe': sharpe,
                    'max_dd': dd,
                    'final_value': res['final_value']
                })

    return pd.DataFrame(results).sort_values('sharpe', ascending=False)
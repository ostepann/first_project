import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy
from optimizer import optimize_dual_momentum
from utils import load_market_data

def main():
    # Синтетические данные (замените на реальные CSV)
    dates = pd.date_range('2020-01-01', '2024-12-31', freq='D')
    data = {}
    for ticker in ['GOLD', 'EQMX', 'OBLG', 'LQDT']:
        df = pd.DataFrame({
            'TRADEDATE': dates,
            'OPEN': 100 + (pd.Series([0.001] * len(dates)).cumsum() + pd.Series(pd.np.random.randn(len(dates)) * 0.01)).cumsum(),
            'HIGH': 100 + (pd.Series([0.001] * len(dates)).cumsum() + pd.Series(pd.np.random.randn(len(dates)) * 0.01)).cumsum() + 0.5,
            'LOW': 100 + (pd.Series([0.001] * len(dates)).cumsum() + pd.Series(pd.np.random.randn(len(dates)) * 0.01)).cumsum() - 0.5,
            'CLOSE': 100 + (pd.Series([0.001] * len(dates)).cumsum() + pd.Series(pd.np.random.randn(len(dates)) * 0.01)).cumsum(),
            'VOLUME': pd.np.random.randint(1000, 10000, len(dates))
        })
        data[ticker] = df

    market_df = data['EQMX'].copy()

    # Бэктест
    strategy = DualMomentumStrategy(
        lookback_period=126,
        vol_window=20,
        max_vol_threshold=0.35
    )
    bt = Backtester(
        commission={'EQMX': 0.005, 'OBLG': 0.003, 'GOLD': 0.006},
        default_commission=0.0,
        slippage=0.001,
        use_slippage=True,
        trade_time_filter='12:00:00'  # если в данных есть время
    )
    result = bt.run(strategy, data, market_data=market_df)

    print("Бэктест завершён:")
    print(f"Финальная стоимость: {result['final_value']:,.2f}")
    print(f"CAGR: {result['cagr']:.2%}")
    print(f"Sharpe: {result['sharpe']:.2f}")
    print(f"Max DD: {result['max_drawdown']:.2%}")

    # Оптимизация
    print("\nЗапуск оптимизации...")
    param_grid = {
        'lookback_period': [60, 126, 180],
        'vol_window': [10, 20, 30],
        'max_vol_threshold': [0.3, 0.35, 0.4]
    }
    opt_results = optimize_dual_momentum(
        data,
        market_df,
        param_grid,
        commission={'EQMX': 0.005, 'OBLG': 0.003, 'GOLD': 0.006}
    )
    print("\nЛучшие параметры:")
    print(opt_results.head(3))

if __name__ == "__main__":
    main()

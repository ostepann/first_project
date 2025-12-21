# backtest_platform/validation/test01/test01_optimization_config_validation.py

import os

_data_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data-validation", "test01"
)

# Конфигурация Теста 1
param_grid = {'base_lookback': [2]}
production_params = {'lookback_period': 2}
commission = {'EQMX': 0.0, 'OBLG': 0.0, 'GOLD': 0.0}
default_commission = 0.0
slippage = 0.0
use_slippage = False
initial_capital = 100.0
trade_time_filter = None
tickers = ['GOLD', 'EQMX', 'OBLG', 'LQDT']
risk_free_ticker = 'LQDT'
market_ticker = 'EQMX'
data_dir = _data_dir
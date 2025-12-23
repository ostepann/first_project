# backtest_platform/validation/test03/test03_optimization_config_validation.py

import os

_data_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data-validation", "test03"
)

commission = {'EQMX': 0.0}
default_commission = 0.0
slippage = 0.0
use_slippage = False
initial_capital = 100.0
trade_time_filter = None
tickers = ['EQMX', 'LQDT']
risk_free_ticker = 'LQDT'
market_ticker = 'EQMX'
data_dir = _data_dir
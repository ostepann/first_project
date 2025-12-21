# backtest_platform/validation/test02/test02_optimization_config_validation.py

import os

_data_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data-validation", "test02"
)

# Настройки Теста 2
commission = {'EQMX_HIGH_VOL': 0.0, 'OBLG_LOW_VOL': 0.0}
default_commission = 0.0
slippage = 0.0
use_slippage = False
initial_capital = 100.0
trade_time_filter = None
tickers = ['OBLG_LOW_VOL', 'EQMX_HIGH_VOL', 'LQDT']
risk_free_ticker = 'LQDT'
market_ticker = 'OBLG_LOW_VOL'
data_dir = _data_dir
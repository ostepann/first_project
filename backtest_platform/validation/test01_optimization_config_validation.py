# backtest_platform/validation/optimization_config_validation.py
import os

# Путь к данным (относительно корня проекта)
_data_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data-validation"
)

# Конфигурация
param_grid = {'base_lookback': [2], 'base_vol_window': [2], 'max_vol_threshold': [0.5]}
production_params = {'base_lookback': 2, 'base_vol_window': 2, 'max_vol_threshold': 0.5}
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

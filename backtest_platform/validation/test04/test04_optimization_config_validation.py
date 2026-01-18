# backtest_platform/validation/test04/test04_optimization_config_validation.py

# --- Основные параметры теста ---
tickers = ['OBLG', 'EQMX', 'GOLD', 'LQDT']
market_ticker = 'EQMX'
data_dir = 'data-validation/test04'

# --- Параметры генерации данных ---
start_date = '2025-12-15'
n_days = 10
daily_return = 1.01  # 1% рост в день
initial_capital = 100.0

base_prices = {
    'OBLG': 188.0,
    'EQMX': 139.0,
    'GOLD': 2.73,
    'LQDT': 1.87
}

# --- Комиссия и проскальзывание (в % и bps) ---
commission = {
    'OBLG': 0.03,   # 0.03%
    'EQMX': 0.04,
    'GOLD': 0.05,
    'LQDT': 0.02,
}
default_commission = 0.0

slippage = {
    'OBLG': 7.5,    # 7.5 bps = 0.075%
    'EQMX': 7.5,
    'GOLD': 10.0,
    'LQDT': 0.6,
}
use_slippage = True

# --- Прочие настройки ---
trade_time_filter = False
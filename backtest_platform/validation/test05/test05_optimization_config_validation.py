# backtest_platform/validation/test05/test05_optimization_config_validation.py

# --- Основные параметры теста ---
tickers = ['OBLG', 'EQMX', 'GOLD', 'LQDT']
market_ticker = 'MOEX'
data_dir = 'data-validation/test05'

# --- Параметры генерации данных ---
start_date = '2025-10-20'
n_days = 10
initial_capital = 100.0

base_prices = {
    'OBLG': 98.0,
    'EQMX': 100.0,
    'GOLD': 50.0,
    'LQDT': 100.0,
    'MARKET_INDEX': 2500.0
}

# --- Комиссия и проскальзывание ---
commission = {
    'OBLG': 0.0,
    'EQMX': 0.0,
    'GOLD': 0.0,
    'LQDT': 0.0,
}
default_commission = 0.0

slippage = {
    'OBLG': 0.0,
    'EQMX': 0.0,
    'GOLD': 0.0,
    'LQDT': 0.0,
}
use_slippage = False

# --- Прочие настройки ---
trade_time_filter = False

# --- Параметры стратегии (СОВМЕСТИМЫЕ С DualMomentumStrategy) ---
strategy_params = {
    "base_lookback": 30,               # вместо lookback_period
    "base_vol_window": 10,             # ✅ совпадает
    "max_vol_threshold": 0.30,         # вместо market_vol_threshold
    "risk_free_ticker": "LQDT",        # вместо risk_free_asset
    "use_rvi_adaptation": True,        # вместо use_rvi_filter
    "bare_mode": False                 # явно отключаем bare_mode
}
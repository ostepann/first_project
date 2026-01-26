# --- Основные параметры теста ---
tickers = ['OBLG', 'EQMX', 'GOLD', 'LQDT']
market_ticker = 'MOEX'
data_dir = 'data-validation/test07'

# --- Параметры генерации данных ---
start_date = '2023-01-03'
n_days = 10  # Достаточно для покрытия 2023-01-05 (будний день)
initial_capital = 100_000

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

# --- Параметры стратегии ---
strategy_params = {
    "base_lookback": 5,                # Короткий период для быстрой реакции в тесте
    "base_vol_window": 5,
    "max_vol_threshold": 0.50,         # Высокий порог, чтобы избежать выхода в кэш
    "risk_free_ticker": "LQDT",
    "use_rvi_adaptation": False,       # Отключаем RVI для упрощения логики теста
    "bare_mode": False
}
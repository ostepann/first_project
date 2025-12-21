# optimization_config.py
<<<<<<< HEAD
"""
Конфигурация для бэктеста и оптимизации Dual Momentum стратегии.
Все настройки хранятся здесь — изменяйте только этот файл.
"""

# === ПАРАМЕТРЫ ОПТИМИЗАЦИИ ===
param_grid = {
    'base_lookback': [10, 20, 50, 75, 100, 126],
    'base_vol_window': [15, 20, 25, 30, 35],
    'max_vol_threshold': [0.3, 0.35, 0.4]
}

# === РЕКОМЕНДОВАННЫЕ ПАРАМЕТРЫ ДЛЯ ТОРГОВЛИ ===
production_params = {
    'base_lookback': 100,
    'base_vol_window': 15,
    'max_vol_threshold': 0.4
}

# === УСЛОВИЯ ТОРГОВЛИ ===
commission = {
    'EQMX': 0.0,
    'OBLG': 0.0,
    'GOLD': 0.0
}
default_commission = 0.0
slippage = 0.001
use_slippage = True
initial_capital = 100_000

# === ФИЛЬТР ПО ВРЕМЕНИ ===
# Установите '12:00:00', если данные содержат время
# Или None, если данные дневные
trade_time_filter = None

# === ТИКЕРЫ ===
tickers = ['GOLD', 'EQMX', 'OBLG', 'LQDT']
risk_free_ticker = 'LQDT'
market_ticker = 'EQMX'  # для рыночной волатильности и тренда

# === ДИРЕКТОРИИ ===
data_dir = "data"  # относительный путь от корня проекта
=======
# Настройки для полной оптимизации параметров Dual Momentum стратегии

param_grid = {
    'base_lookback': [5, 10, 20, 50, 100],
    'base_vol_window': [5, 10, 15, 20, 25],
    'max_vol_threshold': [0.3, 0.35, 0.4]
}

# Вы можете легко изменять этот файл вручную:
# - Добавлять/удалять значения,
# - Комментировать строки для теста,
# - Менять диапазоны.
>>>>>>> b66c2159192989e8615b8c8f3e1820f8ff7e1090

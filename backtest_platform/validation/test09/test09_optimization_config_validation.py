# backtest_platform/validation/test09/test09_optimization_config_validation.py

"""
Конфигурация для валидационного теста №9: Оптимизация параметра lookback.
Проверяет, что оптимизатор корректно выбирает lookback=10 как оптимальный период.
"""

# Директория для тестовых данных
data_dir = 'data-validation/test09'

# Тикеры для теста
assets = ['GOLD', 'EQMX', 'OBLG', 'LQDT']
risk_free_ticker = 'LQDT'
market_ticker = 'EQMX'

# Сетка параметров для оптимизации (фокус на lookback)
param_grid = {
    'base_lookback': [5, 10, 20],      # тестируемые периоды
    'base_vol_window': [20],           # фиксированный для чистоты теста
    'max_vol_threshold': [1.0],        # отключаем фильтр по волатильности
    'use_trend_filter': [False],       # отключаем трендовый фильтр для чистоты теста
    'bare_mode': [True]                # используем минимальную логику (только momentum)
}

# Ожидаемый оптимальный параметр
expected_best_lookback = 10

# Параметры бэктеста
initial_capital = 100_000
commission = 0.0  # без комиссии для чистоты теста
use_slippage = False
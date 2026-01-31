# backtest_platform/validation/test10/test10_optimization_config_validation.py

"""
Конфигурация валидационного теста 10: Граничные случаи
Проверяет корректность обработки edge cases в логике выбора актива
"""

data_dir = 'data-validation/test10'

# Случай 1: все активы в downtrend → выбор кэша (LQDT)
case1_assets = ['EQMX', 'OBLG', 'GOLD', 'LQDT']
case1_expected = 'LQDT'
case1_params = {
    'base_lookback': 10,
    'base_vol_window': 10,
    'max_vol_threshold': 1.0,      # отключаем фильтр волатильности
    'risk_free_ticker': 'LQDT',
    'bare_mode': False,
    'use_trend_filter': True,      # КЛЮЧЕВОЕ: включаем трендовый фильтр
    'trend_window': 15,            # окно для определения тренда
    'use_rvi_adaptation': False    # отключаем адаптацию для чистоты теста
}

# Случай 2: два актива с одинаковым momentum → выбор первого по алфавиту (EQMX < GOLD)
case2_assets = ['EQMX', 'GOLD', 'LQDT']
case2_expected = 'EQMX'  # EQMX идёт раньше GOLD в алфавитном порядке
case2_params = {
    'base_lookback': 5,
    'base_vol_window': 5,
    'max_vol_threshold': 1.0,
    'risk_free_ticker': 'LQDT',
    'bare_mode': True,             # используем минимальную логику (только momentum)
    'use_trend_filter': False,
    'use_rvi_adaptation': False
}

# Случай 3: недостаточно данных для lookback → удержание кэша
case3_assets = ['EQMX', 'OBLG', 'LQDT']
case3_expected = 'LQDT'  # при недостатке данных должен вернуться кэш
case3_params = {
    'base_lookback': 20,           # требуем 20 дней данных
    'base_vol_window': 10,
    'max_vol_threshold': 1.0,
    'risk_free_ticker': 'LQDT',
    'bare_mode': False,
    'use_trend_filter': False,
    'use_rvi_adaptation': False
}
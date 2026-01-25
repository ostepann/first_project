# backtest_platform/validation/test06/test06_optimization_config_validation.py

data_dir = 'data-validation/test06'
assets = ['EQMX', 'OBLG']
expected_selected_asset = 'OBLG'

# Параметры стратегии для теста
strategy_params = {
    'base_lookback': 10,          # короткий lookback — чтобы EQMX имел высокий моментум
    'bare_mode': False,           # используем полную логику
    'use_trend_filter': True,     # ← КЛЮЧЕВОЕ: включаем трендовый фильтр
    'trend_window': 25,           # ← достаточно, чтобы захватить downtrend у EQMX
    'max_vol_threshold': 1.0,     # отключаем фильтр по волатильности
    'risk_free_ticker': 'LQDT'
}
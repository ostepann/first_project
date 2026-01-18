# backtest_platform/validation/test04/test04_generate_validation_data.py

import pandas as pd
import os
import sys

def main():
    # Добавляем папку текущего теста в sys.path для импорта конфига
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    
    import test04_optimization_config_validation as cfg

    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data-validation", "test04"
    )
    os.makedirs(output_dir, exist_ok=True)

    dates = pd.date_range(cfg.start_date, periods=cfg.n_days, freq='B')
    n = len(dates)

    def generate_price_series(base_price):
        prices = [base_price]
        for i in range(1, n):
            prices.append(prices[-1] * cfg.daily_return)
        return prices

    # OBLG
    oblg_prices = generate_price_series(cfg.base_prices['OBLG'])
    oblg = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [cfg.base_prices['OBLG']] + oblg_prices[:-1],
        'HIGH': oblg_prices,
        'LOW': oblg_prices,
        'CLOSE': oblg_prices,
        'VOLUME': [1_000_000] * n
    })

    # EQMX
    eqmx_prices = generate_price_series(cfg.base_prices['EQMX'])
    eqmx = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [cfg.base_prices['EQMX']] + eqmx_prices[:-1],
        'HIGH': eqmx_prices,
        'LOW': eqmx_prices,
        'CLOSE': eqmx_prices,
        'VOLUME': [1_000_000] * n
    })

    # GOLD
    gold_prices = generate_price_series(cfg.base_prices['GOLD'])
    gold = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [cfg.base_prices['GOLD']] + gold_prices[:-1],
        'HIGH': gold_prices,
        'LOW': gold_prices,
        'CLOSE': gold_prices,
        'VOLUME': [10_000_000] * n
    })

    # LQDT — кэш (не растёт)
    lqdt = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [cfg.base_prices['LQDT']] * n,
        'HIGH': [cfg.base_prices['LQDT']] * n,
        'LOW': [cfg.base_prices['LQDT']] * n,
        'CLOSE': [cfg.base_prices['LQDT']] * n,
        'VOLUME': [0] * n
    })

    # RVI — фиксированный низкий уровень
    rvi_values = [10.0] * n
    rvi = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': rvi_values,
        'HIGH': rvi_values,
        'LOW': rvi_values,
        'CLOSE': rvi_values,
        'VOLUME': [0] * n
    })

    # Сохраняем
    for name, df in [("OBLG", oblg), ("EQMX", eqmx), ("GOLD", gold), ("LQDT", lqdt), ("RVI", rvi)]:
        df.to_csv(os.path.join(output_dir, f'test04_{name}.csv'), index=False)

    print("✅ Тест 4: данные сгенерированы")

if __name__ == "__main__":
    main()
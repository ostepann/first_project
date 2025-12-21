# backtest_platform/validation/test02/test02_generate_validation_data.py

import pandas as pd
import numpy as np
import os

def main():
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data-validation", "test02"
    )
    os.makedirs(output_dir, exist_ok=True)

    # 20 торговых дней (для стабильного расчёта волатильности)
    dates = pd.date_range('2023-01-02', periods=20, freq='B')
    n = len(dates)

    # EQMX_HIGH_VOL: растёт в среднем на 0.5% в день, но с высокой волатильностью (скачки ±5%)
    np.random.seed(42)
    eqmx_prices = [100.0]
    for i in range(1, n):
        # Базовый тренд + шум
        trend = 0.005  # +0.5% в день
        noise = np.random.normal(0, 0.05)  # ±5% шум
        price = eqmx_prices[-1] * (1 + trend + noise)
        eqmx_prices.append(price)

    eqmx = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [100.0] + eqmx_prices[:-1],
        'HIGH': np.maximum(eqmx_prices, [100.0] + eqmx_prices[:-1]) * 1.02,
        'LOW': np.minimum(eqmx_prices, [100.0] + eqmx_prices[:-1]) * 0.98,
        'CLOSE': eqmx_prices,
        'VOLUME': [10000] * n
    })

    # OBLG_LOW_VOL: стабильный рост на 0.3% в день, низкая волатильность
    oblg_prices = [100.0]
    for i in range(1, n):
        oblg_prices.append(oblg_prices[-1] * 1.003)  # +0.3% в день

    oblg = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [100.0] + oblg_prices[:-1],
        'HIGH': oblg_prices,
        'LOW': oblg_prices,
        'CLOSE': oblg_prices,
        'VOLUME': [10000] * n
    })

    # LQDT: кэш
    lqdt = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [100.0] * n,
        'HIGH': [100.0] * n,
        'LOW': [100.0] * n,
        'CLOSE': [100.0] * n,
        'VOLUME': [0] * n
    })

    # RVI: низкий
    rvi = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [10.0] * n,
        'HIGH': [10.0] * n,
        'LOW': [10.0] * n,
        'CLOSE': [10.0] * n,
        'VOLUME': [0] * n
    })

    # Сохранение
    for name, df in [("EQMX_HIGH_VOL", eqmx), ("OBLG_LOW_VOL", oblg), ("LQDT", lqdt), ("RVI", rvi)]:
        df.to_csv(os.path.join(output_dir, f'test02_{name}.csv'), index=False)

    # Проверка волатильности (для отладки)
    eqmx_vol = eqmx['CLOSE'].pct_change().std() * np.sqrt(252)
    oblg_vol = oblg['CLOSE'].pct_change().std() * np.sqrt(252)
    print(f"✅ Тест 2: данные сохранены")
    print(f"  EQMX_HIGH_VOL волатильность: {eqmx_vol:.1%}")
    print(f"  OBLG_LOW_VOL волатильность: {oblg_vol:.1%}")

if __name__ == "__main__":
    main()
# backtest_platform/validation/test03/test03_generate_validation_data.py

import pandas as pd
import os

def main():
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data-validation", "test03"
    )
    os.makedirs(output_dir, exist_ok=True)

    # 40 дней: 20 с RVI=10, 20 с RVI=40
    dates = pd.date_range('2023-01-02', periods=40, freq='B')
    n = len(dates)

    # EQMX: растёт на 0.2% в день (плавный рост, чтобы не триггерить вол-фильтр)
    eqmx_prices = [100.0]
    for i in range(1, n):
        eqmx_prices.append(eqmx_prices[-1] * 1.002)

    eqmx = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [100.0] + eqmx_prices[:-1],
        'HIGH': eqmx_prices,
        'LOW': eqmx_prices,
        'CLOSE': eqmx_prices,
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

    # RVI: низкий → высокий
    rvi_values = [10.0] * 20 + [40.0] * 20
    rvi = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': rvi_values,
        'HIGH': rvi_values,
        'LOW': rvi_values,
        'CLOSE': rvi_values,
        'VOLUME': [0] * n
    })

    for name, df in [("EQMX", eqmx), ("LQDT", lqdt), ("RVI", rvi)]:
        df.to_csv(os.path.join(output_dir, f'test03_{name}.csv'), index=False)

    print("✅ Тест 3: данные сгенерированы")

if __name__ == "__main__":
    main()
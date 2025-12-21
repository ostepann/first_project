# backtest_platform/validation/test01/test01_generate_validation_data.py

import pandas as pd
import os

def main():
    # Путь к data-validation/test01
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data-validation", "test01"
    )
    os.makedirs(output_dir, exist_ok=True)

    # 11 торговых дней
    dates = pd.date_range('2023-01-02', periods=11, freq='B')
    n = len(dates)

    # EQMX: +1% в день (самый прибыльный)
    eqmx_close = [100.0]
    for _ in range(n - 1):
        eqmx_close.append(eqmx_close[-1] * 1.01)

    eqmx = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [100.0] + eqmx_close[:-1],
        'HIGH': eqmx_close,
        'LOW': eqmx_close,
        'CLOSE': eqmx_close,
        'VOLUME': [10000] * n
    })

    # GOLD: стагнация
    gold = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [100.0] * n,
        'HIGH': [100.0] * n,
        'LOW': [100.0] * n,
        'CLOSE': [100.0] * n,
        'VOLUME': [10000] * n
    })

    # OBLG: падение
    oblg_close = [100.0]
    for _ in range(n - 1):
        oblg_close.append(oblg_close[-1] * 0.995)
    oblg = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [100.0] + oblg_close[:-1],
        'HIGH': oblg_close,
        'LOW': oblg_close,
        'CLOSE': oblg_close,
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

    # RVI: стабильно низкий
    rvi = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [10.0] * n,
        'HIGH': [10.0] * n,
        'LOW': [10.0] * n,
        'CLOSE': [10.0] * n,
        'VOLUME': [0] * n
    })

    # Сохранение с префиксом test01_
    for name, df in [("EQMX", eqmx), ("GOLD", gold), ("OBLG", oblg), ("LQDT", lqdt), ("RVI", rvi)]:
        df.to_csv(os.path.join(output_dir, f'test01_{name}.csv'), index=False)

    print(f"✅ Тест 1: данные сохранены в {output_dir}")

if __name__ == "__main__":
    main()
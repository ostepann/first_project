# backtest_platform/validation/generate_validation_data.py
import pandas as pd
import os

def main():
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data-validation"
    )
    os.makedirs(output_dir, exist_ok=True)

    # 11 торговых дней
    dates = pd.date_range('2023-01-02', periods=11, freq='B')
    n = len(dates)  # n = 11

    # EQMX: +1% в день (11 значений)
    eqmx_close = [100.0]
    for _ in range(n - 1):  # 10 итераций → 11 значений
        eqmx_close.append(eqmx_close[-1] * 1.01)
    
    eqmx = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [100.0] + eqmx_close[:-1],  # 11 значений
        'HIGH': eqmx_close,
        'LOW': eqmx_close,
        'CLOSE': eqmx_close,
        'VOLUME': [10000] * n  # 11 значений
    })

    # OBLG: -0.5% в день
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

    # GOLD и LQDT: стагнация
    gold = pd.DataFrame({
        'TRADEDATE': dates,
        'OPEN': [100.0] * n,
        'HIGH': [100.0] * n,
        'LOW': [100.0] * n,
        'CLOSE': [100.0] * n,
        'VOLUME': [10000] * n
    })
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

    # Сохранение
    for name, df in [("EQMX", eqmx), ("OBLG", oblg), ("GOLD", gold), ("LQDT", lqdt), ("RVI", rvi)]:
        df.to_csv(os.path.join(output_dir, f'{name}.csv'), index=False)

    print(f"✅ Валидационные данные ({n} дней) сохранены в: ../data-validation/")

if __name__ == "__main__":
    main()
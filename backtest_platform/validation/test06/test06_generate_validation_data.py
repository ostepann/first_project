# backtest_platform/validation/test06/test06_generate_validation_data.py

import pandas as pd
import os
import sys
import numpy as np

def main():
    # Добавляем папку текущего теста в sys.path для импорта конфига
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    
    import test06_optimization_config_validation as cfg

    # Путь к data-validation/test06 (относительно корня проекта)
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        cfg.data_dir
    )
    os.makedirs(output_dir, exist_ok=True)

    # Генерация данных
    dates = pd.date_range(start='2025-01-01', periods=30, freq='D')

    # EQMX: общий downtrend + краткосрочный всплеск (+5%)
    eqmx_base = np.linspace(100, 80, 25)  # downtrend
    eqmx_spike = [80 * 1.05]              # +5%
    eqmx_post = [80 * 1.05 * 0.98] * 4    # небольшое падение после
    eqmx_prices = np.concatenate([eqmx_base, eqmx_spike, eqmx_post])
    eqmx_series = pd.Series(eqmx_prices, index=dates, name='close')

    # OBLG: стабильный uptrend
    oblg_prices = np.linspace(90, 110, 30)
    oblg_series = pd.Series(oblg_prices, index=dates, name='close')

    data = {
        'EQMX': eqmx_series,
        'OBLG': oblg_series
    }

    # Сохранение
    for ticker, series in data.items():
        df = series.to_frame()
        df.index.name = 'date'
        df.to_csv(os.path.join(output_dir, f"{ticker}.csv"))

    print(f"✅ Тестовые данные сохранены в {output_dir}")

if __name__ == '__main__':
    main()
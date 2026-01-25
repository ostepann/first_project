# backtest_platform/validation/test06/test06_run_validation.py

import pandas as pd
import os
import sys

def main():
    # Добавляем папку текущего теста в sys.path
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    
    import test06_optimization_config_validation as cfg

    # Добавляем корень проекта в sys.path, чтобы импортировать backtest_platform
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from backtest_platform.strategies.dual_momentum import DualMomentumStrategy

    # Загрузка данных
    data_dir_abs = os.path.join(project_root, cfg.data_dir)
    asset_data = {}
    for asset in cfg.assets:
        path = os.path.join(data_dir_abs, f"{asset}.csv")
        df = pd.read_csv(path, index_col='date', parse_dates=True)
        df = df.rename(columns={'close': 'CLOSE'})
        asset_data[asset] = df[['CLOSE']]

    # Создание стратегии
    strategy = DualMomentumStrategy(**cfg.strategy_params)

    # Генерация сигнала
    signal = strategy.generate_signal(data_dict=asset_data)
    selected = signal['selected']

    print(f"Выбранный актив: {selected}")
    print(f"Ожидаемый актив: {cfg.expected_selected_asset}")

    assert selected == cfg.expected_selected_asset, (
        f"❌ Ошибка: ожидался {cfg.expected_selected_asset}, получен {selected}"
    )

    print("✅ Тест 6 пройден успешно!")

if __name__ == '__main__':
    main()
# backtest_platform/validation/test10/test10_run_validation.py

import pandas as pd
import os
import sys

def load_case_data(project_root, case_subdir, assets):
    """Загружает данные для конкретного случая из подпапки"""
    case_dir = os.path.join(project_root, 'data-validation', 'test10', case_subdir)
    asset_data = {}
    for asset in assets:
        path = os.path.join(case_dir, f"{asset}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌ Файл не найден: {path}")
        df = pd.read_csv(path, index_col='date', parse_dates=True)
        df = df.rename(columns={'close': 'CLOSE'})
        asset_data[asset] = df[['CLOSE']]
    return asset_data

def validate_case(strategy_params, asset_data, expected_asset, case_name):
    """Выполняет валидацию для одного случая"""
    from backtest_platform.strategies.dual_momentum import DualMomentumStrategy
    
    strategy = DualMomentumStrategy(**strategy_params)
    signal = strategy.generate_signal(data_dict=asset_data)
    selected = signal['selected']
    
    print(f"\n{case_name}")
    print(f"  Выбранный актив: {selected}")
    print(f"  Ожидаемый актив: {expected_asset}")
    
    assert selected == expected_asset, (
        f"❌ {case_name}: ожидался {expected_asset}, получен {selected}"
    )
    print(f"  ✅ Пройден")

def main():
    # Добавляем папку текущего теста в sys.path
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    
    import test10_optimization_config_validation as cfg

    # Добавляем корень проекта в sys.path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    print("=" * 70)
    print("ЗАПУСК ТЕСТА 10: Граничные случаи Dual Momentum стратегии")
    print("=" * 70)

    # === СЛУЧАЙ 1: Все активы в downtrend → выбор LQDT ===
    print("\n[Случай 1] Все активы в нисходящем тренде")
    print("Ожидание: трендовый фильтр отсеивает все рисковые активы → выбор LQDT")
    asset_data1 = load_case_data(project_root, 'case1', cfg.case1_assets)
    validate_case(cfg.case1_params, asset_data1, cfg.case1_expected, "Случай 1 (downtrend)")

    # === СЛУЧАЙ 2: Одинаковый momentum → выбор первого по алфавиту ===
    print("\n[Случай 2] Два актива с одинаковым momentum")
    print("Ожидание: при равных скорах выбирается первый по алфавиту (EQMX < GOLD)")
    asset_data2 = load_case_data(project_root, 'case2', cfg.case2_assets)
    validate_case(cfg.case2_params, asset_data2, cfg.case2_expected, "Случай 2 (одинаковый momentum)")

    # === СЛУЧАЙ 3: Недостаточно данных → удержание кэша ===
    print("\n[Случай 3] Недостаточно данных для расчёта lookback")
    print("Ожидание: при недостатке данных актив не проходит фильтрацию → выбор LQDT")
    asset_data3 = load_case_data(project_root, 'case3', cfg.case3_assets)
    validate_case(cfg.case3_params, asset_data3, cfg.case3_expected, "Случай 3 (недостаток данных)")

    print("\n" + "=" * 70)
    print("✅ ТЕСТ 10 ПРОЙДЕН УСПЕШНО: все граничные случаи обрабатываются корректно")
    print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    except AssertionError as e:
        print(f"\n❌ ТЕСТ 10 ПРОВАЛЕН: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
# backtest_platform/validation/test10/test10_generate_validation_data.py

import pandas as pd
import os
import sys
import numpy as np
import shutil

def clean_directory(directory_path):
    """
    Безопасно удаляет все файлы CSV в указанной директории.
    Не удаляет саму директорию и вложенные папки (на случай если структура изменится).
    """
    if not os.path.exists(directory_path):
        return
    
    # Удаляем только CSV-файлы в текущей директории (не рекурсивно)
    for filename in os.listdir(directory_path):
        if filename.endswith('.csv'):
            file_path = os.path.join(directory_path, filename)
            try:
                os.remove(file_path)
                print(f"  🗑️  Удалён файл: {filename}")
            except Exception as e:
                print(f"  ⚠️  Не удалось удалить {filename}: {e}")

def main():
    # Добавляем папку текущего теста в sys.path для импорта конфига
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    
    import test10_optimization_config_validation as cfg

    # Путь к корню проекта
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # Создаём основную папку для теста 10
    base_output_dir = os.path.join(project_root, cfg.data_dir)
    os.makedirs(base_output_dir, exist_ok=True)

    # === ОЧИСТКА СУЩЕСТВУЮЩИХ ДАННЫХ ===
    print("🧹 Очистка существующих тестовых данных...")
    for case_name in ['case1', 'case2', 'case3']:
        case_dir = os.path.join(base_output_dir, case_name)
        if os.path.exists(case_dir):
            print(f"\nОчистка папки {case_name}:")
            clean_directory(case_dir)
        else:
            print(f"\nПапка {case_name} не существует — будет создана заново")
    
    print("\n" + "=" * 70)

    # === СЛУЧАЙ 1: Все активы в downtrend → выбор LQDT ===
    print("Генерация данных для Случая 1: все активы в downtrend...")
    case1_dir = os.path.join(base_output_dir, 'case1')
    os.makedirs(case1_dir, exist_ok=True)
    
    dates1 = pd.date_range(start='2025-01-01', periods=30, freq='D')
    
    # Все активы имеют чёткий downtrend (отрицательный наклон)
    eqmx1 = pd.Series(np.linspace(100, 70, 30), index=dates1, name='close')
    oblg1 = pd.Series(np.linspace(95, 65, 30), index=dates1, name='close')
    gold1 = pd.Series(np.linspace(110, 80, 30), index=dates1, name='close')
    lqdt1 = pd.Series(np.linspace(100, 102, 30), index=dates1, name='close')  # кэш стабилен
    
    for ticker, series in [('EQMX', eqmx1), ('OBLG', oblg1), ('GOLD', gold1), ('LQDT', lqdt1)]:
        df = series.to_frame()
        df.index.name = 'date'
        df.to_csv(os.path.join(case1_dir, f"{ticker}.csv"))
    
    print(f"✅ Случай 1 сохранён в {case1_dir}")

    # === СЛУЧАЙ 2: Одинаковый momentum → выбор первого по алфавиту ===
    print("\nГенерация данных для Случая 2: одинаковый momentum...")
    case2_dir = os.path.join(base_output_dir, 'case2')
    os.makedirs(case2_dir, exist_ok=True)
    
    dates2 = pd.date_range(start='2025-01-01', periods=10, freq='D')
    
    # EQMX и GOLD имеют одинаковое изменение за период (20% рост)
    eqmx2_base = 100
    eqmx2 = pd.Series([eqmx2_base] * 5 + [eqmx2_base * 1.2] * 5, index=dates2, name='close')
    
    gold2_base = 150
    gold2 = pd.Series([gold2_base] * 5 + [gold2_base * 1.2] * 5, index=dates2, name='close')
    
    lqdt2 = pd.Series([100] * 10, index=dates2, name='close')  # кэш стабилен
    
    for ticker, series in [('EQMX', eqmx2), ('GOLD', gold2), ('LQDT', lqdt2)]:
        df = series.to_frame()
        df.index.name = 'date'
        df.to_csv(os.path.join(case2_dir, f"{ticker}.csv"))
    
    print(f"✅ Случай 2 сохранён в {case2_dir}")
    print(f"   Проверка: momentum EQMX = {(120-100)/100:.1%}, momentum GOLD = {(180-150)/150:.1%} → одинаковы")

    # === СЛУЧАЙ 3: Недостаточно данных для lookback → удержание кэша ===
    print("\nГенерация данных для Случая 3: недостаток данных...")
    case3_dir = os.path.join(base_output_dir, 'case3')
    os.makedirs(case3_dir, exist_ok=True)
    
    # Требуется 20 дней (согласно конфигу), но даём только 15
    dates3 = pd.date_range(start='2025-01-01', periods=15, freq='D')
    
    eqmx3 = pd.Series(np.linspace(100, 110, 15), index=dates3, name='close')
    oblg3 = pd.Series(np.linspace(95, 105, 15), index=dates3, name='close')
    lqdt3 = pd.Series(np.linspace(100, 101, 15), index=dates3, name='close')
    
    for ticker, series in [('EQMX', eqmx3), ('OBLG', oblg3), ('LQDT', lqdt3)]:
        df = series.to_frame()
        df.index.name = 'date'
        df.to_csv(os.path.join(case3_dir, f"{ticker}.csv"))
    
    print(f"✅ Случай 3 сохранён в {case3_dir}")
    print(f"   Предоставлено 15 дней данных при требуемых 20 для lookback")

    print("\n" + "=" * 70)
    print(f"✅ Все тестовые данные успешно сгенерированы и сохранены в {base_output_dir}")
    print("=" * 70)

if __name__ == '__main__':
    main()
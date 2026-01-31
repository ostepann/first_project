# backtest_platform/validation/test09/test09_generate_validation_data.py

"""
Генерация тестовых данных для валидационного теста №9.
Создает 4 фазы с РЕЗКИМИ разворотами (5-7 дней) и контролируемым шумом,
где оптимальный lookback=10 по критерию CAGR.
"""

import pandas as pd
import numpy as np
import os
import sys
import glob

def main():
    # Добавляем папку текущего теста в sys.path для импорта конфига
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    
    import test09_optimization_config_validation as cfg

    # Путь к data-validation/test09 (относительно корня проекта)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    output_dir = os.path.join(project_root, cfg.data_dir)
    
    # === ПРОВЕРКА И УДАЛЕНИЕ СУЩЕСТВУЮЩИХ ФАЙЛОВ ===
    if os.path.exists(output_dir):
        # Ищем все CSV файлы в директории
        csv_files = glob.glob(os.path.join(output_dir, "*.csv"))
        if csv_files:
            print(f"⚠️  Обнаружены существующие тестовые данные в {output_dir}:")
            for f in csv_files:
                print(f"   - {os.path.basename(f)}")
            print("   Удаляем старые файлы...")
            for f in csv_files:
                try:
                    os.remove(f)
                    print(f"   ✅ Удалён: {os.path.basename(f)}")
                except Exception as e:
                    print(f"   ❌ Ошибка при удалении {os.path.basename(f)}: {e}")
            print()
    
    # Создаём директорию (если её нет)
    os.makedirs(output_dir, exist_ok=True)

    # Генерация данных: 252 торговых дня (1 год)
    dates = pd.date_range(start='2025-01-01', periods=252, freq='B')  # будни
    n = len(dates)
    
    np.random.seed(42)  # воспроизводимость

    # === ФАЗА 1 (дни 0-60): GOLD растет РЕЗКО (+40% за 60 дней) ===
    phase1_end = 60
    gold_p1 = np.linspace(100, 140, phase1_end)  # +40%
    eqmx_p1 = np.linspace(100, 105, phase1_end)  # +5% (слабый рост)
    oblg_p1 = np.linspace(100, 103, phase1_end)  # +3%
    
    # === ФАЗА 2 (дни 60-120): РЕЗКИЙ разворот за 7 дней → EQMX растет (+50%), GOLD падает (-20%) ===
    phase2_start = 60
    phase2_mid = 67  # точка разворота (7 дней на переход)
    phase2_end = 120
    
    # GOLD: плавное падение до разворота, затем резкое падение
    gold_p2a = np.linspace(140, 138, phase2_mid - phase2_start)  # подготовка к развороту
    gold_p2b = np.linspace(138, 112, phase2_end - phase2_mid)    # резкое падение -20%
    gold_p2 = np.concatenate([gold_p2a, gold_p2b])
    
    # EQMX: резкий рост после разворота
    eqmx_p2a = np.linspace(105, 107, phase2_mid - phase2_start)  # подготовка
    eqmx_p2b = np.linspace(107, 157, phase2_end - phase2_mid)    # резкий рост +50%
    eqmx_p2 = np.concatenate([eqmx_p2a, eqmx_p2b])
    
    oblg_p2 = np.linspace(103, 106, phase2_end - phase2_start)   # +3%
    
    # === ФАЗА 3 (дни 120-180): РЕЗКИЙ разворот за 5 дней → GOLD растет (+45%), EQMX падает (-15%) ===
    phase3_start = 120
    phase3_mid = 125  # разворот за 5 дней
    phase3_end = 180
    
    gold_p3a = np.linspace(112, 114, phase3_mid - phase3_start)
    gold_p3b = np.linspace(114, 163, phase3_end - phase3_mid)    # +45%
    gold_p3 = np.concatenate([gold_p3a, gold_p3b])
    
    eqmx_p3a = np.linspace(157, 155, phase3_mid - phase3_start)
    eqmx_p3b = np.linspace(155, 133, phase3_end - phase3_mid)    # -15%
    eqmx_p3 = np.concatenate([eqmx_p3a, eqmx_p3b])
    
    oblg_p3 = np.linspace(106, 109, phase3_end - phase3_start)   # +3%
    
    # === ФАЗА 4 (дни 180-252): РЕЗКИЙ разворот за 6 дней → EQMX растет (+35%), GOLD боковик ===
    phase4_start = 180
    phase4_mid = 186  # разворот за 6 дней
    phase4_end = 252
    
    gold_p4a = np.linspace(163, 162, phase4_mid - phase4_start)
    gold_p4b = np.linspace(162, 165, phase4_end - phase4_mid)    # +1.8% (боковик)
    gold_p4 = np.concatenate([gold_p4a, gold_p4b])
    
    eqmx_p4a = np.linspace(133, 135, phase4_mid - phase4_start)
    eqmx_p4b = np.linspace(135, 182, phase4_end - phase4_mid)    # +35%
    eqmx_p4 = np.concatenate([eqmx_p4a, eqmx_p4b])
    
    oblg_p4 = np.linspace(109, 112, phase4_end - phase4_start)   # +3%
    
    # Собираем полные ряды
    gold_prices = np.concatenate([gold_p1, gold_p2, gold_p3, gold_p4])
    eqmx_prices = np.concatenate([eqmx_p1, eqmx_p2, eqmx_p3, eqmx_p4])
    oblg_prices = np.concatenate([oblg_p1, oblg_p2, oblg_p3, oblg_p4])
    lqdt_prices = np.linspace(100, 102, n)  # кэш +2%
    
    # === ДОБАВЛЯЕМ КОНТРОЛИРУЕМЫЙ ШУМ ===
    # Умеренный шум 0.7% для создания ложных сигналов у короткого lookback
    noise_gold = np.random.normal(0, 0.7, n)
    noise_eqmx = np.random.normal(0, 0.7, n)
    
    # Ложные сигналы ТОЛЬКО в 3-4 днях перед настоящими разворотами (для lookback=5)
    noise_gold[57:61] += np.array([1.5, -2.0, 1.8, -1.5])  # ложный разворот перед фазой 2
    noise_eqmx[57:61] += np.array([-1.2, 1.8, -1.5, 1.2])
    
    noise_gold[117:121] += np.array([-1.8, 2.2, -2.0, 1.5])  # ложный разворот перед фазой 3
    noise_eqmx[117:121] += np.array([1.5, -2.0, 1.8, -1.5])
    
    noise_gold[177:181] += np.array([1.2, -1.8, 1.5, -1.2])  # ложный разворот перед фазой 4
    noise_eqmx[177:181] += np.array([-1.0, 1.5, -1.2, 1.0])
    
    gold_prices += noise_gold
    eqmx_prices += noise_eqmx
    
    # Убеждаемся, что цены остаются положительными
    gold_prices = np.maximum(gold_prices, 50)
    eqmx_prices = np.maximum(eqmx_prices, 50)

    # Создание датафреймов
    data = {
        'GOLD': pd.DataFrame({'TRADEDATE': dates, 'CLOSE': gold_prices}),
        'EQMX': pd.DataFrame({'TRADEDATE': dates, 'CLOSE': eqmx_prices}),
        'OBLG': pd.DataFrame({'TRADEDATE': dates, 'CLOSE': oblg_prices}),
        'LQDT': pd.DataFrame({'TRADEDATE': dates, 'CLOSE': lqdt_prices})
    }

    # Сохранение данных
    for ticker, df in data.items():
        df.to_csv(os.path.join(output_dir, f"{ticker}.csv"), index=False)

    print(f"✅ Тестовые данные для Теста 9 сохранены в {output_dir}")
    print(f"   Период: {dates[0].date()} — {dates[-1].date()} ({len(dates)} дней)")
    print(f"   GOLD: {gold_prices[0]:.2f} → {gold_prices[-1]:.2f} (+{(gold_prices[-1]/gold_prices[0]-1)*100:.1f}%)")
    print(f"   EQMX: {eqmx_prices[0]:.2f} → {eqmx_prices[-1]:.2f} (+{(eqmx_prices[-1]/eqmx_prices[0]-1)*100:.1f}%)")
    print(f"   OBLG: {oblg_prices[0]:.2f} → {oblg_prices[-1]:.2f} (+{(oblg_prices[-1]/oblg_prices[0]-1)*100:.1f}%)")
    print(f"   LQDT: {lqdt_prices[0]:.2f} → {lqdt_prices[-1]:.2f} (+{(lqdt_prices[-1]/lqdt_prices[0]-1)*100:.1f}%)")
    print("\n💡 Структура рынка с РЕЗКИМИ разворотами:")
    print(f"   Фаза 1 (0-60):   рост GOLD +40%")
    print(f"   Фаза 2 (60-120): разворот за 7 дней → рост EQMX +50%, GOLD -20%")
    print(f"   Фаза 3 (120-180): разворот за 5 дней → рост GOLD +45%, EQMX -15%")
    print(f"   Фаза 4 (180-252): разворот за 6 дней → рост EQMX +35%, GOLD +1.8%")
    print("   Шум 0.7% + ложные сигналы в 3-4 днях перед разворотами")

if __name__ == '__main__':
    main()
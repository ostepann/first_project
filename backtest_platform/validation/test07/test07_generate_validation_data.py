import pandas as pd
import os
import sys
import numpy as np

def main():
    # Добавляем папку текущего теста в sys.path для импорта конфига
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    
    import test07_optimization_config_validation as cfg

    # Исправлено: правильная расстановка скобок для формирования пути
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    output_dir = os.path.join(project_root, cfg.data_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Генерируем все будние дни в диапазоне
    dates = pd.date_range(cfg.start_date, periods=cfg.n_days, freq='B')
    n = len(dates)

    # === Генерация цен активов ===
    base = cfg.base_prices

    # EQMX: устойчивый рост → положительный momentum (но с пропуском на 2023-01-05)
    eqmx_prices = [base['EQMX']]
    for i in range(1, n):
        eqmx_prices.append(eqmx_prices[-1] * 1.003)  # ~0.3% в день

    # Создаём полный датафрейм для всех дат
    eqmx_full = pd.DataFrame({
        'TRADEDATE': dates,
        'price': eqmx_prices
    })

    # Удаляем дату 2023-01-05 (четверг) из EQMX
    missing_date = pd.Timestamp('2023-01-05')
    eqmx_with_gap = eqmx_full[eqmx_full['TRADEDATE'] != missing_date].copy()
    print(f"⚠️  Пропущена дата в EQMX: {missing_date.date()}")
    print(f"📊 EQMX: {len(eqmx_full)} дней → {len(eqmx_with_gap)} дней (пропущено 1)")

    # GOLD: плоский тренд
    gold_prices = [base['GOLD']] * n

    # OBLG: слабый рост (без пропусков!)
    oblg_prices = [base['OBLG']]
    for i in range(1, n):
        oblg_prices.append(oblg_prices[-1] * 1.001)

    # LQDT: кэш, без роста
    lqdt_prices = [base['LQDT']] * n

    # === Рыночный индекс (MOEX) — умеренная волатильность ===
    np.random.seed(42)
    market_prices = [base['MARKET_INDEX']]
    daily_vol = 0.015
    for i in range(1, n):
        ret = np.random.normal(loc=0.0005, scale=daily_vol)
        market_prices.append(market_prices[-1] * (1 + ret))

    # === RVI — стабильный уровень ===
    rvi_values = [25.0] * n  # Низкий уровень, чтобы не триггерить фильтр

    # === Вспомогательная функция: OHLC из цен закрытия ===
    def make_ohlc_df(tradedate, prices, volume):
        open_prices = [prices[0]] + prices[:-1]
        return pd.DataFrame({
            'TRADEDATE': tradedate,
            'OPEN': open_prices,
            'HIGH': prices,
            'LOW': prices,
            'CLOSE': prices,
            'VOLUME': [volume] * len(prices)
        })

    # Создаём датафреймы
    # Для EQMX используем данные С ПРОПУСКОМ
    eqmx = make_ohlc_df(eqmx_with_gap['TRADEDATE'].tolist(), eqmx_with_gap['price'].tolist(), 1_000_000)
    
    # Для остальных активов — полные данные
    gold = make_ohlc_df(dates.tolist(), gold_prices, 10_000_000)
    oblg = make_ohlc_df(dates.tolist(), oblg_prices, 500_000)
    lqdt = make_ohlc_df(dates.tolist(), lqdt_prices, 0)
    moex = make_ohlc_df(dates.tolist(), market_prices, 0)
    rvi = make_ohlc_df(dates.tolist(), rvi_values, 0)

    # Сохраняем
    for name, df in [
        ("EQMX", eqmx),
        ("GOLD", gold),
        ("OBLG", oblg),
        ("LQDT", lqdt),
        ("MOEX", moex),
        ("RVI", rvi)
    ]:
        df.to_csv(os.path.join(output_dir, f'test07_{name}.csv'), index=False)
        print(f"💾 {name}: {len(df)} строк, даты [{df['TRADEDATE'].min().date()} → {df['TRADEDATE'].max().date()}]")

    # Валидация: проверяем наличие пропуска
    all_dates = set(dates)
    eqmx_dates = set(eqmx['TRADEDATE'])
    missing_in_eqmx = all_dates - eqmx_dates
    if missing_date in missing_in_eqmx:
        print(f"✅ Пропуск подтверждён: {missing_date.date()} отсутствует в EQMX")
    else:
        print(f"❌ ОШИБКА: ожидаемый пропуск {missing_date.date()} не найден в EQMX!")

    print("\n✅ Тест 7: данные сгенерированы (пропуск в EQMX на 2023-01-05)")

if __name__ == "__main__":
    main()
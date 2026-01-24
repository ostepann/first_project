# backtest_platform/validation/test05/test05_generate_validation_data.py

import pandas as pd
import os
import sys
import numpy as np

def main():
    # Добавляем папку текущего теста в sys.path для импорта конфига
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    
    import test05_optimization_config_validation as cfg

    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        cfg.data_dir
    )
    os.makedirs(output_dir, exist_ok=True)

    dates = pd.date_range(cfg.start_date, periods=cfg.n_days, freq='B')
    n = len(dates)

    # === Генерация цен активов ===
    base = cfg.base_prices

    # EQMX: устойчивый рост → положительный momentum
    eqmx_prices = [base['EQMX']]
    for i in range(1, n):
        eqmx_prices.append(eqmx_prices[-1] * 1.002)  # ~0.2% в день

    # GOLD: плоский
    gold_prices = [base['GOLD']] * n

    # OBLG: слабый рост
    oblg_prices = [base['OBLG']]
    for i in range(1, n):
        oblg_prices.append(oblg_prices[-1] * 1.0005)

    # LQDT: кэш, без роста
    lqdt_prices = [base['LQDT']] * n

    # === Рыночный индекс (MOEX) — высокая волатильность (~50% annualized) ===
    np.random.seed(42)  # воспроизводимость
    market_prices = [base['MARKET_INDEX']]
    daily_vol = 0.035  # ~3.5% дневная вол → annualized ≈ 55%
    for i in range(1, n):
        ret = np.random.normal(loc=0.0002, scale=daily_vol)
        market_prices.append(market_prices[-1] * (1 + ret))

    # === RVI — фиксированный высокий уровень (40) ===
    rvi_values = [40.0] * n

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
    eqmx = make_ohlc_df(dates, eqmx_prices, 1_000_000)
    gold = make_ohlc_df(dates, gold_prices, 10_000_000)
    oblg = make_ohlc_df(dates, oblg_prices, 500_000)
    lqdt = make_ohlc_df(dates, lqdt_prices, 0)

    moex = make_ohlc_df(dates, market_prices, 0)  # рыночный индекс
    rvi = make_ohlc_df(dates, rvi_values, 0)     # RVI как OHLC

    # Сохраняем
    for name, df in [
        ("EQMX", eqmx),
        ("GOLD", gold),
        ("OBLG", oblg),
        ("LQDT", lqdt),
        ("MOEX", moex),
        ("RVI", rvi)
    ]:
        df.to_csv(os.path.join(output_dir, f'test05_{name}.csv'), index=False)

    print("✅ Тест 5: данные сгенерированы (высокая волатильность + рост EQMX)")

if __name__ == "__main__":
    main()
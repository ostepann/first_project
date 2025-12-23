# backtest_platform/validation/test03/test03_run_validation.py

import os
import sys
import pandas as pd

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backtest_platform.strategies.dual_momentum import DualMomentumStrategy
from backtest_platform.utils import load_market_data

def main():
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    import test03_optimization_config_validation as cfg

    # Загрузка данных
    data = {}
    for ticker in cfg.tickers:
        df = load_market_data(os.path.join(cfg.data_dir, f'test03_{ticker}.csv'))
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        data[ticker] = df

    rvi_data = load_market_data(os.path.join(cfg.data_dir, 'test03_RVI.csv'))
    rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])

    strategy = DualMomentumStrategy(
        base_lookback=20,
        base_vol_window=20,
        max_vol_threshold=1.0,
        use_rvi_adaptation=True
    )

    # Сохраняем оригинальный метод
    original_generate = strategy.generate_signal

    # Модифицируем стратегию для возврата lookback
    def generate_with_lookback(data_dict, market_data=None, rvi_data=None, **kwargs):
        # Определяем уровень RVI
        rvi_level = 'medium'
        if rvi_data is not None and not rvi_data.empty:
            rvi_value = rvi_data['CLOSE'].iloc[-1]
            if rvi_value < 15:
                rvi_level = 'low'
            elif rvi_value >= 25:
                rvi_level = 'high'
        # Получаем адаптивные окна
        windows = strategy._get_adaptive_windows(rvi_level)
        lookback_used = windows['lookback_period']
        # Получаем оригинальный сигнал
        signal = original_generate(data_dict, market_data, rvi_data, **kwargs)
        # Расширяем сигнал отладочной информацией
        signal['lookback_used'] = lookback_used
        signal['rvi_level'] = rvi_level
        return signal

    strategy.generate_signal = generate_with_lookback

    # Выбираем даты
    dates = data['EQMX']['TRADEDATE'].tolist()
    date_low_rvi = dates[10]   # RVI=10
    date_high_rvi = dates[30]  # RVI=40

    # Функция для получения полного сигнала на дату
    def get_signal_on_date(date):
        daily_dfs = {}
        for ticker, df in data.items():
            daily_dfs[ticker] = df[df['TRADEDATE'] <= date].copy()
        rvi_on_date = rvi_data[rvi_data['TRADEDATE'] <= date].iloc[[-1]]
        return strategy.generate_signal(daily_dfs, rvi_data=rvi_on_date)

    # Получаем сигналы
    signal_low = get_signal_on_date(date_low_rvi)
    signal_high = get_signal_on_date(date_high_rvi)

    print("✅ Тест 3: Адаптация окон под RVI (продуктивная стратегия)")
    print(f"При RVI=10 (low): lookback = {signal_low['lookback_used']} (ожидаемо: 24)")
    print(f"При RVI=40 (high): lookback = {signal_high['lookback_used']} (ожидаемо: 14)")

    test_pass = (
        signal_low['lookback_used'] == 24 and
        signal_high['lookback_used'] == 14
    )

    if test_pass:
        print("✅ ТЕСТ ПРОЙДЕН")
        return True
    else:
        print("❌ ТЕСТ ПРОВАЛЕН")
        return False

if __name__ == "__main__":
    main()
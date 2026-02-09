# backtest_platform/test_rvi_impact.py
"""
Тест влияния rvi_low_multiplier на решения стратегии в день с низким RVI.
Автоматически находит дату с RVI < 18 из загруженных данных.
"""

import pandas as pd
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from strategies.dual_momentum import DualMomentumStrategy
from utils import load_market_data
import optimization_config as cfg

# Загрузка данных
data_dir = os.path.join(project_root, cfg.data_dir)
data = {}
for ticker in cfg.tickers:
    df = load_market_data(os.path.join(data_dir, f'{ticker}.csv'))
    df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
    data[ticker] = df

market_df = data[cfg.market_ticker].copy()
rvi_data = load_market_data(os.path.join(data_dir, f'{cfg.rvi_ticker}.csv'))
rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])

# 🔑 НАХОДИМ ДАТУ С НИЗКИМ RVI (<18)
rvi_low_days = rvi_data[rvi_data['CLOSE'] < 18]
if rvi_low_days.empty:
    print("❌ НЕ НАЙДЕНО дней с RVI < 18 в данных!")
    print(f"Минимальное значение RVI: {rvi_data['CLOSE'].min():.2f}")
    sys.exit(1)

test_date = rvi_low_days.iloc[0]['TRADEDATE']
rvi_value = rvi_low_days.iloc[0]['CLOSE']
print(f"✅ Найдена дата с низким RVI: {test_date.date()} (RVI={rvi_value:.2f})")

# Фильтрация данных до тестовой даты
daily_dfs = {ticker: df[df['TRADEDATE'] <= test_date].copy() for ticker, df in data.items()}
market_slice = market_df[market_df['TRADEDATE'] <= test_date].copy()
rvi_slice = rvi_data[rvi_data['TRADEDATE'] <= test_date].copy()

# Две стратегии с разными мультипликаторами
strat1 = DualMomentumStrategy(
    base_lookback=28,
    base_vol_window=9,
    market_vol_window=21,
    rvi_low_multiplier=1.0,
    rvi_high_multiplier=0.73,
    rvi_low_threshold=18,
    rvi_medium_threshold=25,
    rvi_high_exit_threshold=42,
    use_rvi_adaptation=True,
    debug=True
)
strat2 = DualMomentumStrategy(
    base_lookback=28,
    base_vol_window=9,
    market_vol_window=21,
    rvi_low_multiplier=2.0,
    rvi_high_multiplier=0.73,
    rvi_low_threshold=18,
    rvi_medium_threshold=25,
    rvi_high_exit_threshold=42,
    use_rvi_adaptation=True,
    debug=True
)

# Генерация сигналов
print("\n" + "="*70)
print("Стратегия с rvi_low_multiplier=1.0:")
signal1 = strat1.generate_signal(daily_dfs, market_data=market_slice, rvi_data=rvi_slice)
print(f"  RVI уровень: {signal1.get('rvi_level')}")
print(f"  Адаптированное окно рынка: {signal1.get('used_market_vol_window')}")
print(f"  Выбранный актив: {signal1.get('selected')}")
print(f"  Фильтр сработал: {signal1.get('market_filter_triggered')} ({signal1.get('market_filter_stage')})")

print("\n" + "="*70)
print("Стратегия с rvi_low_multiplier=2.0:")
signal2 = strat2.generate_signal(daily_dfs, market_data=market_slice, rvi_data=rvi_slice)
print(f"  RVI уровень: {signal2.get('rvi_level')}")
print(f"  Адаптированное окно рынка: {signal2.get('used_market_vol_window')}")
print(f"  Выбранный актив: {signal2.get('selected')}")
print(f"  Фильтр сработал: {signal2.get('market_filter_triggered')} ({signal2.get('market_filter_stage')})")

print("\n" + "="*70)
if signal1.get('selected') != signal2.get('selected'):
    print("✅ РАЗЛИЧИЯ В РЕШЕНИЯХ: адаптация влияет на выбор актива")
elif signal1.get('market_filter_triggered') != signal2.get('market_filter_triggered'):
    print("✅ РАЗЛИЧИЯ В ФИЛЬТРЕ: адаптация влияет на срабатывание рыночного фильтра")
else:
    print("⚠️  ОДИНАКОВЫЕ РЕШЕНИЯ: адаптация не влияет на итоговое решение")
    print("   Возможные причины:")
    print("   1. Рыночный фильтр срабатывает для обоих окон (21 и 42)")
    print("   2. Адаптация окон не меняет ранжирование активов")
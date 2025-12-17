import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy
from optimizer import optimize_dual_momentum
from utils import load_market_data

def main():
    # === ЗАГРУЗКА ДАННЫХ ИЗ CSV ===
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    tickers = ['GOLD', 'EQMX', 'OBLG', 'LQDT']
    data = {}

    print("Загрузка данных из CSV...")
    for ticker in tickers:
        file_path = os.path.join(data_dir, f'{ticker}.csv')
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ Файл не найден: {file_path}")
        df = load_market_data(file_path)
        if 'TRADEDATE' not in df.columns:
            raise ValueError(f"❌ В {ticker}.csv отсутствует колонка TRADEDATE")
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        data[ticker] = df
        print(f"✅ {ticker}: {df['TRADEDATE'].min().date()} → {df['TRADEDATE'].max().date()} ({len(df)} строк)")

    market_df = data['EQMX'].copy()

    # === ОПРЕДЕЛЕНИЕ, НУЖЕН ЛИ ФИЛЬТР ПО ВРЕМЕНИ ===
    # Проверим, содержит ли TRADEDATE время (а не только дату)
    sample_date = data['EQMX']['TRADEDATE'].iloc[0]
    has_time = sample_date.time() != pd.Timestamp('00:00:00').time()
    trade_time_filter = '12:00:00' if has_time else None

    if has_time:
        print("⏳ Обнаружено время в данных — будет применён фильтр 12:00")
    else:
        print("📅 Данные дневные — фильтр по времени отключён")

    # === ЗАПУСК БЭКТЕСТА ===
    strategy = DualMomentumStrategy(
        lookback_period=126,
        vol_window=20,
        max_vol_threshold=0.35
    )

    bt = Backtester(
        commission={'EQMX': 0.005, 'OBLG': 0.003, 'GOLD': 0.006},
        default_commission=0.0,
        slippage=0.001,
        use_slippage=True,
        trade_time_filter=trade_time_filter
    )

    print("\n▶ Запуск бэктеста...")
    result = bt.run(strategy, data, market_data=market_df)

    print("\n✅ Бэктест завершён:")
    print(f"Финальная стоимость: {result['final_value']:,.2f}")
    print(f"CAGR: {result['cagr']:.2%}")
    print(f"Sharpe: {result['sharpe']:.2f}")
    print(f"Max DD: {result['max_drawdown']:.2%}")

    # === ЗАПУСК ОПТИМИЗАЦИИ (опционально, можно закомментировать для ускорения) ===
    print("\n🔍 Запуск оптимизации параметров...")
    param_grid = {
        'lookback_period': [60, 126],
        'vol_window': [10, 20],
        'max_vol_threshold': [0.3, 0.35]
    }

    opt_results = optimize_dual_momentum(
        data,
        market_df,
        param_grid,
        commission={'EQMX': 0.005, 'OBLG': 0.003, 'GOLD': 0.006},
        trade_time_filter=trade_time_filter
    )

    print("\n🏆 Топ-3 комбинации параметров:")
    print(opt_results[['lookback_period', 'vol_window', 'max_vol_threshold', 'sharpe', 'cagr']].head(3))

if __name__ == "__main__":
    main()

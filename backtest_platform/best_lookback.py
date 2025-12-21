# backtest_platform/run_example.py

import os
import sys
import pandas as pd
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy
from utils import load_market_data

def main():
    import optimization_config as cfg

    # Загрузка данных
    data_dir = os.path.join(project_root, cfg.data_dir)
    data = {}
    for ticker in cfg.tickers:
        df = load_market_data(os.path.join(data_dir, f'{ticker}.csv'))
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        data[ticker] = df

    # Загрузка RVI
    rvi_path = os.path.join(data_dir, 'RVI.csv')
    if not os.path.exists(rvi_path):
        raise FileNotFoundError("RVI.csv обязателен для этого анализа!")
    rvi_data = load_market_data(rvi_path)
    rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])
    rvi_data = rvi_data[['TRADEDATE', 'CLOSE']].rename(columns={'CLOSE': 'RVI'})

    market_df = data[cfg.market_ticker].copy()

    # Слияние данных с RVI по дате
    all_dates = set()
    for df in data.values():
        all_dates.update(df['TRADEDATE'])
    all_dates = sorted(all_dates)

    merged_data = []
    for date in all_dates:
        rvi_row = rvi_data[rvi_data['TRADEDATE'] == date]
        if rvi_row.empty:
            continue
        rvi_value = rvi_row['RVI'].iloc[0]
        
        # Сбор данных по активам на дату
        assets = {}
        valid = True
        for ticker, df in data.items():
            asset_row = df[df['TRADEDATE'] == date]
            if asset_row.empty:
                valid = False
                break
            assets[ticker] = df[df['TRADEDATE'] <= date].copy()
        if not valid:
            continue

        merged_data.append({
            'date': date,
            'rvi': rvi_value,
            'assets': assets,
            'market': market_df[market_df['TRADEDATE'] <= date].copy()
        })

    if not merged_data:
        raise ValueError("Нет совпадающих дат между RVI и данными активов!")

    # Определение диапазонов RVI
    rvi_bins = [
    #    (0, 15, "RVI < 15"), #95
    #    (15, 20, "15 ≤ RVI < 20"),  #95
    #    (20, 25, "20 ≤ RVI < 25"), #103
    #    (25, 30, "25 ≤ RVI < 30"), #95
        (30, 35, "30 ≤ RVI < 35"), #116
        (35, 100, "RVI ≥ 35")  #116
    ]

    # Список lookback для тестирования
    lookbacks_to_test = [110, 111, 112, 113, 114, 115, 116, 117, 118]
#    lookbacks_to_test = [50, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110]
    results = []

    print("🔍 Анализ оптимального lookback для каждого диапазона RVI...\n")

    for min_rvi, max_rvi, label in rvi_bins:
        # Фильтрация данных по диапазону RVI
        segment_data = [item for item in merged_data if min_rvi <= item['rvi'] < max_rvi]
        if not segment_data:
            print(f"⚠️  Нет данных для диапазона: {label}")
            continue

        print(f"📊 Диапазон: {label} (найдено {len(segment_data)} дней)")
        segment_results = []

        for lookback in lookbacks_to_test:
            # Собираем данные только для этого сегмента
            segment_dict = {}
            for ticker in cfg.tickers:
                # Объединяем все DataFrame'ы актива в сегменте
                dfs = [item['assets'][ticker] for item in segment_data if ticker in item['assets']]
                if dfs:
                    segment_dict[ticker] = pd.concat(dfs).drop_duplicates().sort_values('TRADEDATE')
            
            if not segment_dict:
                continue

            try:
                strategy = DualMomentumStrategy(
                    base_lookback=lookback,
                    base_vol_window=20,  # фиксируем для чистоты эксперимента
                    max_vol_threshold=0.4
                )
                market_segment = pd.concat([item['market'] for item in segment_data]).drop_duplicates().sort_values('TRADEDATE')
                
                bt = Backtester(
                    commission=cfg.commission,
                    default_commission=cfg.default_commission,
                    slippage=cfg.slippage,
                    use_slippage=cfg.use_slippage
                )
                res = bt.run(strategy, segment_dict, market_data=market_segment, initial_capital=100_000)
                segment_results.append({
                    'lookback': lookback,
                    'cagr': res['cagr'],
                    'sharpe': res['sharpe'],
                    'days': len(segment_data)
                })
                print(f"  → lookback={lookback}: CAGR={res['cagr']:.2%}, Sharpe={res['sharpe']:.2f}")
            except Exception as e:
                print(f"  → lookback={lookback}: ❌ Ошибка ({str(e)[:50]})")
                continue

        if segment_results:
            best = max(segment_results, key=lambda x: x['cagr'])
            results.append({
                'rvi_range': label,
                'best_lookback': best['lookback'],
                'best_cagr': best['cagr'],
                'best_sharpe': best['sharpe'],
                'days_in_range': len(segment_data)
            })
        print()

    # Вывод итогов
    print("🏆 ИТОГОВЫЕ РЕКОМЕНДАЦИИ:")
    summary_df = pd.DataFrame(results)
    print(summary_df.to_string(index=False))

    # Сохранение
    summary_df.to_csv("rvi_lookback_recommendations.csv", index=False)
    print("\n✅ Рекомендации сохранены в rvi_lookback_recommendations.csv")

if __name__ == "__main__":
    main()
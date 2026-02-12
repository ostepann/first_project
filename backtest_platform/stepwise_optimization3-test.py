# backtest_platform/stepwise_optimization3-test.py

"""
Скрипт для пошаговой оптимизации параметров стратегии Dual Momentum.
Версия: 1.3.0 (с расширенной диагностикой RVI-адаптации)
"""

import os
import sys
import pandas as pd

__version__ = "1.3.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-08"

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy
from optimizer import optimize_dual_momentum
from utils import load_market_data
import optimization_config as cfg


def load_all_data():
    data_dir = os.path.join(project_root, cfg.data_dir)
    data = {}
    print("Загрузка данных из CSV...")
    for ticker in cfg.tickers:
        file_path = os.path.join(data_dir, f'{ticker}.csv')
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ Файл не найден: {file_path}")
        df = load_market_data(file_path)
        if 'TRADEDATE' not in df.columns:
            raise ValueError(f"❌ В {ticker}.csv отсутствует колонка TRADEDATE")
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        data[ticker] = df
        print(f"✅ {ticker}: {df['TRADEDATE'].min().date()} → {df['TRADEDATE'].max().date()} ({len(df)} строк)")

    rvi_path = os.path.join(data_dir, f'{cfg.rvi_ticker}.csv')
    rvi_data = None
    if os.path.exists(rvi_path):
        rvi_data = load_market_data(rvi_path)
        rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])
        print(f"✅ {cfg.rvi_ticker} загружен: {rvi_data['TRADEDATE'].min().date()} → {rvi_data['TRADEDATE'].max().date()}")
    else:
        print(f"⚠️ {cfg.rvi_ticker}.csv не найден — используется средний уровень волатильности")

    market_df = data[cfg.market_ticker].copy()
    return data, market_df, rvi_data


def run_stepwise_optimization(temp_param_grid, step_name):
    print(f"\n🚀 ЗАПУСК ОПТИМИЗАЦИИ: {step_name}")
    from itertools import product
    total_combinations = len(list(product(*temp_param_grid.values())))
    print(f"⚙️  Количество комбинаций: {total_combinations}")

    data, market_df, rvi_data = load_all_data()

    has_time = data[cfg.tickers[0]]['TRADEDATE'].iloc[0].time() != pd.Timestamp('00:00:00').time()
    trade_time_filter = cfg.trading_start_time if has_time and cfg.time_filter_enabled else None

    # === ДИАГНОСТИКА 1: Проверка загрузки RVI ===
    if rvi_data is not None and not rvi_data.empty:
        rvi_vals = rvi_data['CLOSE'].dropna()
        print(f"\n📊 Статистика RVI (всего {len(rvi_vals)} дней):")
        print(f"   RVI < {cfg.production_params.get('rvi_low_threshold', 14)} (низкий): {(rvi_vals < 14).sum()} дней ({(rvi_vals < 14).mean()*100:.1f}%)")
        print(f"   RVI ≥ {cfg.production_params.get('rvi_high_exit_threshold', 42)} (фильтр): {(rvi_vals >= 42).sum()} дней ({(rvi_vals >= 42).mean()*100:.1f}%)")
        print(f"   Первые 5 значений RVI: {rvi_vals.head().values.tolist()}")
    else:
        print("⚠️  RVI данные НЕ ЗАГРУЖЕНЫ — адаптация не будет работать!")

    try:
        # === ДИАГНОСТИКА 2: Тест влияния rvi_low_multiplier на решения стратегии ===
        print("\n🔍 Тест влияния rvi_low_multiplier на решения стратегии (первые 30 дней)...")
        test_dates = sorted(set.union(*[set(df['TRADEDATE']) for df in data.values()]))[:30]
        
        # Создаём две стратегии с разными мультипликаторами
        strat_low = DualMomentumStrategy(
            base_lookback=28, base_vol_window=9, market_vol_window=21,
            rvi_low_multiplier=1.0, rvi_high_multiplier=0.73,
            rvi_low_threshold=14, rvi_medium_threshold=25, rvi_high_exit_threshold=42,
            use_rvi_adaptation=True, debug=False
        )
        strat_high = DualMomentumStrategy(
            base_lookback=28, base_vol_window=9, market_vol_window=21,
            rvi_low_multiplier=2.0, rvi_high_multiplier=0.73,
            rvi_low_threshold=14, rvi_medium_threshold=25, rvi_high_exit_threshold=42,
            use_rvi_adaptation=True, debug=False
        )
        
        # Собираем различия в решениях
        differences = []
        for date in test_dates:
            daily_dfs = {ticker: df[df['TRADEDATE'] <= date].copy() for ticker, df in data.items()}
            current_rvi = rvi_data[rvi_data['TRADEDATE'] <= date].copy() if rvi_data is not None else None
            
            signal_low = strat_low.generate_signal(daily_dfs, market_data=market_df, rvi_data=current_rvi)
            signal_high = strat_high.generate_signal(daily_dfs, market_data=market_df, rvi_data=current_rvi)
            
            if signal_low.get('selected') != signal_high.get('selected') or \
               signal_low.get('used_market_vol_window') != signal_high.get('used_market_vol_window'):
                differences.append({
                    'date': date,
                    'rvi_level': signal_low.get('rvi_level'),
                    'window_low': signal_low.get('used_market_vol_window'),
                    'window_high': signal_high.get('used_market_vol_window'),
                    'selected_low': signal_low.get('selected'),
                    'selected_high': signal_high.get('selected'),
                    'filter_triggered': signal_low.get('market_filter_triggered')
                })
        
        if differences:
            print(f"✅ Обнаружены различия в {len(differences)} из 30 дней:")
            for diff in differences[:5]:  # Первые 5 различий
                print(f"   {diff['date'].date()}: RVI={diff['rvi_level']}, окно={diff['window_low']}→{diff['window_high']}, "
                      f"актив={diff['selected_low']}→{diff['selected_high']}, фильтр={diff['filter_triggered']}")
        else:
            print("⚠️  НЕ обнаружено различий в решениях при разных rvi_low_multiplier (первые 30 дней)")
            print("   Возможные причины:")
            print("   1. Рыночный фильтр всегда блокирует торговлю в дни с низким RVI")
            print("   2. Адаптация окон не влияет на ранжирование активов")
            print("   3. Недостаточно дней с низким RVI в тестовом периоде")

        # === ЗАПУСК ОПТИМИЗАЦИИ ===
        results_df = optimize_dual_momentum(
            data_dict=data,  # ← ИСПРАВЛЕНО: было data_dict, теперь data
            market_data=market_df,
            rvi_data=rvi_data,
            param_grid=temp_param_grid,
            commission=cfg.commission,
            initial_capital=cfg.initial_capital,
            trade_time_filter=trade_time_filter
        )

        # === ДИАГНОСТИКА 3: Анализ результатов оптимизации ===
        if 'rvi_low_multiplier' in results_df.columns and 'used_market_vol_window' in results_df.columns:
            print(f"\n📈 Анализ влияния rvi_low_multiplier на метрики:")
            summary = results_df.groupby('rvi_low_multiplier').agg({
                'used_market_vol_window': 'first',
                'sharpe': 'first',
                'cagr': 'first',
                'max_drawdown': 'first'
            }).reset_index()
            print(summary.to_string(index=False))
            
            # Проверка вариации метрик
            sharpe_std = results_df['sharpe'].std()
            if sharpe_std < 1e-6:
                print(f"\n⚠️  ВАЖНО: Стандартное отклонение Sharpe = {sharpe_std:.6f} (почти нулевое)")
                print("   Это означает, что разные значения rvi_low_multiplier дают ИДЕНТИЧНЫЕ торговые решения.")
                print("   Рекомендуется проверить:")
                print("   - Срабатывание рыночного фильтра в дни с низким RVI")
                print("   - Влияние адаптации окон на расчёт волатильности активов")

        # 🔑 ДИАГНОСТИКА: Проверка влияния параметров
        if 'market_vol_window' in results_df.columns and len(results_df) > 1:
            unique_windows = results_df['market_vol_window'].nunique()
            if unique_windows > 1:
                group_cols = [col for col in results_df.columns 
                            if col not in ['market_vol_window', 'cagr', 'sharpe', 'max_drawdown', 'final_value', 'used_market_vol_window']]
                if group_cols:
                    grouped = results_df.groupby(group_cols)['sharpe'].nunique()
                    if (grouped > 1).any():
                        print(f"✅ Параметр market_vol_window ВЛИЯЕТ на результаты")
                    else:
                        print(f"⚠️  Sharpe одинаков при разных market_vol_window — фильтр может не срабатывать")
            else:
                print(f"ℹ️  Тестирование с фиксированным market_vol_window={results_df['market_vol_window'].iloc[0]}")

        top_results = results_df.sort_values('sharpe', ascending=False).head(5)
        print(f"\n🏆 Топ-5 результатов для '{step_name}':")
        display_cols = ['rvi_low_multiplier', 'used_market_vol_window', 'cagr', 'sharpe', 'max_drawdown']
        display_cols = [c for c in display_cols if c in top_results.columns]
        print(top_results[display_cols].to_string(index=False))

        output_dir = os.path.join(project_root, "data-optimization")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"optimization_results_{step_name.lower().replace(' ', '_')}.csv")
        results_df.to_csv(output_file, index=False)
        print(f"\n✅ Результаты сохранены в '{output_file}'")

        best_params = top_results.iloc[0].to_dict()
        for metric in ['final_value', 'cagr', 'sharpe', 'max_drawdown', 'used_market_vol_window']:
            best_params.pop(metric, None)
        return best_params

    except Exception as e:
        print(f"❌ Ошибка при оптимизации: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    temp_grid_step1 = {
        'base_lookback': [28],
        'market_vol_window': [21],
        'base_vol_window': [9],
        'market_vol_threshold': [0.35],
        'max_vol_threshold': [0.30],
        'rvi_high_exit_threshold': [42],
        'rvi_low_threshold': [14],
        'rvi_medium_threshold': [25],
        'rvi_low_multiplier': [1.3],  # Исправлено: было 12.0 (опечатка)
        'rvi_high_multiplier': [0.73],
        'use_rvi_adaptation': [True],  # Явно включаем адаптацию
        'use_trend_filter': [True],
        'trend_window': [60],
        'trend_filter_on_insufficient_data': ['allow'],
        'bare_mode': [False],
        'risk_free_ticker': ['LQDT'],
        'debug': [False]
    }

    best_params_step1 = run_stepwise_optimization(temp_grid_step1, "Step_3_RVI_Multiplier")

    if best_params_step1:
        print(f"\n✨ Лучшие параметры после оптимизации:\n{best_params_step1}")
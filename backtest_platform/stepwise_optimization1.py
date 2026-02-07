# backtest_platform/stepwise_optimization.py

"""
Скрипт для пошаговой оптимизации параметров стратегии Dual Momentum.
Версия: 1.1.0 (с поддержкой диагностики рыночного фильтра)
"""

import os
import sys
import pandas as pd

__version__ = "1.1.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-02"

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

    try:
        results_df = optimize_dual_momentum(
            data_dict=data,
            market_data=market_df,
            rvi_data=rvi_data,
            param_grid=temp_param_grid,
            commission=cfg.commission,
            initial_capital=cfg.initial_capital,
            trade_time_filter=trade_time_filter
        )

        # 🔑 ДИАГНОСТИКА: Проверка влияния market_vol_window
        if 'market_vol_window' in results_df.columns and len(results_df) > 1:
            unique_windows = results_df['market_vol_window'].nunique()
            if unique_windows > 1:
                # Группируем по комбинации других параметров
                group_cols = [col for col in results_df.columns if col not in ['market_vol_window', 'cagr', 'sharpe', 'max_drawdown', 'final_value']]
                grouped = results_df.groupby(group_cols)['sharpe'].nunique()
                if (grouped > 1).any():
                    print(f"✅ Параметр market_vol_window ВЛИЯЕТ на результаты (обнаружены различия в Sharpe для одинаковых комбинаций других параметров)")
                else:
                    print(f"⚠️  Внимание: для всех комбинаций других параметров Sharpe одинаков при разных market_vol_window. "
                          f"Возможно, рыночный фильтр не срабатывает в вашем периоде данных.")
            else:
                print(f"ℹ️  Тестирование проводилось с фиксированным market_vol_window={results_df['market_vol_window'].iloc[0]}")

        top_results = results_df.sort_values('sharpe', ascending=False).head(5)
        print(f"\n🏆 Топ-5 результатов для '{step_name}':")
        display_cols = ['base_lookback', 'base_vol_window', 'market_vol_window', 'cagr', 'sharpe', 'max_drawdown']
        display_cols = [c for c in display_cols if c in top_results.columns]
        print(top_results[display_cols].to_string(index=False))

#        output_file = f"optimization_results_{step_name.lower().replace(' ', '_')}.csv"
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

    # === ШАГ 1: Оптимизация окон анализа С ПОЛНЫМ ДИАПАЗОНОМ market_vol_window ===
    temp_grid_step1 = {
        'base_lookback': [28, 29],
        'market_vol_window': [21],  # ← ПОЛНЫЙ ДИАПАЗОН ДЛЯ ТЕСТИРОВАНИЯ
        'base_vol_window': [7, 8, 9],
        'max_vol_threshold': [cfg.production_params['max_vol_threshold']],
        'market_vol_threshold': [cfg.production_params['market_vol_threshold']],
        'rvi_high_exit_threshold': [cfg.production_params['rvi_high_exit_threshold']],
        'rvi_low_threshold': [cfg.production_params['rvi_low_threshold']],
        'rvi_medium_threshold': [cfg.production_params['rvi_medium_threshold']],
        'rvi_low_multiplier': [cfg.production_params['rvi_low_multiplier']],
        'rvi_high_multiplier': [cfg.production_params['rvi_high_multiplier']],
        'use_rvi_adaptation': [cfg.production_params['use_rvi_adaptation']],
        'use_trend_filter': [cfg.production_params['use_trend_filter']],
        'trend_window': [cfg.production_params['trend_window']],
        'trend_filter_on_insufficient_data': [cfg.production_params['trend_filter_on_insufficient_data']],
        'bare_mode': [cfg.production_params['bare_mode']],
        'risk_free_ticker': [cfg.production_params['risk_free_ticker']],
        'debug': [False]  # ← Отключено по умолчанию (включить True для диагностики)
    }

    best_params_step1 = run_stepwise_optimization(temp_grid_step1, "Step_1_Windows")

    if best_params_step1:
        print(f"\n✨ Лучшие параметры после Шага 1:\n{best_params_step1}")
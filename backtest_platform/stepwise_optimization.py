# backtest_platform/stepwise_optimization.py
"""
Скрипт для пошаговой оптимизации параметров стратегии Dual Momentum.
Версия: 1.0.0
Цель: Минимизировать количество тестов при поиске оптимальных параметров.
"""

import os
import sys
import pandas as pd

# Метаданные модуля
__version__ = "1.0.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-01"

# Настройка пути к корню проекта
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy
from optimizer import optimize_dual_momentum # Импортируем функцию оптимизации
from utils import load_market_data
import optimization_config as cfg # Импортируем вашу конфигурацию


def load_all_data():
    """Загружает все необходимые данные, как в run_example.py."""
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

    # Загрузка RVI
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
    """
    Запускает оптимизацию с заданной временной сеткой параметров.
    
    Args:
        temp_param_grid (dict): Временная сетка для оптимизации (например, temp_grid_step1).
        step_name (str): Название шага для логгирования и сохранения результатов.
    """
    print(f"\n🚀 ЗАПУСК ОПТИМИЗАЦИИ: {step_name}")
    # Рассчитываем количество комбинаций
    from itertools import product
    total_combinations = len(list(product(*temp_param_grid.values())))
    print(f"⚙️  Количество комбинаций: {total_combinations}")

    # Загрузка данных
    data, market_df, rvi_data = load_all_data()

    # Определяем, есть ли в данных время или только дата
    has_time = data[cfg.tickers[0]]['TRADEDATE'].iloc[0].time() != pd.Timestamp('00:00:00').time()
    trade_time_filter = cfg.trading_start_time if has_time and cfg.time_filter_enabled else None

    try:
        # Запуск оптимизации
        results_df = optimize_dual_momentum(
            data_dict=data,
            market_data=market_df,
            rvi_data=rvi_data,
            param_grid=temp_param_grid,
            commission=cfg.commission,
            initial_capital=cfg.initial_capital,
            trade_time_filter=trade_time_filter
            # ⚠️ БОЛЬШЕ НЕ НУЖНО ПЕРЕДАВАТЬ: default_commission, slippage, use_slippage
        )

        # Сортировка и вывод лучших результатов
        top_results = results_df.sort_values('sharpe', ascending=False).head(5)
        print(f"\n🏆 Топ-5 результатов для '{step_name}':")
        print(top_results.to_string(index=False))

        # Сохранение полных результатов
        output_file = f"optimization_results_{step_name.lower().replace(' ', '_')}.csv"
        results_df.to_csv(output_file, index=False)
        print(f"\n✅ Результаты сохранены в '{output_file}'")

        # Возвращаем лучшие параметры для следующего шага
        best_params = top_results.iloc[0].to_dict()
        # Удаляем служебные столбцы метрик, оставляя только параметры стратегии
        for metric in ['final_value', 'cagr', 'sharpe', 'max_drawdown']:
            best_params.pop(metric, None)
        return best_params

    except Exception as e:
        print(f"❌ Ошибка при оптимизации: {e}")
        return None


if __name__ == "__main__":
    # === ШАГ 1: Оптимизация окон анализа ===
    temp_grid_step1 = {
        'base_lookback': [28, 29],
        'market_vol_window': [10],  #, 40, 50, 60, 70, 80, 90, 100, 110, 120],
        'base_vol_window': [7, 8, 9], # Зафиксировано
        
        # Все остальные параметры берутся из production_params
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
        'risk_free_ticker': [cfg.production_params['risk_free_ticker']]
    }

    best_params_step1 = run_stepwise_optimization(temp_grid_step1, "Step_1_Windows")
    
    if best_params_step1:
        print(f"\n✨ Лучшие параметры после Шага 1:\n{best_params_step1}")
        # Здесь вы можете обновить cfg.production_params или создать новый словарь для следующего шага
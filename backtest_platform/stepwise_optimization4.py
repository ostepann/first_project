# backtest_platform/stepwise_optimization4.py

"""
Скрипт для пошаговой оптимизации параметров стратегии Dual Momentum.
Версия: 1.3.0 (интеграция модульной конфигурации + улучшенная диагностика)
"""

import os
import sys
import pandas as pd

__version__ = "1.3.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-13"

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy
from optimizer import optimize_dual_momentum
from utils import load_market_data

# 🔑 ИМПОРТ ИЗ МОДУЛЬНОЙ СИСТЕМЫ КОНФИГУРАЦИИ
from config import (
    data_dir, tickers, market_ticker, rvi_ticker,
    commission, initial_capital,
    trading_start_time, time_filter_enabled,
    production_params,
    CRITICAL_WARNING_COMMON, CRITICAL_WARNING_STRATEGY
)


def load_all_data():
    """Загрузка рыночных данных из CSV-файлов."""
    data_path = os.path.join(project_root, data_dir)
    data = {}
    print("\n📥 ЗАГРУЗКА ДАННЫХ ИЗ CSV...")
    for ticker in tickers:
        file_path = os.path.join(data_path, f'{ticker}.csv')
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ Файл не найден: {file_path}")
        df = load_market_data(file_path)
        if 'TRADEDATE' not in df.columns:
            raise ValueError(f"❌ В {ticker}.csv отсутствует колонка TRADEDATE")
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        data[ticker] = df
        print(f"✅ {ticker}: {df['TRADEDATE'].min().date()} → {df['TRADEDATE'].max().date()} ({len(df)} строк)")

    # 🔧 ИСПРАВЛЕНИЕ: Загрузка market_df отдельно (как RVI), а не из data[tickers]
    market_path = os.path.join(data_path, f'{market_ticker}.csv')
    market_df = None
    if os.path.exists(market_path):
        market_df = load_market_data(market_path)
        market_df['TRADEDATE'] = pd.to_datetime(market_df['TRADEDATE'])
        print(f"✅ {market_ticker} загружен: {market_df['TRADEDATE'].min().date()} → {market_df['TRADEDATE'].max().date()} ({len(market_df)} строк)")
    else:
        raise FileNotFoundError(f"❌ Файл рыночного индекса не найден: {market_path}")

    rvi_path = os.path.join(data_path, f'{rvi_ticker}.csv')
    rvi_data = None
    if os.path.exists(rvi_path):
        rvi_data = load_market_data(rvi_path)
        rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])
        print(f"✅ {rvi_ticker} загружен: {rvi_data['TRADEDATE'].min().date()} → {rvi_data['TRADEDATE'].max().date()}")
    else:
        print(f"⚠️ {rvi_ticker}.csv не найден — используется средний уровень волатильности для рыночного фильтра")

    return data, market_df, rvi_data


def run_stepwise_optimization(temp_param_grid, step_name):
    """
    Запуск пошаговой оптимизации с заданной сеткой параметров.
    
    Args:
        temp_param_grid: Словарь с сеткой значений для оптимизации
        step_name: Название шага оптимизации (для логирования и сохранения результатов)
    
    Returns:
        dict: Лучшие параметры по метрике Sharpe Ratio
    """
    print(f"\n🚀 ЗАПУСК ПОШАГОВОЙ ОПТИМИЗАЦИИ: {step_name}")
    from itertools import product
    total_combinations = len(list(product(*temp_param_grid.values())))
    print(f"   ⚙️  Количество комбинаций для тестирования: {total_combinations:,}")
    
    # Валидация критического правила: разделение окон волатильности
    if 'base_vol_window' in temp_param_grid and 'market_vol_window' in temp_param_grid:
        min_base = min(temp_param_grid['base_vol_window'])
        max_market = max(temp_param_grid['market_vol_window'])
        if min_base >= max_market:
            print(f"⚠️  ВНИМАНИЕ: Обнаружено потенциальное нарушение правила разделения окон!")
            print(f"   Мин. base_vol_window={min_base} ≥ Макс. market_vol_window={max_market}")
            print(f"   Рекомендуется: base_vol_window < market_vol_window (мин. разрыв 5 дней)")

    data, market_df, rvi_data = load_all_data()

    has_time = data[tickers[0]]['TRADEDATE'].iloc[0].time() != pd.Timestamp('00:00:00').time()
    trade_time_filter = trading_start_time if has_time and time_filter_enabled else None
    if trade_time_filter:
        print(f"   ⏳ Применён фильтр по времени: {trade_time_filter}")
    else:
        print(f"   📅 Данные дневные — фильтр по времени отключён")

    try:
        results_df = optimize_dual_momentum(
            data_dict=data,
            market_data=market_df,
            rvi_data=rvi_data,
            param_grid=temp_param_grid,
            commission=commission,
            initial_capital=initial_capital,
            trade_time_filter=trade_time_filter
        )

        # 🔑 ДИАГНОСТИКА: Проверка влияния критических параметров
        print(f"\n🔍 ДИАГНОСТИКА ВЛИЯНИЯ ПАРАМЕТРОВ:")
        
        # Проверка влияния market_vol_window
        if 'market_vol_window' in results_df.columns and len(results_df) > 1:
            unique_windows = results_df['market_vol_window'].nunique()
            if unique_windows > 1:
                # Группируем по комбинации других параметров
                group_cols = [col for col in results_df.columns 
                            if col not in ['market_vol_window', 'cagr', 'sharpe', 'max_drawdown', 'final_value', 'total_trades']]
                if group_cols:
                    grouped = results_df.groupby(group_cols)['sharpe'].nunique()
                    if (grouped > 1).any():
                        print(f"✅ Параметр market_vol_window ВЛИЯЕТ на результаты (различия в Sharpe для одинаковых комбинаций)")
                    else:
                        print(f"⚠️  Внимание: для всех комбинаций других параметров Sharpe одинаков при разных market_vol_window.")
                        print(f"   Возможно, рыночный фильтр не срабатывает в вашем периоде данных или пороги завышены.")
                else:
                    print(f"ℹ️  Недостаточно параметров для группировки — пропуск анализа влияния")
            else:
                print(f"ℹ️  Тестирование проводилось с фиксированным market_vol_window={results_df['market_vol_window'].iloc[0]}")

        # Анализ распределения лучших результатов по активам
        if 'selected_ticker' in results_df.columns:
            top_20 = results_df.nlargest(int(len(results_df) * 0.2), 'sharpe')
            asset_distribution = top_20['selected_ticker'].value_counts(normalize=True) * 100
            print(f"\n📊 Распределение лучших 20% комбинаций по активам:")
            for asset, pct in asset_distribution.items():
                bar = '█' * int(pct / 5)
                print(f"   {asset:6s}: {pct:5.1f}% {bar}")

        # Вывод топ-5 результатов
        top_results = results_df.sort_values('sharpe', ascending=False).head(5)
        print(f"\n🏆 ТОП-5 РЕЗУЛЬТАТОВ для '{step_name}':")
        display_cols = ['base_lookback', 'base_vol_window', 'market_vol_window', 
                       'market_vol_threshold', 'max_vol_threshold',
                       'cagr', 'sharpe', 'max_drawdown', 'total_trades']
        display_cols = [c for c in display_cols if c in top_results.columns]
        
        # Форматирование вывода для лучшей читаемости
        formatted = top_results[display_cols].copy()
        if 'cagr' in formatted.columns:
            formatted['cagr'] = formatted['cagr'].apply(lambda x: f"{x:.2%}")
        if 'max_drawdown' in formatted.columns:
            formatted['max_drawdown'] = formatted['max_drawdown'].apply(lambda x: f"{x:.2%}")
        if 'market_vol_threshold' in formatted.columns:
            formatted['market_vol_threshold'] = formatted['market_vol_threshold'].apply(lambda x: f"{x:.1%}")
        if 'max_vol_threshold' in formatted.columns:
            formatted['max_vol_threshold'] = formatted['max_vol_threshold'].apply(lambda x: f"{x:.1%}")
        
        print(formatted.to_string(index=False))

        # Сохранение результатов
        output_dir = os.path.join(project_root, "data-optimization")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"optimization_results_{step_name.lower().replace(' ', '_')}.csv")
        results_df.to_csv(output_file, index=False)
        print(f"\n✅ Результаты сохранены: '{output_file}'")
        print(f"   Всего записей: {len(results_df):,}")

        # Извлечение лучших параметров (без метрик производительности)
        best_params = top_results.iloc[0].to_dict()
        metrics_to_remove = [
            'final_value', 'cagr', 'sharpe', 'max_drawdown', 'total_trades',
            'calmar', 'sortino', 'volatility', 'win_rate', 'profit_factor',
            'used_market_vol_window', 'selected_ticker', 'entry_dates', 'exit_dates'
        ]
        for metric in metrics_to_remove:
            best_params.pop(metric, None)
        
        return best_params

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ ОПТИМИЗАЦИИ: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # === КРИТИЧЕСКИЕ ПРЕДУПРЕЖДЕНИЯ ПРИ ЗАПУСКЕ ===
    print(f"\n⚠️  {CRITICAL_WARNING_COMMON}")
    print(f"⚠️  {CRITICAL_WARNING_STRATEGY}")
    
    # === ШАГ 1: ОПТИМИЗАЦИЯ ОКОН ВОЛАТИЛЬНОСТИ И ПОРОГОВ ===
    # Используем значения из production_params как базу для тонкой настройки

    temp_grid_step1 = {
        'base_lookback': [30],   #Лучшие [29]
        'market_vol_window': [21],  # Фиксировано после определения оптимума (21 день = 1 месяц)
        'base_vol_window': [8],   # Лучшие [9]  # Фиксировано после определения оптимума (короткое окно для активов)
        
        # 🔑 Пороги волатильности (ГОДОВЫЕ ЗНАЧЕНИЯ!)
        'market_vol_threshold': [0.35],  # 35% годовых — оптимальный баланс защиты/участия
        'max_vol_threshold': [0.30],     # 30% годовых — блокировка экстремальных периодов
        
        # === RVI-АДАПТАЦИЯ (зафиксированы после калибровки) ===
        'rvi_high_exit_threshold': [36],   # Порог немедленного выхода в кэш (75-й перцентиль + буфер)
        'rvi_low_threshold': [20],         # Переход к режиму низкой волатильности
        'rvi_medium_threshold': [24],      # Переход к режиму высокой волатильности
        'rvi_low_multiplier': [1.4],       # Удлинение окон при низкой волатильности (+20%)
        'rvi_high_multiplier': [0.72],     # Сокращение окон при высокой волатильности (-29%)
        
        # === ФЛАГИ РЕЖИМОВ (наследуем из production_params) ===
        'use_rvi_adaptation': [True],  # [production_params['use_rvi_adaptation']],
        'use_trend_filter': [True],  # [production_params['use_trend_filter']],
        'trend_window': [60], #[production_params['trend_window']],
        'trend_filter_on_insufficient_data': [production_params['trend_filter_on_insufficient_data']],
        'bare_mode': [production_params['bare_mode']],
        'risk_free_ticker': [production_params['risk_free_ticker']],
        'debug': [False]  # Отключено для финальной оптимизации
    }

    print("\n" + "="*70)
    print("🎯 ШАГ 1: ФИНАЛЬНАЯ ВАЛИДАЦИЯ ПРОИЗВОДСТВЕННЫХ ПАРАМЕТРОВ")
    print("="*70)
    print("Цель: Подтверждение стабильности параметров на полном периоде данных")
    print(f"Базовые параметры взяты из production_cfg.py (версия {production_params.get('version', 'N/A')})")

    best_params_step1 = run_stepwise_optimization(temp_grid_step1, "Step_4_Windows_IMOEX_trend_window")

    if best_params_step1:
        print(f"\n✨ ЛУЧШИЕ ПАРАМЕТРЫ ПОСЛЕ ФИНАЛЬНОЙ ВАЛИДАЦИИ:")
        print("-" * 60)
        for key, value in sorted(best_params_step1.items()):
            # Форматирование для лучшей читаемости
            if isinstance(value, float) and key.endswith('_threshold'):
                print(f"  {key:30s}: {value:.1%} (годовых)")
            elif isinstance(value, float):
                print(f"  {key:30s}: {value:.2f}")
            else:
                print(f"  {key:30s}: {value}")
        print("-" * 60)
        
        # Сравнение с текущими production_params
        print(f"\n🔍 СРАВНЕНИЕ С ТЕКУЩИМИ PRODUCTION-ПАРАМЕТРАМИ:")
        changes = []
        for key in best_params_step1:
            if key in production_params and best_params_step1[key] != production_params[key]:
                changes.append(f"  • {key}: {production_params[key]} → {best_params_step1[key]}")
        
        if changes:
            print("Обнаружены различия:")
            for change in changes:
                print(change)
            print("\n⚠️  Рекомендуется обновить production_cfg.py после ручной проверки!")
        else:
            print("✅ Параметры полностью соответствуют текущей production-конфигурации")
    
    print("\n" + "="*70)
    print("💡 РЕКОМЕНДАЦИИ ПО ДАЛЬНЕЙШИМ ДЕЙСТВИЯМ:")
    print("="*70)
    print("1. Для поиска НОВЫХ оптимумов используйте расширенные сетки в optimization_cfg.py")
    print("2. Запустите валидацию на невидимом периоде (последние 6 месяцев данных)")
    print("3. Проверьте устойчивость параметров через walk-forward анализ")
    print("4. Перед продакшеном протестируйте на демо-счёте минимум 3 месяца")
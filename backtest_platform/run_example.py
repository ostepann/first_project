"""
Основной скрипт для запуска бэктеста с production-параметрами.
Версия: 2.2.2 (фильтрация неподдерживаемых параметров стратегии)
"""

import os
import sys
import pandas as pd
from itertools import product

__version__ = "2.2.2"
__author__ = "Oleg Dev"
__date__ = "2026-02-13"

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy
from utils import load_market_data

# 🔑 ИМПОРТ ИЗ МОДУЛЬНОЙ СИСТЕМЫ КОНФИГУРАЦИИ
from config import (
    data_dir, tickers, market_ticker, rvi_ticker,
    commission, default_commission, slippage, use_slippage,
    trading_start_time, time_filter_enabled, initial_capital,
    production_params,
    param_grid,
    CRITICAL_WARNING_COMMON, CRITICAL_WARNING_PRODUCTION
)


def filter_strategy_params(params: dict) -> dict:
    """
    Фильтрация параметров перед передачей в конструктор DualMomentumStrategy.
    
    Удаляет параметры, которые используются ТОЛЬКО для анализа/отчётов,
    но не принимаются основным конструктором стратегии.
    
    Неподдерживаемые параметры:
      • trend_r_squared_threshold — используется только в функции detect_trend() 
        для отчётов и исследований, НЕ в основном цикле стратегии
      • version — метаданные конфигурации, не параметр стратегии
      • Любые другие служебные поля из production_metadata
    """
    unsupported_keys = [
        'trend_r_squared_threshold',  # Только для отчётов тренда
        'version',                    # Метаданные конфигурации
        'expected_metrics',           # Метаданные
        'critical_fixes',             # Метаданные
        'optimization_method',        # Метаданные
        'validation_folds',           # Метаданные
        'primary_metric',             # Метаданные
        'constraints'                 # Метаданные
    ]
    
    # Создаём копию и удаляем неподдерживаемые ключи
    filtered = {k: v for k, v in params.items() if k not in unsupported_keys}
    
    # Дополнительная проверка: удаляем все ключи, начинающиеся с '_'
    filtered = {k: v for k, v in filtered.items() if not k.startswith('_')}
    
    return filtered


def main():
    # === КРИТИЧЕСКИЕ ПРЕДУПРЕЖДЕНИЯ ПРИ ЗАПУСКЕ ===
    print(f"\n⚠️  {CRITICAL_WARNING_COMMON}")
    print(f"⚠️  {CRITICAL_WARNING_PRODUCTION}")
    
    # === ЗАГРУЗКА ДАННЫХ ===
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

    rvi_path = os.path.join(data_path, f'{rvi_ticker}.csv')
    rvi_data = None
    if os.path.exists(rvi_path):
        rvi_data = load_market_data(rvi_path)
        rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])
        print(f"✅ {rvi_ticker} загружен: {rvi_data['TRADEDATE'].min().date()} → {rvi_data['TRADEDATE'].max().date()}")
    else:
        print(f"⚠️ {rvi_ticker}.csv не найден — используется средний уровень волатильности")

    market_df = data[market_ticker].copy()

    # === ДИАГНОСТИКА ВОЛАТИЛЬНОСТИ ===
    from backtest_platform.indicators.volatility import rolling_volatility
    market_returns = market_df['CLOSE'].pct_change().dropna()
    vol_series = rolling_volatility(market_returns, production_params['market_vol_window'])

    print(f"\n🔍 ДИАГНОСТИКА ВОЛАТИЛЬНОСТИ РЫНКА ({market_ticker}):")
    print(f"  Окно расчёта: {production_params['market_vol_window']} дней")
    print(f"  Мин. волатильность: {vol_series.min():.4f} ({vol_series.min():.2%})")
    print(f"  Макс. волатильность: {vol_series.max():.4f} ({vol_series.max():.2%})")
    print(f"  Средняя волатильность: {vol_series.mean():.4f} ({vol_series.mean():.2%})")
    print(f"  Доступно данных для расчёта: {len(market_returns)} дней")
    print(f"  ⚠️  Минимальное окно для стабильного расчёта: 5 дней")

    # === ФИЛЬТР ПО ВРЕМЕНИ ===
    has_time = data[tickers[0]]['TRADEDATE'].iloc[0].time() != pd.Timestamp('00:00:00').time()
    trade_time_filter = trading_start_time if has_time and time_filter_enabled else None
    if trade_time_filter:
        print(f"⏳ Применён фильтр по времени: {trade_time_filter}")
    else:
        print("📅 Данные дневные — фильтр по времени отключён")

    # === ТЕСТ РЫНОЧНОГО ФИЛЬТРА С РАЗНЫМИ ОКНАМИ (С ЗАЩИТОЙ ОТ ОШИБОК) ===
    print("\n🧪 ТЕСТ РЫНОЧНОГО ФИЛЬТРА С РАЗНЫМИ ЗНАЧЕНИЯМИ market_vol_window:")
    test_windows = [10, 21, 40, 60, 80, 100, 120]
    for window in test_windows:
        strategy = DualMomentumStrategy(
            base_lookback=20,
            base_vol_window=10,
            market_vol_window=window,
            market_vol_threshold=0.02,  # Низкий порог для гарантированного срабатывания
            debug=False
        )
        filter_result = strategy.market_filter(market_df, rvi_data)
        status = "✅ СРАБОТАЛ" if filter_result.get('triggered', False) else "❌ НЕ СРАБОТАЛ"
        
        # 🔑 ЗАЩИТА ОТ ОШИБКИ: безопасное форматирование при отсутствии данных
        used_win = filter_result.get('used_vol_window', 'N/A')
        used_win_str = f"{used_win:3d}" if isinstance(used_win, int) else f"{str(used_win):>3}"
        
        vol_value = filter_result.get('market_vol')
        vol_str = f"{vol_value:.2%}" if isinstance(vol_value, (int, float)) and vol_value is not None else "N/A"
        
        print(f"  market_vol_window={window:3d} → {status} | использовано окно={used_win_str} | волатильность={vol_str}")

    # === ЗАПУСК БЭКТЕСТА С ПРОДАКШН-ПАРАМЕТРАМИ ===
    print("\n▶ ЗАПУСК БЭКТЕСТА С ПРОИЗВОДСТВЕННЫМИ ПАРАМЕТРАМИ...")
    print(f"   Версия стратегии: {production_params.get('version', 'N/A')}")
    print(f"   Базовое окно момента: {production_params['base_lookback']} дней")
    print(f"   Окно волатильности активов: {production_params['base_vol_window']} дней")
    print(f"   Окно волатильности рынка: {production_params['market_vol_window']} дней")
    print(f"   Порог рыночной волатильности: {production_params['market_vol_threshold']:.1%} годовых")
    
    # 🔑 ИСПРАВЛЕНО: фильтрация неподдерживаемых параметров
    # Параметр 'trend_r_squared_threshold' используется ТОЛЬКО для отчётов тренда,
    # но не принимается конструктором DualMomentumStrategy
    strategy_params = filter_strategy_params(production_params)
    strategy = DualMomentumStrategy(**strategy_params)
    
    bt = Backtester(
        commission=commission,
        default_commission=default_commission,
        slippage=slippage,
        use_slippage=use_slippage,
        trade_time_filter=trade_time_filter
    )

    try:
        result = bt.run(
            strategy,
            data,
            market_data=market_df,
            rvi_data=rvi_data,
            initial_capital=initial_capital
        )
        print("\n✅ БЭКТЕСТ ЗАВЕРШЁН:")
        print(f"   Финальная стоимость: {result['final_value']:,.2f} ₽")
        print(f"   CAGR: {result['cagr']:.2%}")
        print(f"   Sharpe Ratio: {result['sharpe']:.2f}")
        print(f"   Макс. просадка: {result['max_drawdown']:.2%}")
        print(f"   Количество сделок: {result.get('total_trades', 'N/A')}")
        
        # 🔑 ДИАГНОСТИКА: Анализ использования рыночного фильтра
        if 'market_filter_stats' in result:
            stats = result['market_filter_stats']
            total_days = stats.get('total_days', 0)
            rvi_triggered = stats.get('rvi_triggered', 0)
            vol_triggered = stats.get('vol_triggered', 0)
            total_triggered = rvi_triggered + vol_triggered
            
            print(f"\n📊 СТАТИСТИКА РЫНОЧНОГО ФИЛЬТРА:")
            print(f"   Всего торговых дней: {total_days}")
            print(f"   Срабатываний по RVI (≥36): {rvi_triggered} ({rvi_triggered/total_days:.1%})")
            print(f"   Срабатываний по волатильности (≥35%): {vol_triggered} ({vol_triggered/total_days:.1%})")
            print(f"   Общая защита капитала: {total_triggered} дней ({total_triggered/total_days:.1%})")
            print(f"   Средняя длительность режима защиты: {total_triggered / max(1, (rvi_triggered > 0) + (vol_triggered > 0)):.1f} дня")

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ БЭКТЕСТЕ: {e}")
        import traceback
        traceback.print_exc()
        return

    # === ЗАПУСК ПОЛНОЙ ОПТИМИЗАЦИИ (ОПЦИОНАЛЬНО) ===
    print("\n🔍 ЗАПУСК ПОЛНОЙ ОПТИМИЗАЦИИ (опционально)...")
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    total = len(list(product(*values)))
    print(f"   ⚙️  Всего комбинаций в полной сетке: {total:,}")
    print(f"   💡 Рекомендуется использовать пошаговую оптимизацию (stepwise_optimization4.py)")
    print(f"      для избежания комбинаторного взрыва и переобучения.")


if __name__ == "__main__":
    main()
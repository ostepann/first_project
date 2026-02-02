# backtest_platform/run_example.py

"""
Основной скрипт для запуска бэктеста с production-параметрами.
Версия: 2.1.0 (с диагностикой рыночного фильтра)
"""

import os
import sys
import pandas as pd
from itertools import product

__version__ = "2.1.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-02"

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy
from utils import load_market_data
import optimization_config as cfg


def main():
    import optimization_config as cfg

    # === ЗАГРУЗКА ДАННЫХ ===
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

    # === ДИАГНОСТИКА ВОЛАТИЛЬНОСТИ ===
    from backtest_platform.indicators.volatility import rolling_volatility
    market_returns = market_df['CLOSE'].pct_change().dropna()
    vol_series = rolling_volatility(market_returns, cfg.production_params['market_vol_window'])

    print(f"\n🔍 ДИАГНОСТИКА ВОЛАТИЛЬНОСТИ РЫНКА ({cfg.market_ticker}):")
    print(f"  Окно расчёта: {cfg.production_params['market_vol_window']} дней")
    print(f"  Мин. волатильность: {vol_series.min():.4f} ({vol_series.min():.2%})")
    print(f"  Макс. волатильность: {vol_series.max():.4f} ({vol_series.max():.2%})")
    print(f"  Средняя волатильность: {vol_series.mean():.4f} ({vol_series.mean():.2%})")
    print(f"  Доступно данных для расчёта: {len(market_returns)} дней")
    print(f"  ⚠️  Минимальное окно для стабильного расчёта: 5 дней")

    # === ФИЛЬТР ПО ВРЕМЕНИ ===
    has_time = data[cfg.tickers[0]]['TRADEDATE'].iloc[0].time() != pd.Timestamp('00:00:00').time()
    trade_time_filter = cfg.trading_start_time if has_time and cfg.time_filter_enabled else None
    if trade_time_filter:
        print(f"⏳ Применён фильтр по времени: {trade_time_filter}")
    else:
        print("📅 Данные дневные — фильтр по времени отключён")

    # === ТЕСТ РЫНОЧНОГО ФИЛЬТРА С РАЗНЫМИ ОКНАМИ ===
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
        status = "✅ СРАБОТАЛ" if filter_result['triggered'] else "❌ НЕ СРАБОТАЛ"
        used_win = filter_result.get('used_vol_window', 'N/A')
        print(f"  market_vol_window={window:3d} → {status} | использовано окно={used_win:3d} | волатильность={filter_result['market_vol']:.2%} если доступна")

    # === ЗАПУСК БЭКТЕСТА ===
    print("\n▶ Запуск бэктеста с production-параметрами...")
    strategy = DualMomentumStrategy(**cfg.production_params, debug=False)
    bt = Backtester(
        commission=cfg.commission,
        default_commission=cfg.default_commission,
        slippage=cfg.slippage,
        use_slippage=cfg.use_slippage,
        trade_time_filter=trade_time_filter
    )

    try:
        result = bt.run(
            strategy,
            data,
            market_data=market_df,
            rvi_data=rvi_data,
            initial_capital=cfg.initial_capital
        )
        print("\n✅ Бэктест завершён:")
        print(f"Финальная стоимость: {result['final_value']:,.2f}")
        print(f"CAGR: {result['cagr']:.2%}")
        print(f"Sharpe: {result['sharpe']:.2f}")
        print(f"Max DD: {result['max_drawdown']:.2%}")
        
        # 🔑 ДИАГНОСТИКА: Анализ использования рыночного фильтра
        if 'market_filter_stats' in result:
            stats = result['market_filter_stats']
            total_days = stats.get('total_days', 0)
            rvi_triggered = stats.get('rvi_triggered', 0)
            vol_triggered = stats.get('vol_triggered', 0)
            print(f"\n📊 Статистика рыночного фильтра:")
            print(f"  Всего торговых дней: {total_days}")
            print(f"  Срабатываний по RVI: {rvi_triggered} ({rvi_triggered/total_days:.1%})")
            print(f"  Срабатываний по волатильности: {vol_triggered} ({vol_triggered/total_days:.1%})")
            print(f"  Общая защита капитала: {(rvi_triggered + vol_triggered)/total_days:.1%}")

    except Exception as e:
        print(f"❌ Ошибка при бэктесте: {e}")
        import traceback
        traceback.print_exc()
        return

    # === ЗАПУСК ОПТИМИЗАЦИИ ===
    print("\n🔍 Запуск полной оптимизации...")
    keys = list(cfg.param_grid.keys())
    values = list(cfg.param_grid.values())
    total = len(list(product(*values)))
    print(f"⚙️  Всего комбинаций: {total}")

    # ... остальной код оптимизации без изменений ...


if __name__ == "__main__":
    main()
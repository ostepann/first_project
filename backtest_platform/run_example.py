# backtest_platform/run_example.py
"""
Основной скрипт для запуска бэктеста с production-параметрами и полной оптимизацией.
Версия: 2.0.0
Изменения:
- Полная интеграция с новой структурой optimization_config.py (v2.5.0).
- Поддержка всех новых параметров стратегии.
"""

import os
import sys
import pandas as pd
from itertools import product

# Метаданные модуля
__version__ = "2.0.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-01"

# Настройка пути к корню проекта
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy
from utils import load_market_data
import optimization_config as cfg


def main():
    # Загрузка конфигурации
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
######################################################################

    # === ДИАГНОСТИКА ВОЛАТИЛЬНОСТИ ===
    from backtest_platform.indicators.volatility import rolling_volatility
    market_returns = market_df['CLOSE'].pct_change().dropna()
    vol_series = rolling_volatility(market_returns, cfg.production_params['market_vol_window'])

    print(f"\n🔍 ДИАГНОСТИКА ВОЛАТИЛЬНОСТИ РЫНКА ({cfg.market_ticker}):")
    print(f"  Окно расчёта: {cfg.production_params['market_vol_window']} дней")
    print(f"  Мин. волатильность: {vol_series.min():.4f} ({vol_series.min():.2%})")
    print(f"  Макс. волатильность: {vol_series.max():.4f} ({vol_series.max():.2%})")
    print(f"  Средняя волатильность: {vol_series.mean():.4f} ({vol_series.mean():.2%})")

    # Найдём день с максимальной волатильностью
    max_vol_date = vol_series.idxmax()
    max_vol_value = vol_series.max()
    print(f"  Дата макс. волатильности: {max_vol_date.date()}")
    print(f"  Значение: {max_vol_value:.4f} ({max_vol_value:.2%})")

######################################################################

    # === ФИЛЬТР ПО ВРЕМЕНИ ===
    has_time = data[cfg.tickers[0]]['TRADEDATE'].iloc[0].time() != pd.Timestamp('00:00:00').time()
    trade_time_filter = cfg.trading_start_time if has_time and cfg.time_filter_enabled else None
    if trade_time_filter:
        print(f"⏳ Применён фильтр по времени: {trade_time_filter}")
    else:
        print("📅 Данные дневные — фильтр по времени отключён")

######################################################################
    # === ДИАГНОСТИКА: ВРЕМЕННЫЙ СЛОВАРЬ ПАРАМЕТРОВ ===
    # debug_params = {
    #      'base_lookback': 20,
    #      'risk_free_ticker': 'LQDT',
    #      'bare_mode': True,
    # }

    # debug_params = cfg.production_params.copy()
    # debug_params.update({
    #     'rvi_high_exit_threshold': 100, # ← Невозможно достичь
    #     'market_vol_threshold': 1.0,     # ← Очень высокий порог
    # })    
  
    debug_params = cfg.production_params.copy()
    debug_params.update({
        'rvi_high_exit_threshold': 35, # ← Невозможно достичь
        'market_vol_threshold': 0.35,     # ← Очень высокий порог
    })    
######################################################################    
       
    # === ЗАПУСК БЭКТЕСТА С РЕКОМЕНДОВАННЫМИ ПАРАМЕТРАМИ ===
    print("\n▶ Запуск бэктеста с production-параметрами...")
    strategy = DualMomentumStrategy(**debug_params)
 #   strategy = DualMomentumStrategy(**cfg.production_params)
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

    except Exception as e:
        print(f"❌ Ошибка при бэктесте: {e}")
        return

    # === ЗАПУСК ОПТИМИЗАЦИИ ===
    print("\n🔍 Запуск полной оптимизации...")
    keys = list(cfg.param_grid.keys())
    values = list(cfg.param_grid.values())
    total = len(list(product(*values)))
    print(f"⚙️  Всего комбинаций: {total}")

    results = []
    for i, combo in enumerate(product(*values), 1):
        params = dict(zip(keys, combo))
        print(f"\n[{i}/{total}] Тестирую: {params}")
        try:
            strategy = DualMomentumStrategy(**params)
            bt = Backtester(
                commission=cfg.commission,
                default_commission=cfg.default_commission,
                slippage=cfg.slippage,
                use_slippage=cfg.use_slippage,
                trade_time_filter=trade_time_filter
            )
            res = bt.run(
                strategy,
                data,
                market_data=market_df,
                rvi_data=rvi_data,
                initial_capital=cfg.initial_capital
            )
            results.append({
                **params,
                'sharpe': res['sharpe'],
                'cagr': res['cagr'],
                'max_drawdown': res['max_drawdown'],
                'final_value': res['final_value']
            })
            print(f"  → Sharpe: {res['sharpe']:.3f}, CAGR: {res['cagr']:.2%}")
        except Exception as e:
            print(f"  → ❌ Пропущено: {str(e)[:50]}...")

    if not results:
        print("❌ Ни одна комбинация не завершилась успешно.")
        return

    opt_results = pd.DataFrame(results).sort_values('sharpe', ascending=False)
    print(f"\n🏆 Топ-5 комбинаций:")
    top5 = opt_results.head(5)
    print(top5[[
        'base_lookback', 'base_vol_window', 'max_vol_threshold', 
        'sharpe', 'cagr', 'max_drawdown'
    ]].to_string(index=False))

    top5.to_csv("optimization_results.csv", index=False)
    print("\n✅ Результаты сохранены в optimization_results.csv")

if __name__ == "__main__":
    main()
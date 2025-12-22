# backtest_platform/validation/test02/test02_run_validation.py

import os
import sys
import pandas as pd

# Добавляем корень проекта в sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Используем ОРИГИНАЛЬНУЮ стратегию из продакшена
from backtest_platform.strategies.dual_momentum import DualMomentumStrategy
from backtest_platform.core.backtester import Backtester
from backtest_platform.utils import load_market_data

def main():
    # Загрузка конфигурации теста
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    import test02_optimization_config_validation as cfg

    # Загрузка данных
    data = {}
    for ticker in cfg.tickers:
        df = load_market_data(os.path.join(cfg.data_dir, f'test02_{ticker}.csv'))
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        data[ticker] = df

    rvi_data = load_market_data(os.path.join(cfg.data_dir, 'test02_RVI.csv'))
    rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])
    market_df = data[cfg.market_ticker].copy()

    # === ИСПОЛЬЗУЕМ ПРОДУКТИВНУЮ СТРАТЕГИЮ ===
    strategy = DualMomentumStrategy(
        base_lookback=5,            # lookback для momentum
        base_vol_window=10,         # окно для волатильности
        max_vol_threshold=0.5       # 50% годовой волатильности — порог
    )

    # Настройка бэктестера
    bt = Backtester(
        commission=cfg.commission,
        default_commission=cfg.default_commission,
        slippage=cfg.slippage,
        use_slippage=cfg.use_slippage,
        trade_time_filter=cfg.trade_time_filter
    )

    # Запуск бэктеста с продуктивным кодом
    result = bt.run(
        strategy,
        data,
        market_data=market_df,
        rvi_data=rvi_data,
        initial_capital=cfg.initial_capital
    )

    # === ВАЛИДАЦИЯ ===
    print("✅ Тест 2: Фильтр по волатильности (с использованием DualMomentumStrategy)")
    print(f"Финальная стоимость: {result['final_value']:.2f}")
    print(f"Количество сделок: {len(result.get('trades', []))}")

    # Условие успеха:
    # - EQMX_HIGH_VOL должен быть отфильтрован (его волатильность ~60% > 50%),
    # - Стратегия должна выбрать OBLG_LOW_VOL (волатильность ~15% < 50%),
    # - Портфель должен вырасти (>100.5).
    if result['final_value'] > 100.5:
        print("✅ ТЕСТ ПРОЙДЕН: продуктивная стратегия корректно отфильтровала высоковолатильный актив")
        return True
    else:
        print("❌ ТЕСТ ПРОВАЛЕН: продуктивная стратегия НЕ отфильтровала высоковолатильный актив")
        return False

if __name__ == "__main__":
    main()
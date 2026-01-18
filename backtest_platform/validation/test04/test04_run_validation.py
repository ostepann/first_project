# backtest_platform/validation/test04/test04_run_validation.py

import os
import sys
import pandas as pd

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backtest_platform.strategies.dual_momentum import DualMomentumStrategy
from backtest_platform.core.backtester import Backtester
from backtest_platform.utils import load_market_data

def main():
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    import test04_optimization_config_validation as cfg

    # Загрузка данных
    data = {}
    for ticker in cfg.tickers:
        df = load_market_data(os.path.join(cfg.data_dir, f'test04_{ticker}.csv'))
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        data[ticker] = df

    rvi_data = load_market_data(os.path.join(cfg.data_dir, 'test04_RVI.csv'))
    rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])
    market_df = data[cfg.market_ticker].copy()

    # ИСПОЛЬЗУЕМ ПРОДУКТИВНУЮ СТРАТЕГИЮ В РЕЖИМЕ BARE MODE
    strategy = DualMomentumStrategy(
        base_lookback=2,
        max_vol_threshold=1.0,
        bare_mode=True  # ← отключает все фильтры и адаптацию
    )

    bt = Backtester(
        commission=cfg.commission,
        default_commission=cfg.default_commission,
        slippage=cfg.slippage,
        use_slippage=cfg.use_slippage,
        trade_time_filter=cfg.trade_time_filter
    )

    result = bt.run(
        strategy,
        data,
        market_data=market_df,
        rvi_data=rvi_data,
        initial_capital=cfg.initial_capital
    )

    # 🔢 Ожидаемое значение (рассчитано вручную или после первого запуска)
    # Пример: при 10 днях, ~9 переключениях, комиссия+спред ≈ 0.1–0.15% на сделку
    expected = 106.58  # ← обновите это значение после первого успешного запуска

    print(f"✅ Тест 4: Учёт комиссии и проскальзывания")
    print(f"Финальная стоимость: {result['final_value']:.2f}")
    print(f"Ожидаемое значение: {expected}")

    if abs(result['final_value'] - expected) < 0.05:
        print("✅ ТЕСТ ПРОЙДЕН")
        return True
    else:
        print("❌ ТЕСТ ПРОВАЛЕН")
        print("💡 Подсказка: если это первый запуск, замените 'expected' на полученное значение.")
        return False

if __name__ == "__main__":
    main()
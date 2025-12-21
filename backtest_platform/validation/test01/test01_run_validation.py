# backtest_platform/validation/test01/test01_run_validation.py

import os
import sys
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backtest_platform.validation.test01.test01_validation_strategy import Test01ValidationStrategy
from core.backtester import Backtester
from utils import load_market_data
import pandas as pd

def main():
    # Загрузка конфигурации
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    import test01_optimization_config_validation as cfg

    # Загрузка данных
    data = {}
    for ticker in cfg.tickers:
        df = load_market_data(os.path.join(cfg.data_dir, f'test01_{ticker}.csv'))
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        data[ticker] = df

    rvi_data = load_market_data(os.path.join(cfg.data_dir, 'test01_RVI.csv'))
    rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])
    market_df = data[cfg.market_ticker].copy()

    # Стратегия
    strategy = Test01ValidationStrategy(
        lookback_period=2,
        risk_free_ticker='LQDT'
    )

    # Бэктест
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

    # Проверка
    expected = 109.37  # 100 * 1.01^9 (покупка на день 2, удержание 9 дней)
    print(f"✅ Тест 1: Выбор самого прибыльного актива")
    print(f"Финальная стоимость: {result['final_value']:.2f}")
    print(f"Ожидаемое значение: {expected}")

    if abs(result['final_value'] - expected) < 0.05:
        print("✅ ТЕСТ ПРОЙДЕН")
        return True
    else:
        print("❌ ТЕСТ ПРОВАЛЕН")
        return False

if __name__ == "__main__":
    main()
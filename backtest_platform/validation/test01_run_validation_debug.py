# backtest_platform/validation/run_validation.py

import os
import sys

# Настройка пути к корню проекта
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Импорт валидационной стратегии (БЕЗ адаптации и волатильности)
from backtest_platform.validation.validation_strategy import ValidationDualMomentumStrategy
from core.backtester import Backtester
from utils import load_market_data
import pandas as pd

def main():
    # Загрузка конфигурации
    _config_path = os.path.dirname(os.path.abspath(__file__))
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    import optimization_config_validation as cfg

    print("🔍 Загрузка данных...")
    data = {}
    for ticker in cfg.tickers:
        df = load_market_data(os.path.join(cfg.data_dir, f'{ticker}.csv'))
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        data[ticker] = df
        print(f"  {ticker}: {len(df)} строк, CLOSE от {df['CLOSE'].iloc[0]:.2f} до {df['CLOSE'].iloc[-1]:.2f}")

    rvi_data = load_market_data(os.path.join(cfg.data_dir, 'RVI.csv'))
    rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])
    print(f"  RVI: {rvi_data['CLOSE'].iloc[0]:.1f} → {rvi_data['CLOSE'].iloc[-1]:.1f}")

    market_df = data[cfg.market_ticker].copy()

    # === СОЗДАНИЕ СТРАТЕГИИ БЕЗ ВОЛАТИЛЬНОСТИ ===
    strategy = ValidationDualMomentumStrategy(
        lookback_period=2,          # только этот параметр нужен
        risk_free_ticker='LQDT'
        # vol_window и max_vol_threshold УДАЛЕНЫ
    )

    # === ТЕСТ СИГНАЛА НА 2-Й ДЕНЬ ===
    print("\n🧪 Тест сигнала на 2-й день...")
    second_date = data['EQMX']['TRADEDATE'].iloc[1]
    test_data_early = {}
    for ticker, df in data.items():
        test_data_early[ticker] = df[df['TRADEDATE'] <= second_date].copy()
    
    signal_early = strategy.generate_signal(test_data_early)
    print(f"  Сигнал на {second_date.date()}: {signal_early}")

    # === ЗАПУСК БЭКТЕСТА ===
    print("\n▶ Запуск бэктеста...")
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

    print(f"\n✅ ВАЛИДАЦИЯ ЗАВЕРШЕНА")
    expected = 109.37  # 100 * (1.01)^10
    print(f"Финальная стоимость: {result['final_value']:.2f}")
    print(f"Ожидаемое значение: {expected}")
    
    if abs(result['final_value'] - expected) < 0.05:
        print("✅ ТЕСТ ПРОЙДЕН")
    else:
        print("❌ ТЕСТ ПРОВАЛЕН")
    
    print(f"CAGR: {result['cagr']:.2%}")

if __name__ == "__main__":
    main()
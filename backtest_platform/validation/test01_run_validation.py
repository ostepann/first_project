# backtest_platform/validation/run_validation.py

# === ФИКС ПУТИ: гарантируем, что пакет backtest_platform доступен ===
import os
import sys

# Получаем путь к корню пакета backtest_platform
_backtest_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Добавляем корень пакета в sys.path (если ещё не добавлен)
if _backtest_root not in sys.path:
    sys.path.insert(0, _backtest_root)

# Теперь импорты будут работать
from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy
from utils import load_market_data

import pandas as pd

def main():
    # Импорт конфигурации из той же папки
    _config_path = os.path.dirname(os.path.abspath(__file__))
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    import optimization_config_validation as cfg

    data = {}
    for ticker in cfg.tickers:
        df = load_market_data(os.path.join(cfg.data_dir, f'{ticker}.csv'))
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        data[ticker] = df

    rvi_data = load_market_data(os.path.join(cfg.data_dir, 'RVI.csv'))
    rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])

    market_df = data[cfg.market_ticker].copy()

    strategy = DualMomentumStrategy(**cfg.production_params)
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

    print("\n✅ ВАЛИДАЦИЯ ЗАВЕРШЕНА")
    print(f"Финальная стоимость: {result['final_value']:.2f}")
    print(f"Ожидаемое значение: 109.37")
    
    if abs(result['final_value'] - 109.37) < 0.05:
        print("✅ ТЕСТ ПРОЙДЕН")
    else:
        print("❌ ТЕСТ ПРОВАЛЕН")
    
    print(f"CAGR: {result['cagr']:.2%}")

if __name__ == "__main__":
    main()
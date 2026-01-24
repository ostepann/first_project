# backtest_platform/validation/test05/test05_run_validation.py

import pandas as pd
import os
import sys

def main():
    # === Добавляем корень проекта в sys.path ===
    project_root = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(__file__)
            )
        )
    )
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # === Импорты ===
    from backtest_platform.validation.test05.test05_optimization_config_validation import (
        tickers, data_dir, strategy_params, commission, default_commission, slippage, use_slippage, trade_time_filter
    )
    from backtest_platform.core.backtester import Backtester
    from backtest_platform.strategies.dual_momentum import DualMomentumStrategy  # ✅ Верный путь!

    # === Загрузка данных ===
    data_root = os.path.join(project_root, data_dir)

    data_dict = {}
    for ticker in tickers:
        df = pd.read_csv(os.path.join(data_root, f'test05_{ticker}.csv'), parse_dates=['TRADEDATE'])
        data_dict[ticker] = df

    market_data = pd.read_csv(os.path.join(data_root, 'test05_MOEX.csv'), parse_dates=['TRADEDATE'])
    rvi_data = pd.read_csv(os.path.join(data_root, 'test05_RVI.csv'), parse_dates=['TRADEDATE'])

    # === Настройка стратегии ===
    strategy = DualMomentumStrategy(**strategy_params)

    # === Настройка бэктестера ===
    backtester = Backtester(
        commission=commission,
        default_commission=default_commission,
        slippage=slippage,
        use_slippage=use_slippage,
        trade_time_filter=trade_time_filter
    )

    # === Запуск ===
    results = backtester.run(
        strategy=strategy,
        data_dict=data_dict,
        market_data=market_data,
        rvi_data=rvi_data,
        initial_capital=100_000,
        price_col='CLOSE'
    )

    # === Анализ последнего решения ===
    trades_df = results['trades']
    if not trades_df.empty:
        last_trade = trades_df.iloc[-1]
        selected_asset = last_trade['ticker']
        last_date = last_trade['date']
    else:
        # Если нет сделок — остаёмся в LQDT (стартовый актив)
        selected_asset = 'LQDT'
        last_date = data_dict['LQDT']['TRADEDATE'].iloc[-1]

    # === Отладочный вывод ===
    print(f"📅 Последняя дата: {last_date}")
    print(f"📈 Выбранный актив: {selected_asset}")

    # Проверка EQMX momentum
    eqmx_prices = data_dict['EQMX']['CLOSE']
    eqmx_mom = eqmx_prices.pct_change().iloc[-1] > 0
    print(f"📊 EQMX momentum: {'положительный' if eqmx_mom else 'не положительный'}")

    # RVI на последнюю дату
    rvi_last = rvi_data[rvi_data['TRADEDATE'] == last_date]
    rvi_val = rvi_last['CLOSE'].iloc[0] if not rvi_last.empty else None
    print(f"🌀 RVI: {rvi_val:.1f}" if rvi_val is not None else "🌀 RVI: N/A")

    # Волатильность рынка
    market_prices = market_data['CLOSE']
    returns = market_prices.pct_change().dropna()
    vol_ann = returns.std() * (252 ** 0.5)
    print(f"📊 Волатильность рынка (annualized): {vol_ann:.2%}")

    # === Валидация ===
    assert selected_asset == 'LQDT', (
        f"❌ ТЕСТ 5 ПРОВАЛЕН: ожидался 'LQDT', получен '{selected_asset}'. "
        "Рыночный фильтр не сработал при высокой волатильности!"
    )
    print("✅ ТЕСТ 5 ПРОЙДЕН: рыночный фильтр корректно принудил выход в кэш.")

if __name__ == "__main__":
    main()
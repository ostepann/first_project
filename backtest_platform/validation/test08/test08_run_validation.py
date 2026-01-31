# backtest_platform/validation/test08/test08_run_validation.py

"""
Тест 8: Валидация метрик бэктеста (CAGR, Sharpe, MaxDD)

КЛЮЧЕВАЯ ПРОБЛЕМА И ЕЁ РЕШЕНИЕ:
------------------------------
Проблема: При 4 днях данных и base_lookback=2 покупка происходила на День 2 по цене 101.0,
          а не по ожидаемой 100.0 → искажение кривой капитала.

Решение: Используем 5 торговых дней с прогревочным периодом:
         • Дни 1-2: цена 100.0 → на День 2 достаточно данных для расчёта моментума
         • День 2: моментум = 0% → стратегия выбирает EQMX и покупает по 100.0
         • Дни 3-5: рост цен → формирование корректной кривой капитала

ВАЖНО: В бэктестере сигнал генерируется ДО покупки на основе данных ДО текущей даты.
       Поэтому для покупки по цене P_t требуется, чтобы на дату t были доступны
       данные за предыдущие (lookback) дней.
"""

import pandas as pd
import numpy as np
import os
import sys

def calculate_expected_metrics():
    """
    Независимый расчёт ожидаемых метрик для кривой капитала:
        [100_000, 100_000, 101_000, 101_500, 102_500]
    
    Формулы ИДЕНТИЧНЫ реализации в backtest_platform/core/backtester.py:
      • CAGR: (final/initial)^(252/days) - 1
      • Sharpe: (mean(returns)*252) / (std(returns, ddof=1)*sqrt(252))
      • MaxDD: min(value / cummax(value) - 1)
    
    ddof=1 критически важен — именно так считает pandas.DataFrame.std()
    """
    # Кривая капитала после исправления логики данных (5 дней)
    capital = np.array([100_000, 100_000, 101_000, 101_500, 102_500])
    
    # Дневные доходности (pct_change эквивалент)
    returns = np.diff(capital) / capital[:-1]
    
    # CAGR с годовизацией через 252 торговых дня
    cagr = (capital[-1] / capital[0]) ** (252 / len(capital)) - 1
    
    # Sharpe с выборочным стандартным отклонением (ddof=1 как в pandas)
    mean_ret = returns.mean()
    std_ret = returns.std(ddof=1)
    sharpe = (mean_ret * 252) / (std_ret * np.sqrt(252)) if std_ret > 0 else 0.0
    
    # Max Drawdown через накопительный максимум
    running_max = np.maximum.accumulate(capital)
    drawdown = (capital / running_max - 1).min()
    
    return {
        'cagr': cagr,
        'sharpe': sharpe,
        'max_drawdown': drawdown,
        'returns': returns.tolist(),
        'capital_curve': capital.tolist()
    }

def main():
    # === НАСТРОЙКА ПУТЕЙ ===
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    
    import test08_optimization_config_validation as cfg

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from backtest_platform.core.backtester import Backtester
    from backtest_platform.strategies.dual_momentum import DualMomentumStrategy

    # === ЗАГРУЗКА ДАННЫХ ===
    data_dir_abs = os.path.join(project_root, cfg.data_dir)
    asset_data = {}
    for asset in cfg.assets:
        path = os.path.join(data_dir_abs, f"{asset}.csv")
        df = pd.read_csv(path, parse_dates=['TRADEDATE'])
        asset_data[asset] = df

    # === НАСТРОЙКА БЭКТЕСТЕРА ===
    # Отключаем комиссии и проскальзывание для чистоты проверки метрик
    strategy = DualMomentumStrategy(**cfg.strategy_params)
    bt = Backtester(
        commission=0.0,
        default_commission=0.0,
        slippage=0.0,
        use_slippage=False,
        trade_time_filter=None
    )

    # === ЗАПУСК БЭКТЕСТА ===
    result = bt.run(
        strategy,
        asset_data,
        market_data=None,
        rvi_data=None,
        initial_capital=100_000,
        price_col='CLOSE'
    )

    # Извлечение фактических результатов
    actual_cagr = result['cagr']
    actual_sharpe = result['sharpe']
    actual_maxdd = result['max_drawdown']
    portfolio_value = result['portfolio_value']['value'].values

    # === НЕЗАВИСИМЫЙ РАСЧЁТ ОЖИДАЕМЫХ МЕТРИК ===
    expected = calculate_expected_metrics()
    expected_cagr = expected['cagr']
    expected_sharpe = expected['sharpe']
    expected_maxdd = expected['max_drawdown']

    # === ВЫВОД РЕЗУЛЬТАТОВ ===
    print("\n" + "="*70)
    print("📊 ТЕСТ 8: ВАЛИДАЦИЯ МЕТРИК БЭКТЕСТА (CAGR, Sharpe, MaxDD)")
    print("="*70)
    
    print("\n📈 Фактическая кривая капитала:")
    for i, value in enumerate(portfolio_value):
        print(f"   День {i+1}: {value:,.2f} руб.")
    
    print(f"\n📉 Дневные доходности (фактические):")
    for i, ret in enumerate(np.diff(portfolio_value) / portfolio_value[:-1]):
        print(f"   День {i+1}→{i+2}: {ret:.4%}")
    
    print(f"\n🎯 ОЖИДАЕМЫЕ МЕТРИКИ (независимый расчёт для кривой {expected['capital_curve']}):")
    print(f"   CAGR:      {expected_cagr:.6f} ({expected_cagr*100:.3f}%)")
    print(f"   Sharpe:    {expected_sharpe:.6f}")
    print(f"   MaxDD:     {expected_maxdd:.6%}")
    
    print(f"\n🔍 ФАКТИЧЕСКИЕ МЕТРИКИ (бэктестер):")
    print(f"   CAGR:      {actual_cagr:.6f} ({actual_cagr*100:.3f}%)")
    print(f"   Sharpe:    {actual_sharpe:.6f}")
    print(f"   MaxDD:     {actual_maxdd:.6%}")

    # === ВАЛИДАЦИЯ ===
    errors = []
    
    # Проверка CAGR
    cagr_error = abs(actual_cagr - expected_cagr) / abs(expected_cagr)
    if cagr_error > cfg.tolerance:
        errors.append(
            f"CAGR: относительная погрешность {cagr_error:.4%} > допуска {cfg.tolerance:.2%}\n"
            f"      ожидается {expected_cagr:.6f}, получено {actual_cagr:.6f}"
        )
    
    # Проверка Sharpe
    sharpe_error = abs(actual_sharpe - expected_sharpe) / abs(expected_sharpe)
    if sharpe_error > cfg.tolerance:
        errors.append(
            f"Sharpe: относительная погрешность {sharpe_error:.4%} > допуска {cfg.tolerance:.2%}\n"
            f"        ожидается {expected_sharpe:.6f}, получено {actual_sharpe:.6f}"
        )
    
    # Проверка MaxDD
    if abs(actual_maxdd - expected_maxdd) > cfg.maxdd_tolerance:
        errors.append(
            f"MaxDD: абсолютная погрешность {abs(actual_maxdd - expected_maxdd):.8f} > допуска {cfg.maxdd_tolerance}\n"
            f"       ожидается {expected_maxdd:.8f}, получено {actual_maxdd:.8f}"
        )

    # === ИТОГОВЫЙ ВЕРДИКТ ===
    if errors:
        print("\n" + "❌"*35)
        print("ОШИБКИ ВАЛИДАЦИИ:")
        print("❌"*35)
        for i, err in enumerate(errors, 1):
            print(f"\n{i}. {err}")
        print("\n💡 РЕКОМЕНДАЦИЯ: Проверьте логику расчёта метрик в backtest_platform/core/backtester.py")
        print("   Убедитесь, что используются те же формулы и параметры (252 дня, ddof=1).")
        print("\n" + "="*70)
        raise AssertionError("Тест 8 НЕ ПРОЙДЕН")
    else:
        print("\n" + "✅"*35)
        print("ТЕСТ 8 ПРОЙДЕН УСПЕШНО!")
        print("✅"*35)
        print("\nВсе метрики рассчитаны корректно с учётом логики бэктестера:")
        print("  • CAGR — годовая доходность с учётом сложного процента")
        print("  • Sharpe Ratio — отношение доходности к риску (с годовизацией)")
        print("  • Max Drawdown — максимальная просадка от исторического пика")
        print("\n" + "="*70)

if __name__ == '__main__':
    main()
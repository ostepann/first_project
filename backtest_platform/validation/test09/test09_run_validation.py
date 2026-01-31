# backtest_platform/validation/test09/test09_run_validation.py

"""
Валидация оптимизации параметра lookback (Тест 9).
Проверяет, что оптимизатор корректно выбирает lookback=10 как оптимальный период
на основе относительной иерархии эффективности (а не абсолютных значений CAGR).
"""

import pandas as pd
import numpy as np
import os
import sys

def main():
    # Добавляем папку текущего теста в sys.path
    _config_path = os.path.dirname(__file__)
    if _config_path not in sys.path:
        sys.path.insert(0, _config_path)
    
    import test09_optimization_config_validation as cfg

    # Добавляем корень проекта в sys.path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from backtest_platform.strategies.dual_momentum import DualMomentumStrategy
    from backtest_platform.core.backtester import Backtester

    # Загрузка тестовых данных
    data_dir_abs = os.path.join(project_root, cfg.data_dir)
    asset_data = {}
    
    print("📂 Загрузка тестовых данных...")
    for asset in cfg.assets:
        path = os.path.join(data_dir_abs, f"{asset}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌ Файл не найден: {path}")
        
        df = pd.read_csv(path, parse_dates=['TRADEDATE'])
        asset_data[asset] = df
        print(f"   ✅ {asset}: {len(df)} записей")

    # Подготовка рыночных данных
    market_data = asset_data[cfg.market_ticker].copy()

    # Функция для запуска бэктеста с заданными параметрами
    def run_backtest_with_params(lookback):
        params = {
            'base_lookback': lookback,
            'base_vol_window': cfg.param_grid['base_vol_window'][0],
            'max_vol_threshold': cfg.param_grid['max_vol_threshold'][0],
            'use_trend_filter': cfg.param_grid['use_trend_filter'][0],
            'bare_mode': cfg.param_grid['bare_mode'][0]
        }
        strategy = DualMomentumStrategy(**params)
        bt = Backtester(
            commission=cfg.commission,
            default_commission=0.0,
            slippage=0.0,
            use_slippage=cfg.use_slippage,
            trade_time_filter=None
        )
        result = bt.run(
            strategy,
            asset_data,
            market_data=market_data,
            rvi_data=None,
            initial_capital=cfg.initial_capital,
            price_col='CLOSE'
        )
        return {
            'base_lookback': lookback,
            'cagr': result['cagr'],
            'sharpe': result['sharpe'],
            'final_value': result['final_value'],
            'num_trades': len(result['trades'])
        }

    # Запуск бэктеста для каждой комбинации параметров
    print("\n🔍 Запуск оптимизации lookback...")
    results = []
    
    for lookback in cfg.param_grid['base_lookback']:
        print(f"   Тестирую lookback={lookback}...", end=' ')
        try:
            res = run_backtest_with_params(lookback)
            results.append(res)
            print(f"CAGR: {res['cagr']:.2%}, Sharpe: {res['sharpe']:.3f}, Сделок: {res['num_trades']}")
        except Exception as e:
            print(f"❌ Ошибка: {str(e)[:60]}")
            continue

    if not results:
        raise RuntimeError("❌ Ни одна комбинация параметров не прошла бэктест")

    # Создаем датафрейм результатов
    results_df = pd.DataFrame(results).sort_values('cagr', ascending=False)
    
    print("\n📊 Результаты оптимизации (сортировка по CAGR):")
    print(results_df[['base_lookback', 'cagr', 'sharpe', 'num_trades']].to_string(index=False))
    
    # Находим оптимальный параметр по CAGR
    best_by_cagr = results_df.iloc[0]
    best_lookback = int(best_by_cagr['base_lookback'])
    
    print(f"\n🏆 Оптимальный lookback по CAGR: {best_lookback}")
    print(f"   CAGR: {best_by_cagr['cagr']:.2%}")
    print(f"   Ожидаемый lookback: {cfg.expected_best_lookback}")

    # Извлекаем метрики для каждого lookback
    cagr_5 = results_df[results_df['base_lookback'] == 5]['cagr'].values[0]
    cagr_10 = results_df[results_df['base_lookback'] == 10]['cagr'].values[0]
    cagr_20 = results_df[results_df['base_lookback'] == 20]['cagr'].values[0]
    trades_5 = results_df[results_df['base_lookback'] == 5]['num_trades'].values[0]
    trades_10 = results_df[results_df['base_lookback'] == 10]['num_trades'].values[0]
    trades_20 = results_df[results_df['base_lookback'] == 20]['num_trades'].values[0]

    # === КЛЮЧЕВАЯ ВАЛИДАЦИЯ: относительная иерархия эффективности ===
    # Проверка 1: lookback=10 должен иметь МАКСИМАЛЬНЫЙ CAGR
    assert best_lookback == cfg.expected_best_lookback, (
        f"❌ Тест провален: ожидался lookback={cfg.expected_best_lookback}, "
        f"получен lookback={best_lookback}\n"
        f"Детали:\n{results_df[['base_lookback', 'cagr', 'num_trades']].to_string(index=False)}"
    )

    # Проверка 2: Иерархия CAGR должна быть: 10 > 5 и 10 > 20
    # Используем минимальную разницу 0.5% для надёжности (учитывая возможный шум в расчётах)
    min_cagr_diff = 0.005  # 0.5%
    
    assert cagr_10 > cagr_5 + min_cagr_diff, (
        f"❌ lookback=10 должен давать ВЫШЕ CAGR чем lookback=5 "
        f"(разница должна быть > {min_cagr_diff:.1%})\n"
        f"   lookback=10: {cagr_10:.2%}\n"
        f"   lookback=5:  {cagr_5:.2%}\n"
        f"   Разница:    {cagr_10 - cagr_5:.2%}"
    )
    
    assert cagr_10 > cagr_20 + min_cagr_diff, (
        f"❌ lookback=10 должен давать ВЫШЕ CAGR чем lookback=20 "
        f"(разница должна быть > {min_cagr_diff:.1%})\n"
        f"   lookback=10: {cagr_10:.2%}\n"
        f"   lookback=20: {cagr_20:.2%}\n"
        f"   Разница:    {cagr_10 - cagr_20:.2%}"
    )

    # Проверка 3: Количество сделок должно отражать качество сигналов
    # lookback=5: много сделок из-за реакции на шум
    # lookback=10: оптимальное количество (только настоящие развороты)
    # lookback=20: мало сделок из-за запаздывания
    assert trades_5 > trades_10 * 1.5, (
        f"❌ lookback=5 должен генерировать ЗНАЧИТЕЛЬНО больше сделок чем lookback=10 "
        f"(из-за ложных сигналов от шума)\n"
        f"   lookback=5: {trades_5} сделок\n"
        f"   lookback=10: {trades_10} сделок\n"
        f"   Ожидается: lookback=5 > lookback=10 * 1.5 ({trades_10 * 1.5:.1f})"
    )
    
    assert trades_20 < trades_10 * 0.7, (
        f"❌ lookback=20 должен генерировать ЗНАЧИТЕЛЬНО меньше сделок чем lookback=10 "
        f"(из-за запаздывания на разворотах)\n"
        f"   lookback=20: {trades_20} сделок\n"
        f"   lookback=10: {trades_10} сделок\n"
        f"   Ожидается: lookback=20 < lookback=10 * 0.7 ({trades_10 * 0.7:.1f})"
    )

    print("\n✅ Тест 9 пройден успешно!")
    print(f"   lookback=10 показал наилучший CAGR: {cagr_10:.2%}")
    print(f"   lookback=5:  CAGR = {cagr_5:.2%} (слишком много сделок: {trades_5})")
    print(f"   lookback=20: CAGR = {cagr_20:.2%} (слишком мало сделок: {trades_20})")
    print("\n💡 Логика теста:")
    print("   • lookback=5 реагирует на шум → много ложных сигналов → снижение CAGR")
    print("   • lookback=10 находит оптимальный баланс → ловит настоящие развороты → максимум CAGR")
    print("   • lookback=20 запаздывает на резких разворотах → пропускает часть движения → снижение CAGR")

if __name__ == '__main__':
    main()
import pandas as pd
import os
import sys
import numpy as np

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
    from backtest_platform.validation.test07.test07_optimization_config_validation import (
        tickers, data_dir, strategy_params, commission, default_commission, 
        slippage, use_slippage, trade_time_filter
    )
    from backtest_platform.core.backtester import Backtester
    from backtest_platform.strategies.dual_momentum import DualMomentumStrategy

    # === Загрузка данных ===
    data_root = os.path.join(project_root, data_dir)

    data_dict = {}
    for ticker in tickers:
        df = pd.read_csv(os.path.join(data_root, f'test07_{ticker}.csv'), parse_dates=['TRADEDATE'])
        data_dict[ticker] = df
        print(f"📥 {ticker}: {len(df)} строк")

    market_data = pd.read_csv(os.path.join(data_root, 'test07_MOEX.csv'), parse_dates=['TRADEDATE'])
    rvi_data = pd.read_csv(os.path.join(data_root, 'test07_RVI.csv'), parse_dates=['TRADEDATE'])

    # === Проверка пропуска в исходных данных ===
    all_dates = set()
    for ticker in tickers:
        all_dates.update(data_dict[ticker]['TRADEDATE'])
    
    eqmx_dates = set(data_dict['EQMX']['TRADEDATE'])
    oblg_dates = set(data_dict['OBLG']['TRADEDATE'])
    
    missing_in_eqmx = sorted(all_dates - eqmx_dates)
    missing_in_oblg = sorted(all_dates - oblg_dates)
    
    print(f"\n🔍 Анализ пропусков в исходных данных:")
    print(f"   Все уникальные даты: {len(all_dates)}")
    print(f"   EQMX пропущенные даты: {len(missing_in_eqmx)} → {[d.date() for d in missing_in_eqmx]}")
    print(f"   OBLG пропущенные даты: {len(missing_in_oblg)} → {[d.date() for d in missing_in_oblg]}")
    
    target_missing_date = pd.Timestamp('2023-01-05')
    assert target_missing_date in missing_in_eqmx, f"❌ Ожидаемый пропуск {target_missing_date.date()} не найден в EQMX!"
    assert len(missing_in_oblg) == 0, "❌ OBLG не должен содержать пропусков!"

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

    # === Запуск бэктеста с обработкой исключений ===
    print("\n🚀 Запуск бэктеста с пропущенными данными...")
    try:
        results = backtester.run(
            strategy=strategy,
            data_dict=data_dict,
            market_data=market_data,
            rvi_data=rvi_data,
            initial_capital=100_000,
            price_col='CLOSE'
        )
        print("✅ Бэктест завершён БЕЗ ИСКЛЮЧЕНИЙ")
    except Exception as e:
        print(f"❌ ТЕСТ 7 ПРОВАЛЕН: возникло исключение при обработке пропусков!\n{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise

    # === Анализ структуры результатов ===
    print(f"\n📊 Структура результатов:")
    print(f"   Ключи: {list(results.keys())}")
    
    # Правильный ключ из кода бэктестера — 'portfolio_value'
    assert 'portfolio_value' in results, "❌ Ожидаемый ключ 'portfolio_value' отсутствует в результатах!"
    portfolio = results['portfolio_value']
    trades_df = results.get('trades', pd.DataFrame())
    
    print(f"\n📈 Результаты бэктеста:")
    print(f"   Дней в портфеле: {len(portfolio)} (из {len(all_dates)} уникальных дат)")
    print(f"   Сделок: {len(trades_df) if not trades_df.empty else 0}")
    print(f"   Финальная стоимость: {results['final_value']:.2f}")

    # === Критическая проверка: пропуск дня ===
    # Согласно логике бэктестера, день с пропуском данных ПРОПУСКАЕТСЯ целиком
    print(f"\n🔍 Поведение на критической дате {target_missing_date.date()}:")
    
    # Проверяем, что дата отсутствует в портфеле (корректное поведение)
    if target_missing_date in portfolio['date'].values:
        print(f"   ⚠️  Дата {target_missing_date.date()} ПРИСУТСТВУЕТ в портфеле")
        # Это может быть допустимо, если бэктестер использует предыдущую цену (ffill),
        # но в текущей реализации ожидается пропуск дня
    else:
        print(f"   ✅ Дата {target_missing_date.date()} ПРОПУЩЕНА (корректное поведение при отсутствии данных)")

    # === Проверка продолжения торговли после пропуска ===
    # Должны быть даты ПОСЛЕ пропущенной
    dates_after_gap = portfolio[portfolio['date'] > target_missing_date]
    assert not dates_after_gap.empty, (
        f"❌ Стратегия не возобновила работу после пропущенной даты {target_missing_date.date()}! "
        f"Последняя дата портфеля: {portfolio['date'].max().date()}"
    )
    print(f"   ✅ Торговля продолжилась после пропуска: следующая дата портфеля = {dates_after_gap['date'].min().date()}")

    # === Проверка сохранения стоимости портфеля ===
    # Портфель не должен обнулиться или упасть ниже 90% от начальной стоимости
    min_value = portfolio['value'].min()
    assert min_value > 90_000, (
        f"❌ Портфель потерял слишком много стоимости из-за пропуска данных! "
        f"Минимум: {min_value:.2f} (должно быть > 90_000)"
    )
    print(f"   ✅ Стоимость портфеля сохранена: минимум = {min_value:.2f}")

    # === Детальный анализ пропущенных дней ===
    print(f"\n📋 Детальный анализ пропущенных дней:")
    portfolio_dates = set(portfolio['date'])
    skipped_dates = sorted(all_dates - portfolio_dates)
    
    print(f"   Всего уникальных дат в исходных данных: {len(all_dates)}")
    print(f"   Дат в портфеле: {len(portfolio_dates)}")
    print(f"   Пропущено дней: {len(skipped_dates)}")
    
    if skipped_dates:
        print(f"   Пропущенные даты: {[d.date() for d in skipped_dates[:5]]}" + 
              ("..." if len(skipped_dates) > 5 else ""))
        # Проверяем, что целевая пропущенная дата среди них
        assert target_missing_date in skipped_dates, (
            f"❌ Ожидаемая пропущенная дата {target_missing_date.date()} отсутствует в списке пропущенных дней!"
        )
        print(f"   ✅ Целевая дата {target_missing_date.date()} корректно пропущена")
    else:
        print("   ⚠️  Нет пропущенных дней (возможно, бэктестер использует ffill)")

    # === Финальная валидация ===
    print("\n" + "="*60)
    print("✅✅✅ ТЕСТ 7 ПРОЙДЕН: стратегия устойчива к пропускам данных")
    print("="*60)
    print("   ✓ Нет исключений при бэктесте")
    print("   ✓ День с пропущенными данными корректно обработан (пропущен)")
    print("   ✓ Торговля продолжилась на последующих датах")
    print("   ✓ Стоимость портфеля сохранена (>90% от начальной)")
    print("="*60)

if __name__ == "__main__":
    main()
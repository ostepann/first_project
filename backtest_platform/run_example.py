# first_project\backtest_platform\run_example.py

"""
Основной скрипт для запуска бэктеста с production-параметрами.
Версия: 2.2.4 (прямой экспорт расширенного лога сделок из бэктестера)
КРИТИЧЕСКОЕ УЛУЧШЕНИЕ:
- Использует расширенные данные сделок напрямую из Backtester.run() версии 1.3.2+
- Каждая сделка содержит: количество бумаг, цену исполнения, остаток наличных, стоимость позиции и общую стоимость портфеля
- НЕ требует реконструкции состояния портфеля — все данные рассчитаны в реальном времени при бэктесте
"""

import os
import sys
import pandas as pd
from itertools import product
from datetime import datetime

__version__ = "2.2.4"
__author__ = "Oleg Dev"
__date__ = "2026-02-14"

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.backtester import Backtester
from strategies.dual_momentum import DualMomentumStrategy
from utils import load_market_data

# 🔑 ИМПОРТ ИЗ МОДУЛЬНОЙ СИСТЕМЫ КОНФИГУРАЦИИ
from config import (
    data_dir, tickers, market_ticker, rvi_ticker,
    commission, default_commission, slippage, use_slippage,
    trading_start_time, time_filter_enabled, initial_capital,
    production_params,
    param_grid,
    CRITICAL_WARNING_COMMON, CRITICAL_WARNING_PRODUCTION
)


def filter_strategy_params(params: dict) -> dict:
    """
    Фильтрация параметров перед передачей в конструктор DualMomentumStrategy.
    
    Удаляет параметры, которые используются ТОЛЬКО для анализа/отчётов,
    но не принимаются основным конструктором стратегии.
    
    Неподдерживаемые параметры:
      • trend_r_squared_threshold — используется только в функции detect_trend() 
        для отчётов и исследований, НЕ в основном цикле стратегии
      • version — метаданные конфигурации, не параметр стратегии
      • Любые другие служебные поля из production_metadata
    """
    unsupported_keys = [
        'trend_r_squared_threshold',  # Только для отчётов тренда
        'version',                    # Метаданные конфигурации
        'expected_metrics',           # Метаданные
        'critical_fixes',             # Метаданные
        'optimization_method',        # Метаданные
        'validation_folds',           # Метаданные
        'primary_metric',             # Метаданные
        'constraints'                 # Метаданные
    ]
    
    # Создаём копию и удаляем неподдерживаемые ключи
    filtered = {k: v for k, v in params.items() if k not in unsupported_keys}
    
    # Дополнительная проверка: удаляем все ключи, начинающиеся с '_'
    filtered = {k: v for k, v in filtered.items() if not k.startswith('_')}
    
    return filtered


def save_trades_to_csv(trades_df: pd.DataFrame, project_root: str, strategy_params: dict):
    """
    Сохраняет расширенный лог сделок в CSV файл с кодировкой UTF-8-SIG.
    
    DataFrame trades_df ДОЛЖЕН содержать колонки (предоставляются Backtester v1.3.2+):
    - date: дата сделки
    - action: тип сделки (BUY/SELL)
    - ticker: тикер актива
    - execution_price: цена исполнения со всеми издержками (комиссия + проскальзывание)
    - market_price: рыночная цена без издержек (для расчёта текущей стоимости позиции)
    - quantity: количество купленных/проданных бумаг (абсолютное значение)
    - quantity_signed: количество со знаком (+ покупка, - продажа)
    - cash_balance: остаток наличных ПОСЛЕ сделки (₽)
    - position_value: стоимость текущей позиции в бумагах ПОСЛЕ сделки (₽)
    - total_value: общая стоимость портфеля ПОСЛЕ сделки = cash_balance + position_value (₽)
    
    Аргументы:
        trades_df: DataFrame со сделками из результата бэктеста (расширенная структура)
        project_root: корень проекта для определения пути сохранения
        strategy_params: параметры стратегии для формирования имени файла
    
    Возвращает:
        Путь к сохранённому файлу или None при ошибке
    """
    if trades_df.empty:
        print("⚠️  Сделок не было совершено — экспорт пропущен")
        return None
    
    # Создаём директорию для сохранения результатов оптимизации
    output_dir = os.path.join(project_root, 'data-optimization')
    os.makedirs(output_dir, exist_ok=True)
    
    # Формируем уникальное имя файла с временной меткой и ключевыми параметрами
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_lookback = strategy_params.get('base_lookback', 'NA')
    market_vol_window = strategy_params.get('market_vol_window', 'NA')
    
    filename = f"trades_lookback{base_lookback}_mktvol{market_vol_window}_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)
    
    try:
        # Сохраняем с кодировкой UTF-8-SIG для корректной работы с кириллицей в Excel
        trades_df.to_csv(
            filepath,
            index=False,
            encoding='utf-8-sig',
            date_format='%Y-%m-%d',
            float_format='%.2f'  # Форматирование всех числовых значений с 2 знаками после запятой
        )
        
        # Сводная статистика для пользователя
        if not trades_df.empty:
            buy_trades = trades_df[trades_df['action'] == 'BUY']
            sell_trades = trades_df[trades_df['action'] == 'SELL']
            final_value = trades_df['total_value'].iloc[-1]
            
            print(f"✅ Сделки сохранены: {filepath}")
            print(f"   Всего записей: {len(trades_df)}")
            print(f"   Покупок: {len(buy_trades)} сделок")
            print(f"   Продаж: {len(sell_trades)} сделок")
            print(f"   Финальная стоимость портфеля: {final_value:,.2f} ₽")
            
            # Дополнительная диагностика при наличии данных
            if 'quantity' in trades_df.columns:
                total_shares_bought = buy_trades['quantity'].sum() if not buy_trades.empty else 0
                total_shares_sold = sell_trades['quantity'].sum() if not sell_trades.empty else 0
                print(f"   Всего куплено бумаг: {total_shares_bought:,.2f} шт.")
                print(f"   Всего продано бумаг: {total_shares_sold:,.2f} шт.")
        else:
            print(f"✅ Сделки сохранены: {filepath} (пустой файл)")
        
        return filepath
    except Exception as e:
        print(f"❌ Ошибка при сохранении сделок: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    # === КРИТИЧЕСКИЕ ПРЕДУПРЕЖДЕНИЯ ПРИ ЗАПУСКЕ ===
    print(f"\n⚠️  {CRITICAL_WARNING_COMMON}")
    print(f"⚠️  {CRITICAL_WARNING_PRODUCTION}")
    
    # === ЗАГРУЗКА ДАННЫХ ===
    data_path = os.path.join(project_root, data_dir)
    data = {}
    print("\n📥 ЗАГРУЗКА ДАННЫХ ИЗ CSV...")
    for ticker in tickers:
        file_path = os.path.join(data_path, f'{ticker}.csv')
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ Файл не найден: {file_path}")
        df = load_market_data(file_path)
        if 'TRADEDATE' not in df.columns:
            raise ValueError(f"❌ В {ticker}.csv отсутствует колонка TRADEDATE")
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        data[ticker] = df
        print(f"✅ {ticker}: {df['TRADEDATE'].min().date()} → {df['TRADEDATE'].max().date()} ({len(df)} строк)")

    rvi_path = os.path.join(data_path, f'{rvi_ticker}.csv')
    rvi_data = None
    if os.path.exists(rvi_path):
        rvi_data = load_market_data(rvi_path)
        rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])
        print(f"✅ {rvi_ticker} загружен: {rvi_data['TRADEDATE'].min().date()} → {rvi_data['TRADEDATE'].max().date()}")
    else:
        print(f"⚠️ {rvi_ticker}.csv не найден — используется средний уровень волатильности")

    market_df = data[market_ticker].copy()

    # === ДИАГНОСТИКА ВОЛАТИЛЬНОСТИ ===
    from backtest_platform.indicators.volatility import rolling_volatility
    market_returns = market_df['CLOSE'].pct_change().dropna()
    vol_series = rolling_volatility(market_returns, production_params['market_vol_window'])

    print(f"\n🔍 ДИАГНОСТИКА ВОЛАТИЛЬНОСТИ РЫНКА ({market_ticker}):")
    print(f"  Окно расчёта: {production_params['market_vol_window']} дней")
    print(f"  Мин. волатильность: {vol_series.min():.4f} ({vol_series.min():.2%})")
    print(f"  Макс. волатильность: {vol_series.max():.4f} ({vol_series.max():.2%})")
    print(f"  Средняя волатильность: {vol_series.mean():.4f} ({vol_series.mean():.2%})")
    print(f"  Доступно данных для расчёта: {len(market_returns)} дней")
    print(f"  ⚠️  Минимальное окно для стабильного расчёта: 5 дней")

    # === ФИЛЬТР ПО ВРЕМЕНИ ===
    has_time = data[tickers[0]]['TRADEDATE'].iloc[0].time() != pd.Timestamp('00:00:00').time()
    trade_time_filter = trading_start_time if has_time and time_filter_enabled else None
    if trade_time_filter:
        print(f"⏳ Применён фильтр по времени: {trade_time_filter}")
    else:
        print("📅 Данные дневные — фильтр по времени отключён")

    # === ТЕСТ РЫНОЧНОГО ФИЛЬТРА С РАЗНЫМИ ОКНАМИ (С ЗАЩИТОЙ ОТ ОШИБОК) ===
    print("\n🧪 ТЕСТ РЫНОЧНОГО ФИЛЬТРА С РАЗНЫМИ ЗНАЧЕНИЯМИ market_vol_window:")
    test_windows = [10, 21, 40, 60, 80, 100, 120]
    for window in test_windows:
        strategy = DualMomentumStrategy(
            base_lookback=20,
            base_vol_window=10,
            market_vol_window=window,
            market_vol_threshold=0.02,  # Низкий порог для гарантированного срабатывания
            debug=False
        )
        filter_result = strategy.market_filter(market_df, rvi_data)
        status = "✅ СРАБОТАЛ" if filter_result.get('triggered', False) else "❌ НЕ СРАБОТАЛ"
        
        # 🔑 ЗАЩИТА ОТ ОШИБКИ: безопасное форматирование при отсутствии данных
        used_win = filter_result.get('used_vol_window', 'N/A')
        used_win_str = f"{used_win:3d}" if isinstance(used_win, int) else f"{str(used_win):>3}"
        
        vol_value = filter_result.get('market_vol')
        vol_str = f"{vol_value:.2%}" if isinstance(vol_value, (int, float)) and vol_value is not None else "N/A"
        
        print(f"  market_vol_window={window:3d} → {status} | использовано окно={used_win_str} | волатильность={vol_str}")

    # === ЗАПУСК БЭКТЕСТА С ПРОДАКШН-ПАРАМЕТРАМИ ===
    print("\n▶ ЗАПУСК БЭКТЕСТА С ПРОИЗВОДСТВЕННЫМИ ПАРАМЕТРАМИ...")
    print(f"   Версия стратегии: {production_params.get('version', 'N/A')}")
    print(f"   Базовое окно момента: {production_params['base_lookback']} дней")
    print(f"   Окно волатильности активов: {production_params['base_vol_window']} дней")
    print(f"   Окно волатильности рынка: {production_params['market_vol_window']} дней")
    print(f"   Порог рыночной волатильности: {production_params['market_vol_threshold']:.1%} годовых")
    
    # 🔑 ИСПРАВЛЕНО: фильтрация неподдерживаемых параметров
    # Параметр 'trend_r_squared_threshold' используется ТОЛЬКО для отчётов тренда,
    # но не принимается конструктором DualMomentumStrategy
    strategy_params = filter_strategy_params(production_params)
    strategy = DualMomentumStrategy(**strategy_params)
    
    bt = Backtester(
        commission=commission,
        default_commission=default_commission,
        slippage=slippage,
        use_slippage=use_slippage,
        trade_time_filter=trade_time_filter
    )

    try:
        result = bt.run(
            strategy,
            data,
            market_data=market_df,
            rvi_data=rvi_data,
            initial_capital=initial_capital
        )
        print("\n✅ БЭКТЕСТ ЗАВЕРШЁН:")
        print(f"   Финальная стоимость: {result['final_value']:,.2f} ₽")
        print(f"   CAGR: {result['cagr']:.2%}")
        print(f"   Sharpe Ratio: {result['sharpe']:.2f}")
        print(f"   Макс. просадка: {result['max_drawdown']:.2%}")
        print(f"   Количество сделок: {result.get('total_trades', 'N/A')}")
        
        # 🔑 СОХРАНЕНИЕ РАСШИРЕННОГО ЛОГА СДЕЛОК В CSV
        print("\n💾 ЭКСПОРТ РАСШИРЕННОГО ЛОГА СДЕЛОК В CSV...")
        trades_file = save_trades_to_csv(result['trades'], project_root, strategy_params)
        
        # 🔑 ДИАГНОСТИКА: Анализ использования рыночного фильтра
        if 'market_filter_stats' in result:
            stats = result['market_filter_stats']
            total_days = stats.get('total_days', 0)
            rvi_triggered = stats.get('rvi_triggered', 0)
            vol_triggered = stats.get('vol_triggered', 0)
            total_triggered = rvi_triggered + vol_triggered
            
            print(f"\n📊 СТАТИСТИКА РЫНОЧНОГО ФИЛЬТРА:")
            print(f"   Всего торговых дней: {total_days}")
            print(f"   Срабатываний по RVI (≥36): {rvi_triggered} ({rvi_triggered/total_days:.1%})")
            print(f"   Срабатываний по волатильности (≥35%): {vol_triggered} ({vol_triggered/total_days:.1%})")
            print(f"   Общая защита капитала: {total_triggered} дней ({total_triggered/total_days:.1%})")
            print(f"   Средняя длительность режима защиты: {total_triggered / max(1, (rvi_triggered > 0) + (vol_triggered > 0)):.1f} дня")

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ БЭКТЕСТЕ: {e}")
        import traceback
        traceback.print_exc()
        return

    # === ЗАПУСК ПОЛНОЙ ОПТИМИЗАЦИИ (ОПЦИОНАЛЬНО) ===
    print("\n🔍 ЗАПУСК ПОЛНОЙ ОПТИМИЗАЦИИ (опционально)...")
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    total = len(list(product(*values)))
    print(f"   ⚙️  Всего комбинаций в полной сетке: {total:,}")
    print(f"   💡 Рекомендуется использовать пошаговую оптимизацию (stepwise_optimization4.py)")
    print(f"      для избежания комбинаторного взрыва и переобучения.")


if __name__ == "__main__":
    main()
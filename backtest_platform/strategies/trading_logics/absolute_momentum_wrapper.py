# backtest_platform/strategies/trading_logics/absolute_momentum_wrapper.py

"""
Версия: 1.0.0 
Обёртка для добавления абсолютного импульса (absolute momentum) поверх любой базовой логики выбора актива.

Эта логика НЕ выбирает актив сама. Вместо этого она:
1. Делегирует выбор базовой логике (например, AdaptiveMomentumLogic).
2. Проверяет, превышает ли доходность выбранного актива доходность безрискового актива (LQDT) за lookback_period.
3. Возвращает выбранный актив только если его абсолютный импульс положителен; иначе — возвращает risk_free_ticker.

Это реализует ключевой элемент Dual Momentum по Гэри Антончи.
"""

from .base_logic import TradingLogic
import pandas as pd

__version__ = "1.0.0"
__author__ = "Oleg Dev"
__date__ = "2026-02-08"

class AbsoluteMomentumWrapper(TradingLogic):
    """
    Обёртка, добавляющая фильтр абсолютного импульса к любой другой торговой логике.
    """

    def __init__(self, base_logic: TradingLogic, lookback_period: int, **kwargs):
        """
        Инициализация обёртки.

        Args:
            base_logic (TradingLogic): Базовая логика для выбора актива (например, AdaptiveMomentumLogic).
            lookback_period (int): Период для расчёта абсолютного импульса (в торговых днях).
            **kwargs: Дополнительные параметры для базового класса (включая risk_free_ticker).
        """
        super().__init__(**kwargs)
        self.base_logic = base_logic
        self.lookback_period = lookback_period

    def select_best_asset(self, data_dict: dict[str, pd.DataFrame]) -> str:
        """
        Выбирает актив с помощью базовой логики, затем применяет фильтр абсолютного импульса.

        Args:
            data_dict (dict[str, pd.DataFrame]): Данные по всем активам.

        Returns:
            str: Тикер актива или risk_free_ticker, если абсолютный импульс отрицателен.
        """
        # Шаг 1: Выбор лучшего актива по базовой логике
        candidate_ticker = self.base_logic.select_best_asset(data_dict)

        # Если базовая логика уже вернула кэш, ничего не меняем
        if candidate_ticker == self.risk_free_ticker:
            return candidate_ticker

        # Шаг 2: Проверка достаточности данных для обоих активов
        if len(data_dict[candidate_ticker]) < self.lookback_period or \
           len(data_dict[self.risk_free_ticker]) < self.lookback_period:
            return self.risk_free_ticker

        # Шаг 3: Расчёт доходности за lookback_period
        asset_price_start = data_dict[candidate_ticker]['CLOSE'].iloc[-self.lookback_period]
        asset_price_end = data_dict[candidate_ticker]['CLOSE'].iloc[-1]
        asset_return = (asset_price_end / asset_price_start) - 1

        rf_price_start = data_dict[self.risk_free_ticker]['CLOSE'].iloc[-self.lookback_period]
        rf_price_end = data_dict[self.risk_free_ticker]['CLOSE'].iloc[-1]
        rf_return = (rf_price_end / rf_price_start) - 1

        # Шаг 4: Сравнение и решение
        if asset_return > rf_return:
            return candidate_ticker
        else:
            return self.risk_free_ticker
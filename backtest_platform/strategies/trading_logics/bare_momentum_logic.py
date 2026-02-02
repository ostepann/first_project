# backtest_platform/strategies/trading_logics/bare_momentum_logic.py

"""
Конкретная реализация торговой логики: "Голый момент" (Bare Momentum).

Эта логика представляет собой самый простой вариант стратегии — она выбирает 
актив исключительно на основе его абсолютного момента (прироста цены) за 
заданный период, игнорируя все фильтры (волатильность, тренд и т.д.).

ОСОБЕННОСТИ:
- Очень быстрая в вычислениях.
- Подвержена влиянию рыночного шума и просадок, так как не фильтрует риски.
- Используется в основном для бенчмаркинга или в очень спокойных рыночных условиях.
"""

from .base_logic import TradingLogic
import pandas as pd

class BareMomentumLogic(TradingLogic):
    """
    Логика торговли, основанная только на абсолютном моменте.

    Наследуется от абстрактного класса `TradingLogic` и реализует его единственный
    обязательный метод `select_best_asset`.
    """

    def __init__(self, lookback_period: int, **kwargs):
        """
        Инициализирует логику "голого момента".

        Args:
            lookback_period (int): Количество дней в прошлом, за которые рассчитывается момент.
            **kwargs: Дополнительные параметры, передаваемые в базовый класс 
                      (в первую очередь `risk_free_ticker`).
        """
        super().__init__(**kwargs)
        self.lookback_period = lookback_period

    def select_best_asset(self, data_dict: dict[str, pd.DataFrame]) -> str:
        """
        Выбирает актив с наибольшим абсолютным моментом.

        Алгоритм:
        1. Проходит по всем активам в `data_dict`, кроме кэш-актива.
        2. Для каждого актива проверяет, достаточно ли у него исторических данных.
        3. Рассчитывает момент как (текущая цена - цена N дней назад) / цена N дней назад.
        4. Выбирает актив с максимальным значением момента.
        5. Если ни один актив не имеет достаточных данных, возвращает кэш-актив.

        Args:
            data_dict (dict[str, pd.DataFrame]): Данные по активам.

        Returns:
            str: Тикер актива с лучшим моментом или `risk_free_ticker`.
        """
        best_mom = -float('inf')
        best_ticker = self.risk_free_ticker
        
        for ticker, df in data_dict.items():
            # Пропускаем кэш-актив, так как он не торгуется в этом режиме
            if ticker == self.risk_free_ticker:
                continue
            # Проверка наличия достаточного количества данных для расчёта
            if len(df) < self.lookback_period:
                continue
                
            # Расчёт абсолютного момента
            mom = (df['CLOSE'].iloc[-1] - df['CLOSE'].iloc[-self.lookback_period]) / df['CLOSE'].iloc[-self.lookback_period]
            if mom > best_mom:
                best_mom = mom
                best_ticker = ticker
                
        return best_ticker
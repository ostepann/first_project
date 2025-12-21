from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def generate_signal(self, data_dict, market_data=None, **kwargs):
        """
        Генерация торгового сигнала.
        
        Args:
            data_dict: dict, ключи — тикеры, значения — pd.DataFrame с колонками
                       TRADEDATE, OPEN, HIGH, LOW, CLOSE, VOLUME
            market_data: (опционально) pd.DataFrame — рыночный индекс для волатильности
        
        Returns:
            dict: например, {'selected': 'EQMX'} или {'allocation': {'GOLD': 1.0}}
        """
        pass

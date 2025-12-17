from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def generate_signal(self, data_dict: dict, **kwargs) -> dict:
        """
        data_dict: {'GOLD': df, 'EQMX': df, 'OBLG': df, 'LQDT': df}
        Returns: {'selected': 'EQMX'} or {'allocation': {'GOLD': 0.6, 'LQDT': 0.4}}
        """
        pass

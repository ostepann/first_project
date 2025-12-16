"""
Base Strategy class for trading strategies.
All custom strategies should inherit from this class.
"""

class BaseStrategy:
    """
    Abstract base class for trading strategies.
    """
    
    def __init__(self):
        self.position = 0  # Current position (0 for no position, 1 for long, -1 for short)
        self.cash = 10000  # Starting cash
        self.holdings = 0  # Value of holdings
        self.total_value = self.cash  # Total portfolio value
        
    def initialize(self, data):
        """
        Initialize strategy with data.
        
        Args:
            data: Input data for the strategy
        """
        pass
    
    def calculate_signal(self, data_point):
        """
        Calculate trading signal based on data point.
        
        Args:
            data_point: A single data point (e.g., OHLCV data)
            
        Returns:
            Signal: Trading signal (-1 for sell, 0 for hold, 1 for buy)
        """
        raise NotImplementedError("Subclasses must implement calculate_signal method")
    
    def update_portfolio(self, price, signal):
        """
        Update portfolio based on signal and price.
        
        Args:
            price: Current asset price
            signal: Trading signal
        """
        pass
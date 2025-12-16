"""
Backtester class for running strategy simulations.
"""

import pandas as pd
import numpy as np
from backtest_platform.core.base_strategy import BaseStrategy


class Backtester:
    """
    Main class for backtesting trading strategies.
    """
    
    def __init__(self, strategy: BaseStrategy, initial_capital=10000):
        """
        Initialize the backtester.
        
        Args:
            strategy: Trading strategy to backtest
            initial_capital: Initial capital for the simulation
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.data = None
        self.signals = []
        self.portfolio_values = []
        
    def load_data(self, data_path):
        """
        Load market data for backtesting.
        
        Args:
            data_path: Path to the data file
        """
        self.data = pd.read_csv(data_path)
        
    def run_backtest(self):
        """
        Run the backtesting simulation.
        
        Returns:
            Results of the backtest
        """
        if self.data is None:
            raise ValueError("Data not loaded. Please load data first.")
            
        # Initialize the strategy
        self.strategy.initialize(self.data)
        
        # Run the backtest through each data point
        portfolio_value = self.initial_capital
        position = 0  # 0: no position, 1: long, -1: short
        
        for index, row in self.data.iterrows():
            # Calculate signal based on current data point
            signal = self.strategy.calculate_signal(row)
            
            # Store the signal
            self.signals.append(signal)
            
            # Update portfolio based on signal
            if 'close' in row:
                close_price = row['close']
            elif 'Close' in row:
                close_price = row['Close']
            else:
                close_price = row.iloc[-1]  # Assume last column is closing price
                
            self.strategy.update_portfolio(close_price, signal)
            
            # Track portfolio value over time
            holdings_value = 0
            if hasattr(self.strategy, 'position') and hasattr(self.strategy, 'cash'):
                holdings_value = self.strategy.position * close_price if hasattr(self.strategy, 'position') else 0
                portfolio_value = self.strategy.cash + holdings_value
                self.portfolio_values.append(portfolio_value)
        
        return self._calculate_results()
    
    def _calculate_results(self):
        """
        Calculate performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.portfolio_values:
            return {}
            
        portfolio_df = pd.DataFrame({'portfolio_value': self.portfolio_values})
        portfolio_df['returns'] = portfolio_df['portfolio_value'].pct_change()
        
        total_return = (self.portfolio_values[-1] - self.initial_capital) / self.initial_capital
        total_trades = len([s for s in self.signals if s != 0])
        
        # Calculate other metrics
        returns = portfolio_df['returns'].dropna()
        if len(returns) > 1:
            volatility = returns.std() * np.sqrt(252)  # Annualized volatility
            sharpe_ratio = (returns.mean() * 252) / volatility if volatility != 0 else 0
        else:
            volatility = 0
            sharpe_ratio = 0
            
        max_drawdown = self._calculate_max_drawdown(portfolio_df['portfolio_value'])
        
        return {
            'total_return': total_return,
            'total_trades': total_trades,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'final_portfolio_value': self.portfolio_values[-1]
        }
    
    def _calculate_max_drawdown(self, portfolio_values):
        """
        Calculate the maximum drawdown.
        
        Args:
            portfolio_values: Series of portfolio values over time
            
        Returns:
            Maximum drawdown value
        """
        peak = portfolio_values.iloc[0]
        max_dd = 0
        
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_dd:
                max_dd = drawdown
                
        return max_dd
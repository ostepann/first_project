"""
Performance metrics for evaluating trading strategies.
"""

import numpy as np
import pandas as pd


def calculate_total_return(initial_value, final_value):
    """
    Calculate the total return of a strategy.
    
    Args:
        initial_value: Initial portfolio value
        final_value: Final portfolio value
        
    Returns:
        Total return as a decimal
    """
    return (final_value - initial_value) / initial_value


def calculate_annualized_return(total_return, num_years):
    """
    Calculate the annualized return.
    
    Args:
        total_return: Total return over the period
        num_years: Number of years in the period
        
    Returns:
        Annualized return as a decimal
    """
    return (1 + total_return) ** (1 / num_years) - 1


def calculate_volatility(returns):
    """
    Calculate the annualized volatility of returns.
    
    Args:
        returns: Series or array of returns
        
    Returns:
        Annualized volatility as a decimal
    """
    if len(returns) <= 1:
        return 0
    return np.std(returns, ddof=1) * np.sqrt(252)  # Assuming 252 trading days per year


def calculate_sharpe_ratio(returns, risk_free_rate=0.0):
    """
    Calculate the Sharpe ratio of a strategy.
    
    Args:
        returns: Series or array of returns
        risk_free_rate: Risk-free rate of return (annualized)
        
    Returns:
        Sharpe ratio
    """
    if len(returns) <= 1:
        return 0
    
    excess_returns = returns - risk_free_rate / 252  # Adjust risk-free rate to daily
    mean_excess_return = np.mean(excess_returns)
    volatility = calculate_volatility(returns)
    
    if volatility == 0:
        return 0
    
    return mean_excess_return * 252 / volatility  # Annualize


def calculate_max_drawdown(portfolio_values):
    """
    Calculate the maximum drawdown of a portfolio.
    
    Args:
        portfolio_values: Series or array of portfolio values over time
        
    Returns:
        Maximum drawdown as a decimal
    """
    if len(portfolio_values) == 0:
        return 0
        
    peak = portfolio_values[0]
    max_dd = 0
    
    for value in portfolio_values:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak
        if drawdown > max_dd:
            max_dd = drawdown
            
    return max_dd


def calculate_calmar_ratio(returns, portfolio_values):
    """
    Calculate the Calmar ratio (annualized return / max drawdown).
    
    Args:
        returns: Series or array of returns
        portfolio_values: Series or array of portfolio values over time
        
    Returns:
        Calmar ratio
    """
    if len(portfolio_values) == 0:
        return 0
    
    total_return = calculate_total_return(portfolio_values[0], portfolio_values[-1])
    years = len(portfolio_values) / 252  # Assuming daily data
    annualized_return = calculate_annualized_return(total_return, years)
    max_dd = calculate_max_drawdown(portfolio_values)
    
    if max_dd == 0:
        return float('inf') if annualized_return > 0 else 0
    
    return annualized_return / max_dd


def calculate_win_loss_ratio(returns):
    """
    Calculate the win/loss ratio of a strategy.
    
    Args:
        returns: Series or array of returns
        
    Returns:
        Win/loss ratio
    """
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    
    if len(losses) == 0:
        return float('inf') if len(wins) > 0 else 0
    
    avg_win = np.mean(wins) if len(wins) > 0 else 0
    avg_loss = np.abs(np.mean(losses))
    
    if avg_loss == 0:
        return float('inf') if avg_win > 0 else 0
    
    return avg_win / avg_loss


def calculate_profit_factor(returns):
    """
    Calculate the profit factor of a strategy.
    
    Args:
        returns: Series or array of returns
        
    Returns:
        Profit factor
    """
    gains = sum(returns[returns > 0])
    losses = abs(sum(returns[returns < 0]))
    
    if losses == 0:
        return float('inf') if gains > 0 else 0
    
    return gains / losses
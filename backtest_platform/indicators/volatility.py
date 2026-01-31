# backtest_platform/indicators/volatility.py

import pandas as pd
import numpy as np

def rolling_volatility(returns: pd.Series, window: int = 20) -> pd.Series:
    """Годовая историческая волатильность на основе rolling std."""
    if len(returns) < window:
        return pd.Series([np.nan] * len(returns), index=returns.index)
    return returns.rolling(window).std() * np.sqrt(252)

def market_volatility(market_df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Рыночная волатильность по CLOSE."""
    returns = market_df['CLOSE'].pct_change()
    return rolling_volatility(returns, window)

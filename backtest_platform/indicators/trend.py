# backtest_platform/indicators/trend.py
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

def detect_trend(prices: pd.Series, window: int = 20) -> str:
    """
    Определяет тренд на основе наклона линейной регрессии.
    
    Args:
        prices: pd.Series цен (CLOSE)
        window: окно для анализа
    
    Returns:
        'uptrend', 'downtrend', 'sideways'
    """
    if len(prices) < window:
        return 'sideways'
    
    y = prices.tail(window).values
    x = np.arange(len(y)).reshape(-1, 1)
    
    model = LinearRegression()
    model.fit(x, y)
    slope = model.coef_[0]
    r_squared = model.score(x, y)
    
    # Пороги можно оптимизировать
    if r_squared < 0.2:
        return 'sideways'
    elif slope > 0:
        return 'uptrend'
    else:
        return 'downtrend'

def get_trend_strength(prices: pd.Series, window: int = 14) -> float:
    """Возвращает силу тренда через нормированный наклон."""
    if len(prices) < window:
        return 0.0
    y = prices.tail(window).values
    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]
    return abs(slope) / prices.iloc[-1]  # нормировка

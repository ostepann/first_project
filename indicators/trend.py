# backtest_platform/indicators/trend.py

import pandas as pd
import numpy as np

def detect_trend(prices: pd.Series, window: int, r_squared_threshold: float) -> str:
    """
    🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ТРЕНДА (для отчётов и исследований).
    
    Классифицирует тренд на основе наклона и статистической значимости (R²).
    Возвращает человекочитаемую строку.
    
    ⚠️ НЕ ИСПОЛЬЗУЙТЕ ЭТУ ФУНКЦИЮ В ЦИКЛЕ СТРАТЕГИИ!
    Она медленнее из-за расчёта R² и не подходит для бинарных решений.
    
    Args:
        prices: pd.Series цен (CLOSE)
        window: окно для анализа (например, 20 периодов)
        r_squared_threshold: порог R² для определения "бокового" тренда (например, 0.2)
    
    Returns:
        'uptrend', 'downtrend', 'sideways'
    """
    if len(prices) < window:
        return 'sideways'
    
    y = prices.tail(window).dropna().values
    if len(y) < 2:
        return 'sideways'
        
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    
    # Расчёт коэффициента детерминации R²
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
    
    # Классификация тренда
    if r_squared < r_squared_threshold:
        return 'sideways'
    elif slope > 0:
        return 'uptrend'
    else:
        return 'downtrend'

def get_trend_strength(prices: pd.Series, window: int = 14) -> float:
    """
    🔍 ИЗМЕРЕНИЕ СИЛЫ ТРЕНДА (для отчётов и исследований).
    
    Возвращает количественную меру силы тренда.
    
    ⚠️ НЕ ИСПОЛЬЗУЙТЕ ЭТУ ФУНКЦИЮ В ЦИКЛЕ СТРАТЕГИИ!
    Для простой проверки наличия тренда используйте `_is_uptrend`.
    
    Args:
        prices: pd.Series цен (CLOSE)
        window: окно для анализа (по умолчанию 14 периодов)
    
    Returns:
        float: сила тренда (абсолютное значение нормированного наклона)
    """
    if len(prices) < window:
        return 0.0
        
    y = prices.tail(window).dropna().values
    if len(y) < 2:
        return 0.0
        
    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]
    return abs(slope) / prices.iloc[-1]  # нормировка на текущую цену
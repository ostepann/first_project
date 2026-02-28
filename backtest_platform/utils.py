# first_project\backtest_platform\utils.py

import pandas as pd

def load_market_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if 'TRADEDATE' in df.columns:
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
    
    # Удаление строк с пропущенными значениями
    df = df.dropna()
    
    return df

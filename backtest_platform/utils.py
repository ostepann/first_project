import pandas as pd

def load_market_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if 'TRADEDATE' in df.columns:
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
    return df

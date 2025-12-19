# Загрузка данных из CSV
data_dir = os.path.join(os.path.dirname(__file__), 'data')
tickers = ['GOLD', 'EQMX', 'OBLG', 'LQDT']
data = {}

print("Загрузка данных из CSV...")
for ticker in tickers:
    file_path = os.path.join(data_dir, f'{ticker}.csv')
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Файл не найден: {file_path}")
    df = load_market_data(file_path)
    df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
    data[ticker] = df
    print(f"✅ {ticker}: {df['TRADEDATE'].min().date()} → {df['TRADEDATE'].max().date()} ({len(df)} строк)")

# Загрузка RVI
rvi_path = os.path.join(data_dir, 'RVI.csv')
if os.path.exists(rvi_path):
    rvi_data = load_market_data(rvi_path)
    rvi_data['TRADEDATE'] = pd.to_datetime(rvi_data['TRADEDATE'])
    print(f"✅ RVI загружен: {rvi_data['TRADEDATE'].min().date()} → {rvi_data['TRADEDATE'].max().date()}")
else:
    rvi_data = None
    print("⚠️ RVI.csv не найден — будет использоваться средний уровень")

market_df = data['EQMX'].copy()

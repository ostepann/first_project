import requests
import pandas as pd
from datetime import datetime, timezone
import os

# Настройки: тикеры и соответствующие параметры на MOEX
TICKERS_CONFIG = {
    'OBLG': {'market': 'bonds',    'board': 'TQCB', 'secid': 'OBLG'},  # Пример ISIN ОФЗ; замените на нужный
    'EQMX': {'market': 'shares',   'board': 'TQTF', 'secid': 'EQMX'},
    'GOLD': {'market': 'shares',   'board': 'TQTF', 'secid': 'GOLD'},          # GOLD → ETF FXGD (золото)
    'LQDT': {'market': 'shares',   'board': 'TQTF', 'secid': 'LQDT'},
}

# Альтернатива: если вы используете другие ISIN/тикеры для OBLG — замените 'secid' выше

def fetch_spread(market, board, secid):
    url = f"https://iss.moex.com/iss/engines/stock/markets/{market}/boards/{board}/securities/{secid}.json"
    params = {'iss.only': 'marketdata'}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        marketdata = data.get('marketdata')
        if not marketdata or not marketdata.get('data'):
            return None
        
        columns = marketdata['columns']
        row = marketdata['data'][0]
        d = dict(zip(columns, row))
        
        bid = d.get('bid')
        ask = d.get('ask')
        
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            return None
        
        spread_abs = ask - bid
        mid = (ask + bid) / 2
        spread_bps = (spread_abs / mid) * 10_000  # в базисных пунктах
        
        return {
            'bid': bid,
            'ask': ask,
            'spread_abs': spread_abs,
            'spread_bps': round(spread_bps, 3),
            'mid_price': round(mid, 6),
            'volume_bid': d.get('biddepth', 0),
            'volume_ask': d.get('askdepth', 0),
        }
    except Exception as e:
        print(f"⚠️ Ошибка при загрузке {secid}: {e}")
        return None

def main():
    timestamp = datetime.now(timezone.utc).isoformat()
    records = []
    
    for alias, config in TICKERS_CONFIG.items():
        print(f"Запрашиваю данные для {alias} ({config['secid']})...")
        spread_data = fetch_spread(config['market'], config['board'], config['secid'])
        
        if spread_data:
            record = {
                'datetime_utc': timestamp,
                'alias': alias,
                'secid': config['secid'],
                'market': config['market'],
                'board': config['board'],
                **spread_data
            }
            records.append(record)
        else:
            print(f"❌ Нет данных по {alias}")
    
    if not records:
        print("Нет данных для сохранения.")
        return
    
    df = pd.DataFrame(records)
    
    # Сохраняем в CSV (дописываем новые строки)
    filename = 'moex_spreads_log.csv'
    file_exists = os.path.isfile(filename)
    df.to_csv(filename, mode='a', header=not file_exists, index=False)
    
    print(f"\n✅ Успешно сохранено {len(records)} записей в {filename}")
    print(df[['alias', 'spread_bps', 'bid', 'ask']].to_string(index=False))

if __name__ == '__main__':
    main()
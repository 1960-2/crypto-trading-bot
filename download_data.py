#!/usr/bin/env python3
"""Автоматическая загрузка данных Binance"""

import pandas as pd
import requests
from datetime import datetime, timedelta
import os

def download_binance_data(days: int = 180):
    """Скачать данные с Binance API"""
    print(f"📥 Загрузка данных за {days} дней...")
    
    # Binance API endpoint
    url = "https://api.binance.com/api/v3/klines"
    
    # Параметры
    params = {
        'symbol': 'BTCUSDT',
        'interval': '1h',
        'limit': 1000  # максимум за запрос
    }
    
    all_data = []
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (days * 24 * 60 * 60 * 1000)
    
    current_time = start_time
    while current_time < end_time:
        params['startTime'] = current_time
        params['endTime'] = min(current_time + (1000 * 60 * 60 * 1000), end_time)
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if not data:
                break
            
            all_data.extend(data)
            current_time = data[-1][0] + 1
            
            print(f"✅ Загружено {len(all_data)} свечей...")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            break
    
    # Конвертировать в DataFrame
    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    
    # Сохранить
    os.makedirs('data', exist_ok=True)
    output_file = 'data/btc_real_data.csv'
    df.to_csv(output_file, index=False)
    
    print(f"\n💾 Сохранено в: {output_file}")
    print(f"📊 Всего свечей: {len(df)}")
    print(f"📅 Период: {pd.to_datetime(df['open_time'].iloc[0], unit='ms')} - {pd.to_datetime(df['open_time'].iloc[-1], unit='ms')}")
    
    return output_file

if __name__ == "__main__":
    download_binance_data(days=180)
import pandas as pd
import requests
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict
import asyncio
import aiohttp

class CryptoDataPipeline:
    def __init__(self):
        self.data_dir = "/Users/finnbryant/Dev/CryptoApp/data"
        self.supported_symbols = ["BTC", "ETH", "ADA", "SOL", "MATIC", "DOT"]
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        
    async def collect_training_data(self, days: int = 90) -> str:
        """Collect comprehensive training data for all supported symbols"""
        os.makedirs(self.data_dir, exist_ok=True)
        
        all_data = []
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._fetch_symbol_data(session, symbol, days) 
                for symbol in self.supported_symbols
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for symbol, result in zip(self.supported_symbols, results):
                if isinstance(result, Exception):
                    logging.error(f"Failed to fetch {symbol}: {result}")
                    continue
                    
                if result:
                    # Add symbol column
                    for row in result:
                        row['symbol'] = symbol
                    all_data.extend(result)
        
        # Create DataFrame and save
        df = pd.DataFrame(all_data)
        
        if not df.empty:
            # Sort by timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values(['symbol', 'timestamp'])
            
            # Save training data
            filename = f"{self.data_dir}/training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            
            logging.info(f"Collected {len(df)} data points for training: {filename}")
            return filename
        else:
            raise Exception("No data collected for training")
    
    async def _fetch_symbol_data(self, session: aiohttp.ClientSession, symbol: str, days: int) -> List[Dict]:
        """Fetch historical data for a single symbol"""
        try:
            coingecko_id = self._get_coingecko_id(symbol)
            
            url = f"{self.coingecko_base}/coins/{coingecko_id}/market_chart"
            params = {
                "vs_currency": "usd",
                "days": str(days),
                "interval": "hourly"
            }
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logging.warning(f"API error for {symbol}: {response.status}")
                    return []
                    
                data = await response.json()
                
                prices = data.get('prices', [])
                volumes = data.get('total_volumes', [])
                market_caps = data.get('market_caps', [])
                
                result = []
                for i, (timestamp, price) in enumerate(prices):
                    volume = volumes[i][1] if i < len(volumes) else 0
                    market_cap = market_caps[i][1] if i < len(market_caps) else 0
                    
                    result.append({
                        'timestamp': timestamp,
                        'close': price,
                        'volume': volume,
                        'market_cap': market_cap
                    })
                
                return result
                
        except Exception as e:
            logging.error(f"Error fetching {symbol}: {e}")
            return []
    
    def _get_coingecko_id(self, symbol: str) -> str:
        """Map symbol to CoinGecko ID"""
        mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum', 
            'ADA': 'cardano',
            'SOL': 'solana',
            'MATIC': 'matic-network',
            'DOT': 'polkadot'
        }
        return mapping.get(symbol.upper(), symbol.lower())
    
    def get_latest_training_file(self) -> str:
        """Get the most recent training data file"""
        files = [f for f in os.listdir(self.data_dir) if f.startswith('training_data_') and f.endswith('.csv')]
        
        if not files:
            raise FileNotFoundError("No training data files found")
        
        # Sort by filename (timestamp embedded)
        files.sort(reverse=True)
        return os.path.join(self.data_dir, files[0])

import pandas as pd
import logging
import os
from datetime import datetime
from typing import List, Dict
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

class CryptoDataPipeline:
    def __init__(self):
        # Get project root dynamically
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(project_root, 'data')
        self.supported_symbols = ["BTC", "ETH", "ADA", "SOL", "MATIC", "DOT", "BOSS"]
        self.cmc_base = "https://pro-api.coinmarketcap.com/v1"
        self.api_key = os.getenv('COINMARKETCAP_API_KEY')
        self._symbol_to_id = None
    
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
        """Fetch historical data for a single symbol from CoinMarketCap"""
        try:
            # Use CMC quotes endpoint
            url = f"{self.cmc_base}/cryptocurrency/quotes/latest"
            headers = {'X-CMC_PRO_API_KEY': self.api_key}
            params = {
                'symbol': symbol,
                'convert': 'USD'
            }
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    logging.warning(f"API error for {symbol}: {response.status}")
                    return []
                    
                data = await response.json()
                coin_data = data.get('data', {}).get(symbol)
                
                if not coin_data:
                    return []
                
                quote = coin_data.get('quote', {}).get('USD', {})
                
                # CMC doesn't provide historical hourly data in basic plan
                # Store current snapshot (you'd need CMC Pro for historical)
                return [{
                    'timestamp': datetime.now(),
                    'price': quote.get('price', 0),
                    'volume': quote.get('volume_24h', 0),
                    'market_cap': quote.get('market_cap', 0),
                    'percent_change_24h': quote.get('percent_change_24h', 0)
                }]
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
    
    async def add_new_symbol(self, symbol: str) -> bool:
        """Add a new symbol to the supported list after validating it exists"""
        try:
            symbol_upper = symbol.upper()
            
            # Check if already supported
            if symbol_upper in self.supported_symbols:
                logging.info(f"Symbol {symbol_upper} is already supported")
                return True
            
            # Test if symbol is valid by trying to get its CoinGecko ID
            coingecko_id = await self._get_coingecko_id(symbol_upper)
            
            # If we get here, the symbol is valid
            self.supported_symbols.append(symbol_upper)
            logging.info(f"Successfully added new symbol: {symbol_upper} (ID: {coingecko_id})")
            return True
            
        except Exception as e:
            logging.error(f"Failed to add symbol {symbol}: {e}")
            return False
    
    async def validate_symbol(self, symbol: str) -> Dict[str, str]:
        """Validate a symbol and return its details"""
        try:
            coingecko_id = await self._get_coingecko_id(symbol)
            
            # Get coin details
            if not hasattr(self, '_coins_cache') or not self._coins_cache:
                await self._load_coins_list()
            
            coin_info = next((coin for coin in self._coins_cache 
                            if coin['id'] == coingecko_id), None)
            
            return {
                'symbol': symbol.upper(),
                'coingecko_id': coingecko_id,
                'name': coin_info['name'] if coin_info else 'Unknown',
                'status': 'valid'
            }
            
        except Exception as e:
            return {
                'symbol': symbol.upper(),
                'coingecko_id': None,
                'name': None,
                'status': 'invalid',
                'error': str(e)
            }
    
    async def search_symbols(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Search for symbols matching a query"""
        # For CMC, we'll search directly via API
        try:
            headers = {'X-CMC_PRO_API_KEY': self.api_key}
            url = f"{self.cmc_base}/cryptocurrency/map"
            params = {'limit': 5000}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        coins = data.get('data', [])
                        
                        query_lower = query.lower()
                        matches = []
                        
                        for coin in coins:
                            if (query_lower in coin['symbol'].lower() or 
                                query_lower in coin['name'].lower()):
                                matches.append({
                                    'symbol': coin['symbol'].upper(),
                                    'name': coin['name'],
                                    'cmc_id': coin['id']
                                })
                                
                                if len(matches) >= limit:
                                    break
                        
                        return matches
        except Exception as e:
            logging.error(f"Error searching symbols: {e}")
            return []
            {'id': 'solana', 'symbol': 'sol', 'name': 'Solana'},
            {'id': 'matic-network', 'symbol': 'matic', 'name': 'Polygon'},
            {'id': 'polkadot', 'symbol': 'dot', 'name': 'Polkadot'}
        ]
    
    def get_latest_training_file(self) -> str:
        """Get the most recent training data file"""
        files = [f for f in os.listdir(self.data_dir) if f.startswith('training_data_') and f.endswith('.csv')]
        
        if not files:
            raise FileNotFoundError("No training data files found")
        
        # Sort by filename (timestamp embedded)
        files.sort(reverse=True)
        return os.path.join(self.data_dir, files[0])

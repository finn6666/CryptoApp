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
        self.cg_base = "https://api.coingecko.com/api/v3"
        self.api_key = os.getenv('COINGECKO_API_KEY', '')
        self._symbol_to_id = None
        # Symbol → CoinGecko ID cache (populated lazily)
        self._cg_id_cache: dict = {}
    
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
        """Fetch current snapshot for a single symbol from CoinGecko."""
        try:
            # Resolve symbol → CoinGecko ID
            coin_id = self._cg_id_cache.get(symbol.upper())
            if not coin_id:
                search_url = f"{self.cg_base}/search"
                headers = {'x-cg-demo-api-key': self.api_key} if self.api_key else {}
                async with session.get(search_url, headers=headers, params={'query': symbol}) as resp:
                    if resp.status != 200:
                        return []
                    search_data = await resp.json()
                    for c in search_data.get('coins', []):
                        if c.get('symbol', '').upper() == symbol.upper():
                            coin_id = c.get('id')
                            self._cg_id_cache[symbol.upper()] = coin_id
                            break

            if not coin_id:
                logging.warning(f"CoinGecko ID not found for {symbol}")
                return []

            url = f"{self.cg_base}/coins/markets"
            headers = {'x-cg-demo-api-key': self.api_key} if self.api_key else {}
            params = {
                'vs_currency': 'usd',
                'ids': coin_id,
                'sparkline': 'false',
                'price_change_percentage': '24h',
            }

            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    logging.warning(f"CoinGecko API error for {symbol}: {response.status}")
                    return []

                data = await response.json()
                if not data:
                    return []

                coin_data = data[0]
                return [{
                    'timestamp': datetime.now(),
                    'price': coin_data.get('current_price', 0),
                    'volume': coin_data.get('total_volume', 0),
                    'market_cap': coin_data.get('market_cap', 0),
                    'percent_change_24h': coin_data.get('price_change_percentage_24h', 0),
                }]

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
        """Search for symbols matching a query via CoinGecko /search."""
        try:
            headers = {'x-cg-demo-api-key': self.api_key} if self.api_key else {}
            url = f"{self.cg_base}/search"
            params = {'query': query}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        matches = []
                        for coin in data.get('coins', [])[:limit]:
                            matches.append({
                                'symbol': (coin.get('symbol') or '').upper(),
                                'name': coin.get('name', ''),
                                'coingecko_id': coin.get('id', ''),
                            })
                        return matches
        except Exception as e:
            logging.error(f"Error searching symbols: {e}")
        return []
    
    def get_latest_training_file(self) -> str:
        """Get the most recent training data file"""
        files = [f for f in os.listdir(self.data_dir) if f.startswith('training_data_') and f.endswith('.csv')]
        
        if not files:
            raise FileNotFoundError("No training data files found")
        
        # Sort by filename (timestamp embedded)
        files.sort(reverse=True)
        return os.path.join(self.data_dir, files[0])

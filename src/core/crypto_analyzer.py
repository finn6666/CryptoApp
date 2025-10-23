import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class CoinStatus(Enum):
    CURRENT = "current"
    NEW = "new"
    UPCOMING = "upcoming"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    MEDIUM_HIGH = "medium-high"
    HIGH = "high"

@dataclass
class Coin:
    """Represents a cryptocurrency with all its data"""
    id: str
    name: str
    symbol: str
    status: CoinStatus
    attractiveness_score: float
    investment_highlights: List[str]
    market_cap_rank: Optional[int]
    price: Optional[float]
    price_btc: Optional[float]
    price_change_24h_usd: Optional[float]
    market_cap: Optional[str]
    total_volume: Optional[str]
    risk_level: Optional[RiskLevel] = None
    launch_date: Optional[str] = None
    presale_discount: Optional[str] = None
    presale_price: Optional[float] = None
    
class CryptoAnalyzer:
    """Main class for analyzing cryptocurrency data"""
    
    def __init__(self, data_file: str = "data/live_api.json"):
        self.data_file = data_file
        self.coins: List[Coin] = []
        self.load_data()
    
    def load_data(self) -> None:
        """Load cryptocurrency data from JSON file"""
        try:
            with open(self.data_file, 'r') as file:
                data = json.load(file)
                self.coins = self._parse_coins(data['coins'])
        except FileNotFoundError:
            print(f"Error: {self.data_file} not found!")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {self.data_file}")
    
    def _parse_coins(self, coins_data: List[Dict]) -> List[Coin]:
        """Parse raw coin data into Coin objects"""
        coins = []
        
        for coin_item in coins_data:
            item = coin_item['item']
            data = item.get('data', {})
            
            # Handle different price formats
            price = None
            if 'price' in data and data['price'] is not None:
                if isinstance(data['price'], str):
                    # Remove commas and convert
                    price_str = data['price'].replace(',', '')
                    try:
                        price = float(price_str)
                    except ValueError:
                        price = None
                else:
                    price = data['price']
            elif 'presale_price' in data:
                price = data['presale_price']
            
            # Get price change
            price_change = None
            if 'price_change_percentage_24h' in data and data['price_change_percentage_24h']:
                price_change = data['price_change_percentage_24h'].get('usd')
            
            # Parse risk level
            risk_level = None
            if 'risk_level' in item:
                try:
                    risk_level = RiskLevel(item['risk_level'])
                except ValueError:
                    risk_level = None
            
            coin = Coin(
                id=item['id'],
                name=item['name'],
                symbol=item['symbol'],
                status=CoinStatus(item['status']),
                attractiveness_score=item.get('attractiveness_score', 0.0),
                investment_highlights=item.get('investment_highlights', []),
                market_cap_rank=item.get('market_cap_rank'),
                price=price,
                price_btc=float(item.get('price_btc', 0)) if item.get('price_btc') else None,
                price_change_24h_usd=price_change,
                market_cap=data.get('market_cap'),
                total_volume=data.get('total_volume'),
                risk_level=risk_level,
                launch_date=item.get('launch_date'),
                presale_discount=item.get('presale_discount'),
                presale_price=data.get('presale_price')
            )
            coins.append(coin)
        
        return coins

    def get_top_coins(self, limit: int = 10, status: Optional[CoinStatus] = None) -> List[Coin]:
        """Get top coins by attractiveness score"""
        coins = self.coins.copy()

        # Filter by status if specified
        if status:
            coins = [coin for coin in coins if coin.status == status]
            
        # Sort by attractiveness score (highest first)
        coins.sort(key=lambda x: x.attractiveness_score, reverse=True)
        
        return coins[:limit]

    def get_trending_coins(self) -> List[Coin]:
        """Get trending coins sorted by attractiveness score"""
        return sorted(self.coins, key=lambda x: x.attractiveness_score, reverse=True)

    def get_low_cap_coins(self, limit: int = 10) -> List[Coin]:
        """Get low cap coins (under $500M market cap) prioritized by attractiveness score"""
        low_cap_coins = []
        
        for coin in self.coins:
            market_cap_str = coin.market_cap
            is_low_cap = False
            
            # Extract numeric value from market cap string
            if isinstance(market_cap_str, str) and '$' in market_cap_str:
                clean_str = market_cap_str.replace('$', '').replace(',', '')
                try:
                    if 'B' in clean_str:
                        market_cap_num = float(clean_str.replace('B', '')) * 1_000_000_000
                    elif 'M' in clean_str:
                        market_cap_num = float(clean_str.replace('M', '')) * 1_000_000
                    else:
                        market_cap_num = float(clean_str)
                        
                    if market_cap_num < 500_000_000:  # Under $500M
                        is_low_cap = True
                except:
                    pass
            
            if is_low_cap:
                low_cap_coins.append(coin)
        
        # Sort by attractiveness score (highest first)
        low_cap_coins.sort(key=lambda x: x.attractiveness_score, reverse=True)
        
        return low_cap_coins[:limit]

    def filter_by_status(self, status: CoinStatus) -> List[Coin]:
        """Filter coins by their status"""
        return [coin for coin in self.coins if coin.status == status]

    def get_high_potential_coins(self, min_score: float = 7.0) -> List[Coin]:
        """Get coins with high potential (attractiveness score above threshold)"""
        return [coin for coin in self.coins if coin.attractiveness_score >= min_score]
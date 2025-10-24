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
    price_change_24h: Optional[float]
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
            # Get price change
            price_change = None
            if 'price_change_percentage_24h' in data and data['price_change_percentage_24h']:
                price_change_data = data['price_change_percentage_24h']
                if isinstance(price_change_data, dict):
                    # Try different currency keys
                    price_change = (price_change_data.get('gbp') or 
                                price_change_data.get('usd') or 
                                price_change_data.get('eur'))
                elif isinstance(price_change_data, (int, float)):
                    # Direct numeric value
                    price_change = price_change_data
            
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
                price_change_24h=price_change,
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

        # Remove coins with price None or price >= 200 as i dont want high price coins
        coins = [coin for coin in coins if coin.price is not None and coin.price <= 200]

        return coins[:limit]

    def get_trending_coins(self) -> List[Coin]:
        """Get trending coins sorted by attractiveness score"""
        return sorted(self.coins, key=lambda x: x.attractiveness_score, reverse=True)

    def _parse_market_cap(self, market_cap_str: Optional[str]) -> float:
        """Helper method to parse market cap string and return numeric value"""
        if not market_cap_str or not isinstance(market_cap_str, str) or '£' not in market_cap_str:
            return 0
            
        clean_str = market_cap_str.replace('£', '').replace(',', '')
        try:
            if 'B' in clean_str:
                return float(clean_str.replace('B', '')) * 1_000_000_000
            elif 'M' in clean_str:
                return float(clean_str.replace('M', '')) * 1_000_000
            else:
                return float(clean_str)
        except:
            return 0

    def get_low_cap_coins(self, limit: int = 12) -> List[Coin]:
        """Get low cap coins (under $500M market cap) prioritized by attractiveness score"""
        low_cap_coins = []
        
        for coin in self.coins:
            market_cap_num = self._parse_market_cap(coin.market_cap)
            if market_cap_num > 0 and market_cap_num < 500_000_000:  # Under $500M
                low_cap_coins.append(coin)
        
        # Sort by attractiveness score (highest first)
        low_cap_coins.sort(key=lambda x: x.attractiveness_score, reverse=True)
        
        return low_cap_coins[:limit]

    def filter_by_status(self, status: CoinStatus) -> List[Coin]:
        """Filter coins by their status"""
        return [coin for coin in self.coins if coin.status == status]

    def get_high_potential_coins(self, min_score: float = 6.0) -> List[Coin]:
        """Get coins with high potential (attractiveness score above threshold)"""
        return [coin for coin in self.coins if coin.attractiveness_score >= min_score]
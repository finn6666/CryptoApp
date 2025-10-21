import requests
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from crypto_analyzer import Coin, CoinStatus, RiskLevel

class LiveDataFetcher:
    """Fetches live cryptocurrency data from APIs"""
    
    def __init__(self):
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CryptoAnalyzer/1.0'
        })
        
    def get_trending_coins(self, limit: int = 10) -> List[Dict]:
        """Get trending coins from CoinGecko"""
        try:
            url = f"{self.coingecko_base_url}/search/trending"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            trending_coins = []
            
            for item in data.get('coins', [])[:limit]:
                coin_data = item.get('item', {})
                trending_coins.append({
                    'id': coin_data.get('id'),
                    'name': coin_data.get('name'),
                    'symbol': coin_data.get('symbol'),
                    'market_cap_rank': coin_data.get('market_cap_rank'),
                    'thumb': coin_data.get('thumb'),
                    'price_btc': coin_data.get('price_btc'),
                    'score': coin_data.get('score', 0)
                })
            
            return trending_coins
            
        except requests.RequestException as e:
            print(f"Error fetching trending coins: {e}")
            return []
    
    def get_top_coins_by_market_cap(self, limit: int = 20) -> List[Dict]:
        """Get top coins by market capitalization"""
        try:
            url = f"{self.coingecko_base_url}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': limit,
                'page': 1,
                'sparkline': False,
                'price_change_percentage': '24h'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            print(f"Error fetching top coins: {e}")
            return []
    
    def get_gainers_and_losers(self, limit: int = 10) -> Dict[str, List[Dict]]:
        """Get biggest gainers and losers in 24h"""
        try:
            # Get a larger set of coins to find gainers/losers
            coins = self.get_top_coins_by_market_cap(100)
            
            # Filter and sort (handle None values)
            valid_coins = [coin for coin in coins 
                          if coin.get('price_change_percentage_24h') is not None]
            
            gainers = sorted(valid_coins, 
                           key=lambda x: x.get('price_change_percentage_24h', 0), 
                           reverse=True)[:limit]
            
            losers = sorted(valid_coins, 
                          key=lambda x: x.get('price_change_percentage_24h', 0))[:limit]
            
            return {
                'gainers': gainers,
                'losers': losers
            }
            
        except Exception as e:
            print(f"Error fetching gainers/losers: {e}")
            return {'gainers': [], 'losers': []}
    
    def get_new_listings(self) -> List[Dict]:
        """Get recently listed coins (simulated - CoinGecko doesn't have a direct endpoint)"""
        try:
            # Get coins and filter by recent addition (approximate)
            url = f"{self.coingecko_base_url}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',  # Changed to more reliable ordering
                'per_page': 50,
                'page': 1,
                'sparkline': False
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            coins = response.json()
            
            # Filter for smaller market caps (often newer coins) with valid data
            new_coins = [coin for coin in coins 
                        if coin.get('market_cap_rank') and 
                        coin.get('market_cap_rank') > 200 and
                        coin.get('market_cap_rank') < 1000]  # Reasonable range
            
            return new_coins[:10]
            
        except requests.RequestException as e:
            print(f"Error fetching new listings: {e}")
            return []
    
    def calculate_attractiveness_score(self, coin_data: Dict) -> float:
        """Calculate attractiveness score based on various metrics"""
        score = 5.0  # Base score
        
        # Market cap ranking bonus (lower rank = higher score)
        rank = coin_data.get('market_cap_rank')
        if rank:
            if rank <= 10:
                score += 2.0
            elif rank <= 50:
                score += 1.5
            elif rank <= 100:
                score += 1.0
            elif rank <= 500:
                score += 0.5
        
        # Price change bonus/penalty
        price_change = coin_data.get('price_change_percentage_24h', 0)
        if price_change > 10:
            score += 1.5
        elif price_change > 5:
            score += 1.0
        elif price_change > 0:
            score += 0.5
        elif price_change < -10:
            score -= 1.5
        elif price_change < -5:
            score -= 1.0
        
        # Volume/Market cap ratio (liquidity indicator)
        market_cap = coin_data.get('market_cap', 0)
        volume = coin_data.get('total_volume', 0)
        if market_cap > 0:
            volume_ratio = volume / market_cap
            if volume_ratio > 0.1:  # High trading activity
                score += 1.0
            elif volume_ratio > 0.05:
                score += 0.5
        
        # Ensure score is within bounds
        return max(1.0, min(10.0, score))
    
    def generate_investment_highlights(self, coin_data: Dict) -> List[str]:
        """Generate investment highlights based on coin data"""
        highlights = []
        
        # Market cap ranking
        rank = coin_data.get('market_cap_rank')
        if rank and rank <= 10:
            highlights.append("Top 10 cryptocurrency")
        elif rank and rank <= 50:
            highlights.append("Top 50 market cap")
        elif rank and rank <= 100:
            highlights.append("Established project")
        
        # Price performance
        price_change = coin_data.get('price_change_percentage_24h', 0)
        if price_change > 20:
            highlights.append("Massive 24h gains")
        elif price_change > 10:
            highlights.append("Strong upward momentum")
        elif price_change > 5:
            highlights.append("Positive momentum")
        
        # Volume
        volume = coin_data.get('total_volume', 0)
        if volume > 1_000_000_000:  # $1B+ volume
            highlights.append("High liquidity")
        elif volume > 100_000_000:  # $100M+ volume
            highlights.append("Good liquidity")
        
        # Market cap
        market_cap = coin_data.get('market_cap', 0)
        if market_cap > 10_000_000_000:  # $10B+
            highlights.append("Large cap stability")
        elif market_cap < 100_000_000:  # Under $100M
            highlights.append("High growth potential")
        
        # Default highlights if none found
        if not highlights:
            highlights = ["Active trading", "Market opportunity"]
        
        return highlights[:3]  # Limit to 3 highlights
    
    def convert_to_coin_objects(self, coins_data: List[Dict], status: CoinStatus = CoinStatus.CURRENT) -> List[Coin]:
        """Convert API data to Coin objects"""
        coins = []
        
        for coin_data in coins_data:
            try:
                # Determine risk level based on market cap rank
                rank = coin_data.get('market_cap_rank')
                if rank and rank <= 20:
                    risk_level = RiskLevel.LOW
                elif rank and rank <= 100:
                    risk_level = RiskLevel.MEDIUM
                else:
                    risk_level = RiskLevel.HIGH
                
                coin = Coin(
                    id=coin_data.get('id', ''),
                    name=coin_data.get('name', ''),
                    symbol=coin_data.get('symbol', '').upper(),
                    status=status,
                    attractiveness_score=self.calculate_attractiveness_score(coin_data),
                    investment_highlights=self.generate_investment_highlights(coin_data),
                    market_cap_rank=coin_data.get('market_cap_rank'),
                    price=coin_data.get('current_price'),
                    price_btc=coin_data.get('price_btc'),
                    price_change_24h_usd=coin_data.get('price_change_percentage_24h'),
                    market_cap=f"${coin_data.get('market_cap', 0):,.0f}" if coin_data.get('market_cap') else None,
                    total_volume=f"${coin_data.get('total_volume', 0):,.0f}" if coin_data.get('total_volume') else None,
                    risk_level=risk_level
                )
                coins.append(coin)
            except Exception as e:
                print(f"Warning: Error processing coin {coin_data.get('id', 'unknown')}: {e}")
                continue
        
        return coins
    
    def fetch_live_data(self) -> Dict[str, List[Coin]]:
        """Fetch comprehensive live cryptocurrency data"""
        print("🔄 Fetching live cryptocurrency data...")
        
        # Add small delays to respect API rate limits
        time.sleep(0.5)
        
        # Get different categories of coins
        top_coins_data = self.get_top_coins_by_market_cap(20)
        time.sleep(1)
        
        trending_data = self.get_trending_coins(10)
        time.sleep(1)
        
        gainers_losers = self.get_gainers_and_losers(10)
        time.sleep(1)
        
        new_listings_data = self.get_new_listings()
        
        # Convert to Coin objects
        top_coins = self.convert_to_coin_objects(top_coins_data, CoinStatus.CURRENT)
        trending_coins = self.convert_to_coin_objects(trending_data, CoinStatus.CURRENT)
        gainers = self.convert_to_coin_objects(gainers_losers['gainers'], CoinStatus.CURRENT)
        new_coins = self.convert_to_coin_objects(new_listings_data, CoinStatus.NEW)
        
        return {
            'top_coins': top_coins,
            'trending': trending_coins,
            'gainers': gainers,
            'new_coins': new_coins,
            'all_coins': top_coins + new_coins  # Combine for analysis
        }
    
    def save_to_json(self, data: Dict[str, List[Coin]], filename: str = "live_api.json") -> None:
        """Save fetched data to JSON file"""
        try:
            # Convert Coin objects to dictionaries
            json_data = {"coins": []}
            
            for coin in data['all_coins']:
                coin_dict = {
                    "item": {
                        "id": coin.id,
                        "name": coin.name,
                        "symbol": coin.symbol,
                        "status": coin.status.value,
                        "attractiveness_score": coin.attractiveness_score,
                        "investment_highlights": coin.investment_highlights,
                        "market_cap_rank": coin.market_cap_rank,
                        "price_btc": coin.price_btc,
                        "risk_level": coin.risk_level.value if coin.risk_level else None,
                        "data": {
                            "price": coin.price,
                            "price_btc": str(coin.price_btc) if coin.price_btc else None,
                            "price_change_percentage_24h": {
                                "usd": coin.price_change_24h_usd
                            } if coin.price_change_24h_usd else None,
                            "market_cap": coin.market_cap,
                            "total_volume": coin.total_volume,
                            "content": None
                        }
                    }
                }
                json_data["coins"].append(coin_dict)
            
            with open(filename, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            print(f"✅ Live data saved to {filename}")
            
        except Exception as e:
            print(f"❌ Error saving data: {e}")


def fetch_and_update_data():
    """Main function to fetch live data and update the application"""
    fetcher = LiveDataFetcher()
    
    try:
        live_data = fetcher.fetch_live_data()
        
        print(f"\n📊 Successfully fetched live data:")
        print(f"• Top Coins: {len(live_data['top_coins'])}")
        print(f"• Trending: {len(live_data['trending'])}")
        print(f"• Gainers: {len(live_data['gainers'])}")
        print(f"• New Coins: {len(live_data['new_coins'])}")
        print(f"• Total: {len(live_data['all_coins'])}")
        
        # Save to both files
        fetcher.save_to_json(live_data, "live_api.json")
        fetcher.save_to_json(live_data, "api.json")  # Update main data file
        
        return live_data
        
    except Exception as e:
        print(f"❌ Error fetching live data: {e}")
        return None


if __name__ == "__main__":
    fetch_and_update_data()
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
                'per_page': 250,  # Get more coins to filter from
                'page': 1,
                'sparkline': False,
                'price_change_percentage': '24h'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            all_coins = response.json()
            
            # Filter for low cap coins (rank 100+ and market cap under $1B)
            low_cap_coins = [
                coin for coin in all_coins 
                if coin.get('market_cap_rank') and 
                coin.get('market_cap_rank') >= 100 and
                coin.get('market_cap') and 
                coin.get('market_cap') < 1_000_000_000  # Under $1 billion market cap
            ]
            
            return low_cap_coins[:limit]
            
        except requests.RequestException as e:
            print(f"Error fetching low cap coins: {e}")
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
        """Get recently listed coins with low market caps"""
        try:
            # Get coins and filter by recent addition (approximate)
            url = f"{self.coingecko_base_url}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 250,
                'page': 2,  # Get coins from page 2 for smaller caps
                'sparkline': False
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            coins = response.json()
            
            # Filter for very small market caps (potential gems)
            small_cap_coins = [coin for coin in coins 
                             if coin.get('market_cap_rank') and 
                             coin.get('market_cap_rank') > 300 and
                             coin.get('market_cap') and
                             coin.get('market_cap') < 100_000_000]  # Under $100M market cap
            
            return small_cap_coins[:15]
            
        except requests.RequestException as e:
            print(f"Error fetching small cap coins: {e}")
            return []
    
    def calculate_attractiveness_score(self, coin_data: Dict) -> float:
        """Calculate attractiveness score based on various metrics (optimized for low cap coins)"""
        score = 5.0  # Base score
        
        # Market cap ranking bonus (adjusted for low cap preference)
        rank = coin_data.get('market_cap_rank')
        market_cap = coin_data.get('market_cap', 0)
        
        # Reward smaller market caps more
        if market_cap < 10_000_000:  # Under $10M - micro cap gems
            score += 2.5
        elif market_cap < 50_000_000:  # Under $50M - small cap potential
            score += 2.0
        elif market_cap < 100_000_000:  # Under $100M - low cap
            score += 1.5
        elif market_cap < 500_000_000:  # Under $500M - mid-small cap
            score += 1.0
        elif market_cap < 1_000_000_000:  # Under $1B - still decent
            score += 0.5
        
        # Price change bonus/penalty (more aggressive for low caps)
        price_change = coin_data.get('price_change_percentage_24h', 0)
        if price_change > 20:
            score += 2.0  # Major pump
        elif price_change > 10:
            score += 1.5
        elif price_change > 5:
            score += 1.0
        elif price_change > 0:
            score += 0.5
        elif price_change < -20:
            score -= 2.0  # Major dump
        elif price_change < -10:
            score -= 1.5
        elif price_change < -5:
            score -= 1.0
        
        # Volume/Market cap ratio (liquidity indicator) - crucial for low caps
        if market_cap > 0:
            volume = coin_data.get('total_volume', 0)
            volume_ratio = volume / market_cap
            if volume_ratio > 0.5:  # Very high trading activity
                score += 1.5
            elif volume_ratio > 0.2:  # High trading activity
                score += 1.0
            elif volume_ratio > 0.1:
                score += 0.5
            elif volume_ratio < 0.01:  # Very low liquidity - risky
                score -= 1.0
        
        # Ensure score is within bounds
        return max(1.0, min(10.0, score))
    
    def generate_investment_highlights(self, coin_data: Dict) -> List[str]:
        """Generate investment highlights based on coin data (optimized for low caps)"""
        highlights = []
        
        # Market cap analysis
        market_cap = coin_data.get('market_cap', 0)
        if market_cap < 10_000_000:  # Under $10M
            highlights.append("Micro cap gem")
        elif market_cap < 50_000_000:  # Under $50M
            highlights.append("Small cap potential")
        elif market_cap < 100_000_000:  # Under $100M
            highlights.append("Low cap opportunity")
        elif market_cap < 500_000_000:  # Under $500M
            highlights.append("Mid-small cap")
        
        # Price performance
        price_change = coin_data.get('price_change_percentage_24h', 0)
        if price_change > 50:
            highlights.append("Explosive growth")
        elif price_change > 20:
            highlights.append("Strong momentum")
        elif price_change > 10:
            highlights.append("Good uptrend")
        elif price_change > 5:
            highlights.append("Positive movement")
        elif price_change < -20:
            highlights.append("Major dip opportunity")
        elif price_change < -10:
            highlights.append("Potential buy the dip")
        
        # Volume analysis
        volume = coin_data.get('total_volume', 0)
        if market_cap > 0:
            volume_ratio = volume / market_cap
            if volume_ratio > 0.5:
                highlights.append("High trading volume")
            elif volume_ratio > 0.2:
                highlights.append("Active trading")
            elif volume_ratio < 0.01:
                highlights.append("Low liquidity risk")
        
        # Volume thresholds
        if volume > 10_000_000:  # $10M+ volume
            highlights.append("Good liquidity")
        elif volume > 1_000_000:  # $1M+ volume
            highlights.append("Decent volume")
        elif volume < 100_000:  # Under $100K volume
            highlights.append("Low volume")
        
        # Default highlights if none found
        if not highlights:
            highlights = ["Low cap coin", "High risk/reward"]
        
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
        
        # Get different categories of low cap coins
        low_cap_coins_data = self.get_top_coins_by_market_cap(25)
        time.sleep(1)
        
        trending_data = self.get_trending_coins(10)
        time.sleep(1)
        
        gainers_losers = self.get_gainers_and_losers(10)
        time.sleep(1)
        
        small_cap_data = self.get_new_listings()
        
        # Convert to Coin objects
        low_cap_coins = self.convert_to_coin_objects(low_cap_coins_data, CoinStatus.CURRENT)
        trending_coins = self.convert_to_coin_objects(trending_data, CoinStatus.CURRENT)
        gainers = self.convert_to_coin_objects(gainers_losers['gainers'], CoinStatus.CURRENT)
        small_caps = self.convert_to_coin_objects(small_cap_data, CoinStatus.NEW)
        
        # Combine all low cap coins
        all_low_caps = low_cap_coins + small_caps
        
        return {
            'top_coins': low_cap_coins,
            'trending': trending_coins,
            'gainers': gainers,
            'new_coins': small_caps,
            'all_coins': all_low_caps  # Focus on low cap opportunities
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
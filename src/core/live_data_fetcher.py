import requests
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from .crypto_analyzer import Coin, CoinStatus, RiskLevel
from .config import Config

class LiveDataFetcher:
    """Fetches live cryptocurrency data from APIs with secure authentication"""
    
    def __init__(self):
        # Validate configuration on initialization
        Config.validate()
        
        self.coingecko_base_url = Config.COINGECKO_BASE_URL
        self.coinmarketcap_base_url = Config.COINMARKETCAP_BASE_URL
        
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
            
            low_cap_coins = [
                coin for coin in all_coins 
                if coin.get('market_cap_rank') and 
                coin.get('market_cap_rank') >= 100 and
                coin.get('market_cap') and 
                coin.get('market_cap') < 1_000_000_000  # Under $1 billion market cap
            ]
            
            return low_cap_coins[:10]
            
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
            score += 3.0
        elif market_cap < 50_000_000:  # Under $50M - small cap potential
            score += 2.5
        elif market_cap < 100_000_000:  # Under $100M - low cap
            score += 2.0
        elif market_cap < 500_000_000:  # Under $500M - mid-small cap
            score += 1.5
        elif market_cap < 1_000_000_000:  # Under $1B - still decent
            score += 1.0
        
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
    
    def save_to_json(self, data: Dict[str, List[Coin]], filename: str = "data/live_api.json") -> None:
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

    def save_combined_data(self, data: Dict, filename: str = "data/live_api.json") -> None:
        """Save combined data from multiple sources to JSON file"""
        try:
            # Data is already in the correct format
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✅ Combined data saved to {filename}")
            
        except Exception as e:
            print(f"❌ Error saving combined data: {e}")

    def fetch_coinmarketcap_data(self, limit: int = 50) -> Optional[List[Dict]]:
        """Fetch cryptocurrency data from CoinMarketCap Pro API"""
        try:
            url = f"{self.coinmarketcap_base_url}/cryptocurrency/listings/latest"
            
            params = {
                'start': 1,
                'limit': limit,
                'convert': 'USD',
                'sort': 'market_cap',
                'sort_dir': 'desc'
            }
            
            headers = Config.get_coinmarketcap_headers()
            
            print(f"🔄 Fetching top {limit} coins from CoinMarketCap...")
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status', {}).get('error_code') != 0:
                raise Exception(f"CoinMarketCap API Error: {data.get('status', {}).get('error_message')}")
            
            coins = []
            for coin in data.get('data', []):
                formatted_coin = {
                    'id': coin['slug'],
                    'name': coin['name'],
                    'symbol': coin['symbol'],
                    'market_cap_rank': coin['cmc_rank'],
                    'price': coin['quote']['USD']['price'],
                    'price_change_24h': coin['quote']['USD']['percent_change_24h'],
                    'market_cap': coin['quote']['USD']['market_cap'],
                    'volume_24h': coin['quote']['USD']['volume_24h'],
                    'circulating_supply': coin.get('circulating_supply'),
                    'max_supply': coin.get('max_supply'),
                    'last_updated': coin['quote']['USD']['last_updated']
                }
                coins.append(formatted_coin)
            
            print(f"✅ Successfully fetched {len(coins)} coins from CoinMarketCap")
            return coins
            
        except requests.exceptions.RequestException as e:
            print(f"❌ CoinMarketCap API request failed: {e}")
            return None
        except Exception as e:
            print(f"❌ CoinMarketCap API error: {e}")
            return None


def calculate_attractiveness_score(coin: Dict) -> float:
    """Calculate attractiveness score for a coin based on various factors"""
    score = 5.0  # Base score
    
    # Market cap rank factor (lower rank = higher score)
    rank = coin.get('market_cap_rank', 1000)
    if rank <= 10:
        score += 2.0
    elif rank <= 50:
        score += 1.5
    elif rank <= 100:
        score += 1.0
    elif rank <= 200:
        score += 0.5
    
    # Price change factor
    price_change = coin.get('price_change_24h', 0)
    if price_change > 10:
        score += 1.0
    elif price_change > 5:
        score += 0.5
    elif price_change < -10:
        score -= 1.0
    elif price_change < -5:
        score -= 0.5
    
    # Volume factor (higher volume = more liquid)
    volume = coin.get('volume_24h', 0)
    if volume > 1000000000:  # > $1B
        score += 0.5
    elif volume > 100000000:  # > $100M
        score += 0.3
    
    return min(10.0, max(1.0, score))


def generate_highlights(coin: Dict) -> List[str]:
    """Generate investment highlights for a coin"""
    highlights = []
    
    rank = coin.get('market_cap_rank', 1000)
    price_change = coin.get('price_change_24h', 0)
    volume = coin.get('volume_24h', 0)
    
    if rank <= 10:
        highlights.append("Top 10 cryptocurrency")
    elif rank <= 50:
        highlights.append("Established market position")
    elif rank <= 200:
        highlights.append("Growing market presence")
    else:
        highlights.append("Low cap opportunity")
    
    if price_change > 10:
        highlights.append("Strong 24h momentum")
    elif price_change > 5:
        highlights.append("Positive price action")
    elif price_change < -10:
        highlights.append("Potential buying opportunity")
    
    if volume > 1000000000:
        highlights.append("High liquidity")
    elif volume > 100000000:
        highlights.append("Good trading volume")
    
    return highlights


def assess_risk_level(coin: Dict) -> str:
    """Assess risk level based on market cap and volatility"""
    rank = coin.get('market_cap_rank', 1000)
    price_change = abs(coin.get('price_change_24h', 0))
    
    if rank <= 20 and price_change < 5:
        return "low"
    elif rank <= 100 and price_change < 10:
        return "medium"
    else:
        return "high"


def fetch_and_update_data():
    """Main function to fetch live data from multiple sources and combine them"""
    fetcher = LiveDataFetcher()
    
    try:
        print("🚀 Fetching live cryptocurrency data from multiple sources...")
        
        # Fetch from CoinMarketCap (primary source)
        cmc_data = fetcher.fetch_coinmarketcap_data(limit=200)
        
        # Fetch additional data from CoinGecko
        coingecko_data = fetcher.fetch_live_data()
        
        # Combine and format data
        formatted_data = {
            "last_updated": datetime.now().isoformat(),
            "sources": ["coinmarketcap", "coingecko"],
            "coins": []
        }
        
        # Process CoinMarketCap data (primary source)
        cmc_coins = {}
        if cmc_data:
            print(f"✅ CoinMarketCap: {len(cmc_data)} coins")
            for coin in cmc_data:
                score = calculate_attractiveness_score(coin)
                
                formatted_coin = {
                    "item": {
                        "id": coin['id'],
                        "name": coin['name'],
                        "symbol": coin['symbol'],
                        "status": "current",
                        "attractiveness_score": score,
                        "investment_highlights": generate_highlights(coin),
                        "risk_level": assess_risk_level(coin),
                        "market_cap_rank": coin['market_cap_rank'],
                        "price_btc": None,
                        "data": {
                            "price": coin['price'],
                            "price_btc": None,
                            "price_change_percentage_24h": {
                                "usd": coin['price_change_24h']
                            },
                            "market_cap": f"${coin['market_cap']:,.0f}",
                            "total_volume": f"${coin['volume_24h']:,.0f}",
                            "content": None,
                            "source": "coinmarketcap"
                        }
                    }
                }
                cmc_coins[coin['symbol']] = formatted_coin
                formatted_data["coins"].append(formatted_coin)
        
        # Add CoinGecko data for additional coins and enhanced info
        if coingecko_data and 'all_coins' in coingecko_data:
            print(f"✅ CoinGecko: {len(coingecko_data['all_coins'])} additional coins")
            
            for coin in coingecko_data['all_coins']:
                symbol = coin.symbol.upper()
                
                # If coin already exists from CoinMarketCap, enhance with CoinGecko data
                if symbol in cmc_coins:
                    # Add CoinGecko specific data
                    existing_coin = cmc_coins[symbol]
                    existing_coin["item"]["data"]["coingecko_rank"] = coin.market_cap_rank
                    existing_coin["item"]["data"]["additional_source"] = "coingecko"
                
                else:
                    # Add new coin from CoinGecko
                    score = calculate_attractiveness_score({
                        'market_cap_rank': coin.market_cap_rank or 1000,
                        'price_change_24h': coin.price_change_24h_usd or 0,
                        'volume_24h': 0,  # CoinGecko format may differ
                        'price': coin.price or 0
                    })
                    
                    formatted_coin = {
                        "item": {
                            "id": coin.id,
                            "name": coin.name,
                            "symbol": coin.symbol,
                            "status": getattr(coin.status, 'value', 'current') if hasattr(coin, 'status') and coin.status else "current",
                            "attractiveness_score": score,
                            "investment_highlights": coin.investment_highlights or [],
                            "risk_level": getattr(coin.risk_level, 'value', 'medium') if hasattr(coin, 'risk_level') and coin.risk_level else "medium",
                            "market_cap_rank": coin.market_cap_rank,
                            "price_btc": coin.price_btc,
                            "data": {
                                "price": coin.price,
                                "price_btc": coin.price_btc,
                                "price_change_percentage_24h": {
                                    "usd": coin.price_change_24h_usd or 0
                                },
                                "market_cap": coin.market_cap or "N/A",
                                "total_volume": "N/A",
                                "content": None,
                                "source": "coingecko"
                            }
                        }
                    }
                    formatted_data["coins"].append(formatted_coin)
        
        # Sort by attractiveness score
        formatted_data["coins"].sort(
            key=lambda x: x["item"]["attractiveness_score"], 
            reverse=True
        )
        formatted_data["coins"] = formatted_data["coins"][:10]  # Limit to top 10
        
        # Save combined data
        fetcher.save_combined_data(formatted_data, "data/live_api.json")
        
        total_coins = len(formatted_data["coins"])
        cmc_count = len(cmc_data) if cmc_data else 0
        cg_count = total_coins - cmc_count
        
        print(f"🎉 Successfully combined data:")
        print(f"  • CoinMarketCap: {cmc_count} coins")
        print(f"  • CoinGecko: {cg_count} additional coins") 
        print(f"  • Total: {total_coins} coins")
        print(f"  • Sources: {', '.join(formatted_data['sources'])}")
        
        return formatted_data
        
    except Exception as e:
        print(f"❌ Error fetching combined data: {e}")
        
        # Fallback to CoinGecko only
        try:
            print("⚠️  Trying CoinGecko fallback...")
            live_data = fetcher.fetch_live_data()
            
            if live_data:
                print(f"📊 CoinGecko fallback successful:")
                print(f"• Total: {len(live_data.get('all_coins', []))}")
                
                # Save to live data file
                fetcher.save_to_json(live_data, "data/live_api.json")
                return live_data
            else:
                print("❌ All data sources failed")
                return None
                
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            return None


if __name__ == "__main__":
    fetch_and_update_data()
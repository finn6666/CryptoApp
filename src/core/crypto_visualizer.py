"""
Simple ASCII-based data visualization for cryptocurrency analysis
"""

from typing import List
from .crypto_analyzer import Coin

class CryptoVisualizer:
    """Simple ASCII charts for crypto data"""
    
    @staticmethod
    def create_score_chart(coins: List[Coin], max_width: int = 50) -> str:
        """Create a horizontal bar chart of attractiveness scores"""
        if not coins:
            return "No data available"
        
        chart_lines = []
        chart_lines.append("📊 ATTRACTIVENESS SCORE CHART")
        chart_lines.append("=" * (max_width + 20))
        
        # Find max score for scaling
        max_score = max(coin.attractiveness_score for coin in coins)
        
        for coin in coins:
            score = coin.attractiveness_score
            bar_length = int((score / max_score) * max_width)
            
            # Create color-coded bars using different characters
            if score >= 9.0:
                bar_char = "█"  # Solid block for highest scores
            elif score >= 8.0:
                bar_char = "▓"  # Medium block
            elif score >= 7.0:
                bar_char = "▒"  # Light block
            else:
                bar_char = "░"  # Very light block
            
            bar = bar_char * bar_length
            
            # Format the line
            line = f"{coin.symbol:>6} │{bar:<{max_width}} │ {score:.1f}"
            chart_lines.append(line)
        
        chart_lines.append("=" * (max_width + 20))
        return "\n".join(chart_lines)
    
    @staticmethod
    def create_price_change_chart(coins: List[Coin], max_width: int = 40) -> str:
        """Create a chart showing 24h price changes"""
        # Filter coins with price change data
        coins_with_change = [coin for coin in coins if coin.price_change_24h_usd is not None]
        
        if not coins_with_change:
            return "No price change data available"
        
        chart_lines = []
        chart_lines.append("📈 24-HOUR PRICE CHANGES")
        chart_lines.append("=" * (max_width + 25))
        
        # Find max absolute change for scaling
        changes = [abs(coin.price_change_24h_usd) for coin in coins_with_change if coin.price_change_24h_usd is not None]
        max_change = max(changes) if changes else 1.0
        
        for coin in coins_with_change:
            change = coin.price_change_24h_usd
            if change is None:
                continue
                
            # Calculate bar length and direction
            if change >= 0:
                bar_length = int((change / max_change) * max_width) if max_change > 0 else 0
                bar = "+" + ("█" * bar_length)
                change_str = f"+{change:.1f}%"
            else:
                bar_length = int((abs(change) / max_change) * max_width) if max_change > 0 else 0
                bar = "-" + ("█" * bar_length)
                change_str = f"{change:.1f}%"
            
            # Format the line
            line = f"{coin.symbol:>6} │{bar:<{max_width + 1}} │ {change_str:>8}"
            chart_lines.append(line)
        
        chart_lines.append("=" * (max_width + 25))
        return "\n".join(chart_lines)
    
    @staticmethod
    def create_status_distribution(coins: List[Coin]) -> str:
        """Create a simple distribution chart of coin statuses"""
        from collections import Counter
        
        status_counts = Counter(coin.status.value for coin in coins)
        
        chart_lines = []
        chart_lines.append("📋 COIN STATUS DISTRIBUTION")
        chart_lines.append("=" * 35)
        
        total = len(coins)
        for status, count in status_counts.items():
            percentage = (count / total) * 100 if total > 0 else 0
            bar_length = int(percentage / 5)  # Scale to 20 chars max
            bar = "█" * bar_length
            
            line = f"{status.title():>10} │{bar:<20} │ {count:>2} ({percentage:.1f}%)"
            chart_lines.append(line)
        
        chart_lines.append("=" * 35)
        return "\n".join(chart_lines)
    
    @staticmethod
    def create_market_cap_ranking(coins: List[Coin]) -> str:
        """Create a chart showing market cap rankings"""
        # Filter coins with market cap rank
        ranked_coins = [coin for coin in coins if coin.market_cap_rank is not None]
        ranked_coins.sort(key=lambda x: x.market_cap_rank or 9999)  # Handle None values
        
        if not ranked_coins:
            return "No market cap ranking data available"
        
        chart_lines = []
        chart_lines.append("🏆 MARKET CAP RANKINGS")
        chart_lines.append("=" * 40)
        
        for coin in ranked_coins:
            rank = coin.market_cap_rank
            if rank is None:
                continue
                
            # Visual representation of ranking (lower rank = better)
            if rank <= 5:
                rank_visual = "🥇" * (6 - rank)
            elif rank <= 10:
                rank_visual = "🥈" * 3
            elif rank <= 20:
                rank_visual = "🥉" * 2
            else:
                rank_visual = "📊"
            
            line = f"#{rank:>3} │ {coin.symbol:>6} │ {rank_visual} │ {coin.name}"
            chart_lines.append(line)
        
        chart_lines.append("=" * 40)
        return "\n".join(chart_lines)
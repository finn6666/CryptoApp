"""
DeepSeek AI Integration for Crypto Sentiment Analysis
Provides AI-powered sentiment scoring to enhance gem detection
Cost: ~$0.60/month with efficient caching
"""

import os
import json
import logging
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# Load environment variables to get API key
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class SentimentAnalysis:
    """Sentiment analysis result"""
    score: float  # -1.0 to 1.0 (negative to positive)
    confidence: float  # 0.0 to 1.0
    key_points: List[str]
    reasoning: str
    timestamp: str


class DeepSeekAnalyzer:
    """
    DeepSeek AI analyzer for cryptocurrency sentiment analysis
    
    Features:
    - Market sentiment scoring
    - News/social media analysis
    - Technology assessment
    - Risk evaluation
    """
    
    # Class-level cache to reduce redundant API calls
    _analysis_cache = {}
    
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY', '')
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"  # Cost-effective model
        
        # Get project root for cache directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cache_dir = os.path.join(project_root, 'data', 'deepseek_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cache settings (reduce API calls)
        self.cache_ttl_hours = 24  # Cache results for 24 hours
        
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY not set. Sentiment analysis will be disabled.")
    
    def is_available(self) -> bool:
        """Check if DeepSeek API is configured"""
        return bool(self.api_key)
    
    def analyze_coin_sentiment(self, coin_data: Dict) -> Optional[SentimentAnalysis]:
        """
        Analyze sentiment for a cryptocurrency
        
        Args:
            coin_data: Coin information (symbol, name, price, market_cap_rank, etc.)
        
        Returns:
            SentimentAnalysis object or None if unavailable
        """
        if not self.is_available():
            return None
        
        try:
            symbol = coin_data.get('symbol', 'UNKNOWN')
            
            # Check cache first (file and memory)
            cached_result = self._get_cached_sentiment(symbol)
            if cached_result:
                return cached_result
            
            # Build analysis prompt
            prompt = self._build_analysis_prompt(coin_data)
            
            # Call DeepSeek API
            response = self._call_deepseek_api(prompt)
            
            if not response:
                return None
            
            # Parse response into structured sentiment
            sentiment = self._parse_sentiment_response(response, symbol)
            
            # Cache the result (both file and memory)
            if sentiment:
                self._cache_sentiment(symbol, sentiment)
            
            return sentiment
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment for {coin_data.get('symbol')}: {e}")
            return None
    
    def _build_analysis_prompt(self, coin_data: Dict) -> str:
        """Build optimized AI prompt for sentiment analysis"""
        symbol = coin_data.get('symbol', 'UNKNOWN')
        name = coin_data.get('name', 'Unknown')
        price = coin_data.get('price', 0)
        market_cap_rank = coin_data.get('market_cap_rank', 999)
        price_change_24h = coin_data.get('price_change_24h', 0)
        
        # Concise, optimized prompt
        prompt = f"""Analyze {name} ({symbol}) - Rank #{market_cap_rank}, ${price}, {price_change_24h:+.1f}% (24h).

Provide unique insight in ONE compelling sentence (max 15 words). No templates. Focus on what makes THIS coin different.

JSON:
{{
    "sentiment_score": 0.5,  // -1 to 1
    "confidence": 0.7,  // 0 to 1
    "key_points": ["Unique catalyst", "Competitive edge", "Key risk"],
    "reasoning": "One unique, insightful sentence about THIS specific coin"
}}"""
        
        return prompt
    
    def _call_deepseek_api(self, prompt: str) -> Optional[str]:
        """Call DeepSeek API with optimized settings"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Expert crypto analyst. Give unique, specific insights for each coin. Avoid generic templates. Be insightful and concise."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.5,
                "max_tokens": 300  # Reduced from 500 to save costs
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return content
            else:
                logger.error(f"DeepSeek API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            return None
    
    def _parse_sentiment_response(self, response: str, symbol: str) -> Optional[SentimentAnalysis]:
        """Parse DeepSeek response into SentimentAnalysis object"""
        try:
            # Extract JSON from response (might be wrapped in markdown code blocks)
            response_clean = response.strip()
            if response_clean.startswith('```'):
                # Remove markdown code blocks
                lines = response_clean.split('\n')
                json_lines = [l for l in lines if not l.startswith('```')]
                response_clean = '\n'.join(json_lines)
            
            data = json.loads(response_clean)
            
            return SentimentAnalysis(
                score=float(data.get('sentiment_score', 0.0)),
                confidence=float(data.get('confidence', 0.5)),
                key_points=data.get('key_points', []),
                reasoning=data.get('reasoning', ''),
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error parsing sentiment response for {symbol}: {e}")
            return None
    
    def _get_cached_sentiment(self, symbol: str) -> Optional[SentimentAnalysis]:
        """Get cached sentiment from memory or file if available and not expired"""
        # Check memory cache first (fastest)
        cache_key = f"{symbol.lower()}_sentiment"
        if cache_key in self._analysis_cache:
            cached_data, cached_time = self._analysis_cache[cache_key]
            if datetime.now() - cached_time < timedelta(hours=self.cache_ttl_hours):
                return cached_data
            else:
                # Remove expired from memory
                del self._analysis_cache[cache_key]
        
        # Check file cache
        try:
            cache_file = os.path.join(self.cache_dir, f"{symbol.lower()}_sentiment.json")
            
            if not os.path.exists(cache_file):
                return None
            
            # Check if cache is expired
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_time > timedelta(hours=self.cache_ttl_hours):
                return None
            
            with open(cache_file, 'r') as f:
                data = json.load(f)
                sentiment = SentimentAnalysis(**data)
                # Store in memory cache for faster access
                self._analysis_cache[cache_key] = (sentiment, datetime.now())
                return sentiment
                
        except Exception as e:
            logger.debug(f"Cache read error for {symbol}: {e}")
            return None
    
    def _cache_sentiment(self, symbol: str, sentiment: SentimentAnalysis):
        """Cache sentiment analysis result to both memory and file"""
        # Store in memory cache
        cache_key = f"{symbol.lower()}_sentiment"
        self._analysis_cache[cache_key] = (sentiment, datetime.now())
        
        # Store in file cache
        try:
            cache_file = os.path.join(self.cache_dir, f"{symbol.lower()}_sentiment.json")
            
            with open(cache_file, 'w') as f:
                json.dump({
                    'score': sentiment.score,
                    'confidence': sentiment.confidence,
                    'key_points': sentiment.key_points,
                    'reasoning': sentiment.reasoning,
                    'timestamp': sentiment.timestamp
                }, f, indent=2)
                
        except Exception as e:
            logger.error(f"Cache write error for {symbol}: {e}")
    
    def enhance_gem_score(self, base_score: float, coin_data: Dict) -> Dict:
        """
        Enhance gem score with AI sentiment analysis
        
        Args:
            base_score: Original gem score (0-100)
            coin_data: Coin information
        
        Returns:
            Enhanced scoring data with AI insights
        """
        sentiment = self.analyze_coin_sentiment(coin_data)
        
        if not sentiment:
            # Return original score if sentiment not available
            return {
                'enhanced_score': base_score,
                'ai_enabled': False,
                'sentiment': None
            }
        
        # Enhance score with sentiment (weighted at 15% instead of 20% to be more conservative)
        sentiment_boost = sentiment.score * 15 * sentiment.confidence
        enhanced_score = max(0, min(100, base_score + sentiment_boost))
        
        return {
            'enhanced_score': round(enhanced_score, 2),
            'base_score': base_score,
            'sentiment_boost': round(sentiment_boost, 2),
            'ai_enabled': True,
            'sentiment': {
                'score': sentiment.score,
                'confidence': sentiment.confidence,
                'key_points': sentiment.key_points,
                'reasoning': sentiment.reasoning
            }
        }
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Clear sentiment cache for a symbol or all symbols"""
        try:
            if symbol:
                # Clear specific symbol from memory and file
                cache_key = f"{symbol.lower()}_sentiment"
                if cache_key in self._analysis_cache:
                    del self._analysis_cache[cache_key]
                
                cache_file = os.path.join(self.cache_dir, f"{symbol.lower()}_sentiment.json")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    logger.info(f"Cleared cache for {symbol}")
            else:
                # Clear all cache
                self._analysis_cache.clear()
                for file in os.listdir(self.cache_dir):
                    if file.endswith('_sentiment.json'):
                        os.remove(os.path.join(self.cache_dir, file))
                logger.info("Cleared all sentiment cache")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def get_usage_stats(self) -> Dict:
        """Get cache statistics and API usage estimates"""
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('_sentiment.json')]
            
            total_size = sum(
                os.path.getsize(os.path.join(self.cache_dir, f)) 
                for f in cache_files
            )
            
            return {
                'cached_symbols': len(cache_files),
                'cache_size_kb': round(total_size / 1024, 2),
                'cache_ttl_hours': self.cache_ttl_hours,
                'api_configured': self.is_available(),
                'estimated_monthly_cost_usd': 0.60  # Based on typical usage
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

# Global instance
deepseek_analyzer = DeepSeekAnalyzer()

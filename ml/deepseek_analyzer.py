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
from dataclasses import dataclass

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
            logger.debug("DeepSeek API not configured, skipping sentiment analysis")
            return None
        
        try:
            symbol = coin_data.get('symbol', 'UNKNOWN')
            
            # Check cache first
            cached_result = self._get_cached_sentiment(symbol)
            if cached_result:
                logger.debug(f"Using cached sentiment for {symbol}")
                return cached_result
            
            # Build analysis prompt
            prompt = self._build_analysis_prompt(coin_data)
            
            # Call DeepSeek API
            response = self._call_deepseek_api(prompt)
            
            if not response:
                return None
            
            # Parse response into structured sentiment
            sentiment = self._parse_sentiment_response(response, symbol)
            
            # Cache the result
            if sentiment:
                self._cache_sentiment(symbol, sentiment)
            
            return sentiment
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment for {coin_data.get('symbol')}: {e}")
            return None
    
    def _build_analysis_prompt(self, coin_data: Dict) -> str:
        """Build AI prompt for sentiment analysis"""
        symbol = coin_data.get('symbol', 'UNKNOWN')
        name = coin_data.get('name', 'Unknown')
        price = coin_data.get('price', 0)
        market_cap_rank = coin_data.get('market_cap_rank', 999)
        price_change_24h = coin_data.get('price_change_24h', 0)
        
        prompt = f"""Analyze the cryptocurrency {name} ({symbol}) for investment potential.

Current Data:
- Price: ${price}
- Market Cap Rank: #{market_cap_rank}
- 24h Change: {price_change_24h}%

Please provide:
1. Overall Sentiment Score (-1.0 to 1.0, where -1 is very bearish, 0 is neutral, 1 is very bullish)
2. Confidence Level (0.0 to 1.0)
3. Three key points about this coin (technology, adoption, risks)
4. Brief reasoning (2-3 sentences)

Consider:
- Market position and competition
- Technology and use case
- Recent developments
- Risk factors for small-cap cryptos

Respond in JSON format:
{{
    "sentiment_score": 0.5,
    "confidence": 0.7,
    "key_points": ["point1", "point2", "point3"],
    "reasoning": "brief explanation"
}}"""
        
        return prompt
    
    def _call_deepseek_api(self, prompt: str) -> Optional[str]:
        """Call DeepSeek API"""
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
                        "content": "You are a cryptocurrency market analyst. Provide objective, data-driven analysis in JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,  # Lower temperature for more consistent analysis
                "max_tokens": 500  # Keep costs down
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return content
            else:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
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
        """Get cached sentiment if available and not expired"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{symbol.lower()}_sentiment.json")
            
            if not os.path.exists(cache_file):
                return None
            
            # Check if cache is expired
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_time > timedelta(hours=self.cache_ttl_hours):
                logger.debug(f"Cache expired for {symbol}")
                return None
            
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return SentimentAnalysis(**data)
                
        except Exception as e:
            logger.debug(f"Cache read error for {symbol}: {e}")
            return None
    
    def _cache_sentiment(self, symbol: str, sentiment: SentimentAnalysis):
        """Cache sentiment analysis result"""
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
        
        # Enhance score with sentiment
        # Sentiment ranges from -1 to 1, weight it at 20% of total score
        sentiment_boost = sentiment.score * 20 * sentiment.confidence
        enhanced_score = base_score + sentiment_boost
        
        # Clamp to 0-100 range
        enhanced_score = max(0, min(100, enhanced_score))
        
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
                # Clear specific symbol
                cache_file = os.path.join(self.cache_dir, f"{symbol.lower()}_sentiment.json")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    logger.info(f"Cleared cache for {symbol}")
            else:
                # Clear all cache
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

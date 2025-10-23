"""
Configuration management for CryptoApp
Handles API keys and application settings securely
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration with secure API key management"""
    
    # API Keys
    COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
    
    # API URLs
    COINMARKETCAP_BASE_URL = "https://pro-api.coinmarketcap.com/v1"
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
    
    # App Settings
    DEFAULT_COIN_LIMIT = 50
    CACHE_DURATION = 300  # 5 minutes
    REQUEST_TIMEOUT = 30
    
    @classmethod
    def validate(cls):
        """Validate that required API keys are present"""
        if not cls.COINMARKETCAP_API_KEY:
            raise ValueError(
                "COINMARKETCAP_API_KEY not found in environment.\n"
                "Please check your .env file or set the environment variable."
            )
        return True
    
    @classmethod
    def get_coinmarketcap_headers(cls):
        """Get headers for CoinMarketCap API requests"""
        return {
            'X-CMC_PRO_API_KEY': cls.COINMARKETCAP_API_KEY,
            'Accept': 'application/json',
            'Accept-Encoding': 'deflate, gzip'
        }
    
    @classmethod
    def get_coingecko_headers(cls):
        """Get headers for CoinGecko API requests"""
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'CryptoApp/1.0'
        }
        
        if cls.COINGECKO_API_KEY:
            headers['x-cg-pro-api-key'] = cls.COINGECKO_API_KEY
            
        return headers
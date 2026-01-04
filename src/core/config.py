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
    
    # API URLs
    COINMARKETCAP_BASE_URL = "https://pro-api.coinmarketcap.com/v1"
    
    # App Settings
    DEFAULT_COIN_LIMIT = 10
    CACHE_DURATION = 300  # 5 minutes
    REQUEST_TIMEOUT = 30
    
    @classmethod
    def validate(cls):
        """Validate configuration - CoinMarketCap API key required"""
        if not cls.COINMARKETCAP_API_KEY:
            raise ValueError("COINMARKETCAP_API_KEY not found in environment")
        return True
    
    @classmethod
    def get_cmc_headers(cls):
        """Get headers for CoinMarketCap API requests"""
        return {
            'X-CMC_PRO_API_KEY': cls.COINMARKETCAP_API_KEY,
            'Accept': 'application/json'
        }
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
    
    # API Keys (CoinGecko Demo API key is optional — free tier works without it,
    # but a key raises the rate limit from ~10 req/min to 30 req/min)
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', '')
    
    # API URLs
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
    
    # App Settings
    DEFAULT_COIN_LIMIT = 10
    CACHE_DURATION = 300  # 5 minutes
    REQUEST_TIMEOUT = 30
    
    @classmethod
    def validate(cls):
        """Validate configuration — CoinGecko works without a key, so always passes."""
        return True
    
    @classmethod
    def get_coingecko_headers(cls):
        """Get headers for CoinGecko API requests."""
        headers = {'Accept': 'application/json'}
        if cls.COINGECKO_API_KEY:
            headers['x-cg-demo-api-key'] = cls.COINGECKO_API_KEY
        return headers
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
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
    
    # API URLs
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
    
    # App Settings
    DEFAULT_COIN_LIMIT = 10
    CACHE_DURATION = 300  # 5 minutes
    REQUEST_TIMEOUT = 30
    
    @classmethod
    def validate(cls):
        """Validate configuration - CoinGecko API key is optional"""
        return True
    
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
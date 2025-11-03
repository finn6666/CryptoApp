import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MLConfig:
    # Model settings
    model_type: str = "RandomForest"
    n_estimators: int = 100
    test_size: float = 0.2
    random_state: int = 42
    
    # Feature engineering
    rsi_window: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    moving_avg_windows: List[int] = None
    
    # Data requirements
    min_data_points: int = 100
    feature_lookback_hours: int = 720  # 30 days
    
    # Caching
    prediction_cache_ttl: int = 300  # 5 minutes
    redis_url: Optional[str] = None
    
    # API endpoints
    azure_function_url: Optional[str] = None
    crypto_api_base: Optional[str] = None
    
    # Training schedule  
    retrain_schedule: str = "0 2 * * 0"  # Every Sunday at 2 AM - weekly retraining
    
    # Model storage
    model_dir: str = "/Users/finnbryant/Dev/CryptoApp/models"
    data_dir: str = "/Users/finnbryant/Dev/CryptoApp/data"
    
    # Monitoring (optional - for production deployments)
    alert_email: Optional[str] = None
    slack_webhook: Optional[str] = None
    
    def __post_init__(self):
        if self.moving_avg_windows is None:
            self.moving_avg_windows = [7, 30]
        
        # Load from environment variables
        self.redis_url = os.getenv('REDIS_CONNECTION_STRING', self.redis_url)
        self.azure_function_url = os.getenv('ML_FUNCTION_URL', self.azure_function_url)
        self.crypto_api_base = os.getenv('CRYPTO_API_BASE_URL', self.crypto_api_base)
        self.alert_email = os.getenv('ALERT_EMAIL', self.alert_email)
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL', self.slack_webhook)
    
    def validate(self) -> bool:
        """Validate configuration"""
        required_paths = [self.model_dir, self.data_dir]
        
        for path in required_paths:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
        
        return True

# Global config instance
ml_config = MLConfig()

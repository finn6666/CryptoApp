import os
from dataclasses import dataclass
from typing import List, Optional

"""
Type Hints in ML Configuration:

Q: Why use type hints (int, str, List, Optional, etc.) in Python?
A: Type hints are a Python best practice (PEP 484) that provide several benefits:

1. **Code Documentation**: Types make it immediately clear what each parameter expects
   - Example: `n_estimators: int = 100` tells us this is an integer
   - Without types: `n_estimators = 100` - is this an int? float? string?

2. **IDE Support**: Modern IDEs (VS Code, PyCharm) use types for:
   - Autocomplete suggestions
   - Error detection before runtime
   - Better code navigation

3. **Static Analysis**: Tools like mypy can catch type errors before code runs
   - Example: Prevents passing "100" (string) when 100 (int) is expected

4. **ML Best Practice**: Especially important in ML where:
   - Wrong types can cause silent failures (0.2 vs "0.2" in model params)
   - Hyperparameters need specific types
   - Config validation is critical for reproducibility

5. **Dataclasses**: Using @dataclass with types provides:
   - Automatic __init__, __repr__, __eq__ methods
   - Type checking
   - Default values
   - Validation

Example without types (risky):
    config = {"n_estimators": "100"}  # String! Will cause runtime error later

Example with types (safe):
    config = MLConfig(n_estimators="100")  # IDE/mypy catches this immediately!

In production ML systems, type hints are standard practice to prevent bugs
and make code maintainable, especially when multiple people work on the code.
"""

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
    moving_avg_windows: Optional[List[int]] = None  # Optional indicates this can be None
    
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
    
    # Model storage (default paths - will be resolved at runtime)
    model_dir: str = "models"  # Relative to project root
    data_dir: str = "data"     # Relative to project root
    
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

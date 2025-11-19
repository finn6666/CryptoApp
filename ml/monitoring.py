"""
Simplified ML Monitoring for CryptoApp
Basic logging and performance tracking without external services
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class MLMonitor:
    """Simple ML performance monitor for basic logging"""
    
    def __init__(self):
        self.performance_log = []
        self.logger = logging.getLogger(__name__)
        
    def log_prediction(self, symbol: str, prediction: float, actual: Optional[float] = None, 
                      response_time: float = 0, cached: bool = False):
        """Log prediction for basic performance tracking"""
        entry = {
            'timestamp': datetime.utcnow(),
            'symbol': symbol,
            'prediction': prediction,
            'actual': actual,
            'response_time': response_time,
            'cached': cached,
            'error': actual is not None and abs(prediction - actual) > 0.05 if actual else None
        }
        
        self.performance_log.append(entry)
        
        # Keep only last 500 entries for memory efficiency
        if len(self.performance_log) > 500:
            self.performance_log = self.performance_log[-500:]
            
        self.logger.info(f"ML prediction logged for {symbol}: {prediction}")
    
    def get_basic_stats(self, hours: int = 24) -> Dict:
        """Get basic performance statistics"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_logs = [log for log in self.performance_log if log['timestamp'] >= cutoff_time]
        
        if not recent_logs:
            return {"message": "No recent predictions logged"}
        
        total_predictions = len(recent_logs)
        cached_predictions = sum(1 for log in recent_logs if log.get('cached', False))
        avg_response_time = sum(log.get('response_time', 0) for log in recent_logs) / total_predictions
        
        return {
            'total_predictions': total_predictions,
            'cache_hit_rate': cached_predictions / total_predictions if total_predictions > 0 else 0,
            'avg_response_time': round(avg_response_time, 3),
            'period_hours': hours
        }
    
    def log_error(self, error_type: str, error_message: str, symbol: str = None):
        """Log ML-related errors"""
        self.logger.error(f"ML Error [{error_type}] for {symbol or 'N/A'}: {error_message}")

# Global monitor instance
ml_monitor = MLMonitor()

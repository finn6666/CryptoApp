import logging
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
from config.ml_config import ml_config

class MLMonitor:
    def __init__(self):
        self.performance_log = []
        self.alert_thresholds = {
            'prediction_accuracy': 0.6,
            'api_response_time': 5.0,
            'cache_hit_rate': 0.7,
            'error_rate': 0.1
        }
    
    def log_prediction(self, symbol: str, prediction: float, actual: float = None, 
                      response_time: float = 0, cached: bool = False):
        """Log prediction for performance tracking"""
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
        
        # Keep only last 1000 entries
        if len(self.performance_log) > 1000:
            self.performance_log = self.performance_log[-1000:]
    
    def calculate_metrics(self, hours: int = 24) -> Dict:
        """Calculate performance metrics for the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_logs = [log for log in self.performance_log if log['timestamp'] >= cutoff_time]
        
        if not recent_logs:
            return {}
        
        df = pd.DataFrame(recent_logs)
        
        metrics = {
            'total_predictions': len(df),
            'cache_hit_rate': df['cached'].mean() if 'cached' in df else 0,
            'avg_response_time': df['response_time'].mean() if 'response_time' in df else 0,
            'error_rate': 0,
            'accuracy': 0
        }
        
        # Calculate accuracy if we have actual values
        if 'actual' in df and df['actual'].notna().any():
            actual_data = df.dropna(subset=['actual'])
            if len(actual_data) > 0:
                errors = abs(actual_data['prediction'] - actual_data['actual'])
                metrics['accuracy'] = (errors <= 0.05).mean()  # Within 5% considered accurate
                metrics['error_rate'] = (errors > 0.05).mean()
        
        return metrics
    
    def check_alerts(self) -> List[str]:
        """Check if any metrics exceed alert thresholds"""
        metrics = self.calculate_metrics()
        alerts = []
        
        for metric, threshold in self.alert_thresholds.items():
            if metric in metrics:
                value = metrics[metric]
                
                if metric in ['prediction_accuracy', 'cache_hit_rate']:
                    if value < threshold:
                        alerts.append(f"{metric} is {value:.3f}, below threshold {threshold}")
                elif metric in ['api_response_time', 'error_rate']:
                    if value > threshold:
                        alerts.append(f"{metric} is {value:.3f}, above threshold {threshold}")
        
        if alerts:
            self.send_alerts(alerts, metrics)
        
        return alerts
    
    def send_alerts(self, alerts: List[str], metrics: Dict):
        """Send alerts via configured channels"""
        message = f"ML System Alert - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        message += "Issues detected:\n"
        for alert in alerts:
            message += f"• {alert}\n"
        
        message += f"\nCurrent metrics:\n"
        for key, value in metrics.items():
            message += f"• {key}: {value:.3f}\n"
        
        # Send email alert
        if ml_config.alert_email:
            self._send_email_alert(message)
        
        # Send Slack alert
        if ml_config.slack_webhook:
            self._send_slack_alert(message)
        
        logging.error(f"ML Alerts triggered: {alerts}")
    
    def _send_email_alert(self, message: str):
        """Send email alert (placeholder - implement with your email service)"""
        logging.info(f"Email alert would be sent to {ml_config.alert_email}")
        # Implement actual email sending here
    
    def _send_slack_alert(self, message: str):
        """Send Slack alert"""
        try:
            payload = {
                "text": "🚨 CryptoApp ML Alert",
                "attachments": [{
                    "color": "danger",
                    "text": message,
                    "ts": datetime.utcnow().timestamp()
                }]
            }
            
            response = requests.post(ml_config.slack_webhook, json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            logging.error(f"Failed to send Slack alert: {e}")

# Global monitor instance
ml_monitor = MLMonitor()
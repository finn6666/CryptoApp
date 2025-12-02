#!/usr/bin/env python3
"""
Raspberry Pi SIEM-style Monitoring System for CryptoApp
Monitors: Azure VM health, crypto anomalies, ML alerts, system metrics
Optimized for Pi 4GB RAM
"""

import requests
import psutil
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from collections import deque
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('siem_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Alert:
    """Alert data structure"""
    timestamp: datetime
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # SYSTEM, MARKET, ML, SECURITY
    title: str
    description: str
    metric_value: Any = None
    threshold: Any = None
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'metric_value': self.metric_value,
            'threshold': self.threshold
        }

class SIEMMonitor:
    """SIEM-style monitoring for CryptoApp infrastructure"""
    
    def __init__(self, config_path: str = "siem_config.json"):
        self.config = self.load_config(config_path)
        self.alerts = deque(maxlen=1000)  # Keep last 1000 alerts
        self.metrics_history = {
            'vm_health': deque(maxlen=100),
            'api_latency': deque(maxlen=100),
            'market_volumes': deque(maxlen=100),
            'gem_scores': deque(maxlen=100)
        }
        
    def load_config(self, config_path: str) -> Dict:
        """Load monitoring configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config not found at {config_path}, using defaults")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """Default monitoring configuration"""
        return {
            "azure_vm": {
                "url": "http://your-vm-ip:5001",
                "check_interval": 60,  # seconds
                "timeout": 10
            },
            "thresholds": {
                "cpu_percent": 80,
                "memory_percent": 85,
                "disk_percent": 90,
                "api_latency_ms": 5000,
                "gem_score_spike": 15.0,  # Unusual high score
                "volume_spike_multiplier": 5.0  # 5x normal volume
            },
            "alerts": {
                "email_enabled": False,
                "email_to": "",
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_password": ""
            },
            "market_monitoring": {
                "coingecko_api": "https://api.coingecko.com/api/v3",
                "check_interval": 300,  # 5 minutes
                "top_n_coins": 50
            }
        }
    
    def check_vm_health(self) -> Dict[str, Any]:
        """Monitor Azure VM health"""
        vm_url = self.config['azure_vm']['url']
        timeout = self.config['azure_vm']['timeout']
        
        health_data = {
            'status': 'unknown',
            'latency_ms': None,
            'error': None
        }
        
        try:
            start_time = time.time()
            response = requests.get(f"{vm_url}/api/health", timeout=timeout)
            latency_ms = (time.time() - start_time) * 1000
            
            health_data['status'] = 'online' if response.status_code == 200 else 'degraded'
            health_data['latency_ms'] = latency_ms
            
            # Check latency threshold
            if latency_ms > self.config['thresholds']['api_latency_ms']:
                self.create_alert(
                    severity='HIGH',
                    category='SYSTEM',
                    title='High API Latency',
                    description=f'VM response time: {latency_ms:.0f}ms',
                    metric_value=latency_ms,
                    threshold=self.config['thresholds']['api_latency_ms']
                )
            
            # Try to get VM metrics if available
            try:
                metrics_response = requests.get(f"{vm_url}/api/metrics", timeout=timeout)
                if metrics_response.status_code == 200:
                    health_data['vm_metrics'] = metrics_response.json()
            except:
                pass
                
        except requests.exceptions.Timeout:
            health_data['status'] = 'timeout'
            health_data['error'] = 'Request timeout'
            self.create_alert(
                severity='CRITICAL',
                category='SYSTEM',
                title='VM Timeout',
                description=f'Azure VM not responding (timeout: {timeout}s)'
            )
        except requests.exceptions.ConnectionError:
            health_data['status'] = 'offline'
            health_data['error'] = 'Connection failed'
            self.create_alert(
                severity='CRITICAL',
                category='SYSTEM',
                title='VM Offline',
                description='Cannot connect to Azure VM'
            )
        except Exception as e:
            health_data['status'] = 'error'
            health_data['error'] = str(e)
            logger.error(f"VM health check error: {e}")
        
        self.metrics_history['vm_health'].append({
            'timestamp': datetime.now(),
            'data': health_data
        })
        
        return health_data
    
    def check_local_system(self) -> Dict[str, Any]:
        """Monitor Raspberry Pi system resources"""
        thresholds = self.config['thresholds']
        
        system_data = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'temperature': self.get_pi_temperature(),
            'uptime_hours': (time.time() - psutil.boot_time()) / 3600
        }
        
        # Check thresholds and create alerts
        if system_data['cpu_percent'] > thresholds['cpu_percent']:
            self.create_alert(
                severity='MEDIUM',
                category='SYSTEM',
                title='High CPU Usage on Pi',
                description=f"CPU usage: {system_data['cpu_percent']}%",
                metric_value=system_data['cpu_percent'],
                threshold=thresholds['cpu_percent']
            )
        
        if system_data['memory_percent'] > thresholds['memory_percent']:
            self.create_alert(
                severity='HIGH',
                category='SYSTEM',
                title='High Memory Usage on Pi',
                description=f"Memory usage: {system_data['memory_percent']}%",
                metric_value=system_data['memory_percent'],
                threshold=thresholds['memory_percent']
            )
        
        if system_data['disk_percent'] > thresholds['disk_percent']:
            self.create_alert(
                severity='HIGH',
                category='SYSTEM',
                title='High Disk Usage on Pi',
                description=f"Disk usage: {system_data['disk_percent']}%",
                metric_value=system_data['disk_percent'],
                threshold=thresholds['disk_percent']
            )
        
        if system_data['temperature'] and system_data['temperature'] > 70:
            self.create_alert(
                severity='MEDIUM',
                category='SYSTEM',
                title='High Pi Temperature',
                description=f"Temperature: {system_data['temperature']}°C",
                metric_value=system_data['temperature'],
                threshold=70
            )
        
        return system_data
    
    def get_pi_temperature(self) -> float:
        """Get Raspberry Pi CPU temperature"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                return round(temp, 1)
        except:
            return None
    
    def monitor_market_anomalies(self) -> Dict[str, Any]:
        """Detect unusual market activity"""
        vm_url = self.config['azure_vm']['url']
        
        try:
            # Get current coin data from VM
            response = requests.get(f"{vm_url}/api/coins", timeout=10)
            if response.status_code != 200:
                return {'status': 'error', 'message': 'Failed to fetch coin data'}
            
            coins = response.json()
            anomalies = []
            
            for coin in coins[:self.config['market_monitoring']['top_n_coins']]:
                # Check for gem score spikes
                gem_score = coin.get('gem_score', 0)
                if gem_score > self.config['thresholds']['gem_score_spike']:
                    anomalies.append({
                        'type': 'gem_spike',
                        'symbol': coin['symbol'],
                        'gem_score': gem_score
                    })
                    self.create_alert(
                        severity='MEDIUM',
                        category='MARKET',
                        title=f'High Gem Score Detected: {coin["symbol"]}',
                        description=f'Gem score: {gem_score:.2f}',
                        metric_value=gem_score
                    )
                
                # Check for volume anomalies
                volume_24h = coin.get('volume_24h', 0)
                market_cap = coin.get('market_cap', 1)
                volume_ratio = volume_24h / market_cap if market_cap > 0 else 0
                
                if volume_ratio > 1.0:  # Volume exceeds market cap
                    anomalies.append({
                        'type': 'volume_spike',
                        'symbol': coin['symbol'],
                        'volume_ratio': volume_ratio
                    })
                    self.create_alert(
                        severity='HIGH',
                        category='MARKET',
                        title=f'Unusual Volume: {coin["symbol"]}',
                        description=f'Volume/MCap ratio: {volume_ratio:.2f}x',
                        metric_value=volume_ratio
                    )
            
            return {
                'status': 'success',
                'anomalies_found': len(anomalies),
                'anomalies': anomalies
            }
            
        except Exception as e:
            logger.error(f"Market monitoring error: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def create_alert(self, severity: str, category: str, title: str, 
                    description: str, metric_value: Any = None, threshold: Any = None):
        """Create and log an alert"""
        alert = Alert(
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            title=title,
            description=description,
            metric_value=metric_value,
            threshold=threshold
        )
        
        self.alerts.append(alert)
        logger.warning(f"[{severity}] {category}: {title} - {description}")
        
        # Send email if configured and severity is high enough
        if (self.config['alerts']['email_enabled'] and 
            severity in ['CRITICAL', 'HIGH']):
            self.send_email_alert(alert)
    
    def send_email_alert(self, alert: Alert):
        """Send email alert"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['alerts']['smtp_user']
            msg['To'] = self.config['alerts']['email_to']
            msg['Subject'] = f"[{alert.severity}] CryptoApp SIEM Alert: {alert.title}"
            
            body = f"""
CryptoApp SIEM Alert

Severity: {alert.severity}
Category: {alert.category}
Time: {alert.timestamp}

{alert.title}
{alert.description}

Metric Value: {alert.metric_value}
Threshold: {alert.threshold}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(
                self.config['alerts']['smtp_server'],
                self.config['alerts']['smtp_port']
            )
            server.starttls()
            server.login(
                self.config['alerts']['smtp_user'],
                self.config['alerts']['smtp_password']
            )
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent for: {alert.title}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for SIEM dashboard"""
        recent_alerts = [alert.to_dict() for alert in list(self.alerts)[-50:]]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'alerts': {
                'total': len(self.alerts),
                'critical': sum(1 for a in self.alerts if a.severity == 'CRITICAL'),
                'high': sum(1 for a in self.alerts if a.severity == 'HIGH'),
                'medium': sum(1 for a in self.alerts if a.severity == 'MEDIUM'),
                'low': sum(1 for a in self.alerts if a.severity == 'LOW'),
                'recent': recent_alerts
            },
            'system': {
                'pi': self.check_local_system(),
                'vm': list(self.metrics_history['vm_health'])[-1]['data'] 
                      if self.metrics_history['vm_health'] else None
            },
            'uptime': (time.time() - psutil.boot_time()) / 3600
        }
    
    def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        logger.info("Starting monitoring cycle...")
        
        # Check VM health
        vm_health = self.check_vm_health()
        logger.info(f"VM Status: {vm_health['status']}")
        
        # Check local system
        local_system = self.check_local_system()
        logger.info(f"Pi CPU: {local_system['cpu_percent']}%, "
                   f"Memory: {local_system['memory_percent']}%")
        
        # Check market anomalies
        market_status = self.monitor_market_anomalies()
        logger.info(f"Market anomalies: {market_status.get('anomalies_found', 0)}")
        
        logger.info("Monitoring cycle complete\n")
    
    def run_forever(self):
        """Main monitoring loop"""
        logger.info("🚀 CryptoApp SIEM Monitor started")
        logger.info(f"Monitoring VM: {self.config['azure_vm']['url']}")
        logger.info(f"Check interval: {self.config['azure_vm']['check_interval']}s\n")
        
        try:
            while True:
                self.run_monitoring_cycle()
                time.sleep(self.config['azure_vm']['check_interval'])
        except KeyboardInterrupt:
            logger.info("\n👋 SIEM Monitor stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in monitoring loop: {e}")
            raise

def main():
    """Main entry point"""
    monitor = SIEMMonitor()
    monitor.run_forever()

if __name__ == "__main__":
    main()

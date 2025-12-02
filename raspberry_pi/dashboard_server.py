#!/usr/bin/env python3
"""
Flask-based SIEM Dashboard for Raspberry Pi
Lightweight dashboard optimized for 4GB RAM
"""

from flask import Flask, render_template, jsonify
from siem_monitor import SIEMMonitor
import json
import threading
import time
from datetime import datetime

app = Flask(__name__)
monitor = SIEMMonitor()

# Global state
monitoring_active = False
monitor_thread = None

def background_monitoring():
    """Run monitoring in background thread"""
    global monitoring_active
    monitoring_active = True
    
    while monitoring_active:
        try:
            monitor.run_monitoring_cycle()
            time.sleep(monitor.config['azure_vm']['check_interval'])
        except Exception as e:
            print(f"Monitoring error: {e}")
            time.sleep(10)

@app.route('/')
def index():
    """Main SIEM dashboard page"""
    return render_template('siem_dashboard.html')

@app.route('/api/dashboard')
def get_dashboard_data():
    """Get current dashboard data"""
    return jsonify(monitor.get_dashboard_data())

@app.route('/api/alerts')
def get_alerts():
    """Get recent alerts"""
    alerts = [alert.to_dict() for alert in list(monitor.alerts)]
    return jsonify({
        'total': len(alerts),
        'alerts': alerts[-100:]  # Last 100 alerts
    })

@app.route('/api/alerts/<severity>')
def get_alerts_by_severity(severity):
    """Get alerts by severity level"""
    filtered = [a.to_dict() for a in monitor.alerts if a.severity == severity.upper()]
    return jsonify({
        'severity': severity.upper(),
        'count': len(filtered),
        'alerts': filtered[-50:]
    })

@app.route('/api/metrics/vm')
def get_vm_metrics():
    """Get VM health metrics"""
    if monitor.metrics_history['vm_health']:
        recent = list(monitor.metrics_history['vm_health'])
        return jsonify({
            'current': recent[-1] if recent else None,
            'history': [m for m in recent[-20:]]
        })
    return jsonify({'current': None, 'history': []})

@app.route('/api/metrics/pi')
def get_pi_metrics():
    """Get Raspberry Pi system metrics"""
    return jsonify(monitor.check_local_system())

@app.route('/api/status')
def get_status():
    """Get monitoring system status"""
    return jsonify({
        'monitoring_active': monitoring_active,
        'uptime_hours': monitor.get_dashboard_data()['uptime'],
        'total_alerts': len(monitor.alerts),
        'config': {
            'vm_url': monitor.config['azure_vm']['url'],
            'check_interval': monitor.config['azure_vm']['check_interval']
        }
    })

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration (sanitized)"""
    config = monitor.config.copy()
    # Remove sensitive data
    if 'alerts' in config:
        config['alerts']['smtp_password'] = '***'
    return jsonify(config)

def start_monitoring():
    """Start background monitoring thread"""
    global monitor_thread
    if not monitoring_active:
        monitor_thread = threading.Thread(target=background_monitoring, daemon=True)
        monitor_thread.start()

if __name__ == '__main__':
    print("🚀 Starting CryptoApp SIEM Dashboard")
    print("📊 Dashboard: http://0.0.0.0:5002")
    print("🔍 Starting background monitoring...\n")
    
    # Start monitoring in background
    start_monitoring()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5002, debug=False)

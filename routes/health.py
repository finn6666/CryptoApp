"""
Health, metrics, and debug routes.
"""

import time
import logging
from datetime import datetime
from flask import Blueprint, jsonify

import services.app_state as state

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/api/status/idle')
def get_idle_status():
    """Get current idle time and auto-shutdown status"""
    idle_time = time.time() - state.last_request_time
    return jsonify({
        'auto_shutdown_enabled': state.shutdown_enabled,
        'idle_timeout_seconds': state.IDLE_TIMEOUT,
        'idle_timeout_minutes': state.IDLE_TIMEOUT // 60,
        'current_idle_seconds': int(idle_time),
        'current_idle_minutes': round(idle_time / 60, 1),
        'time_until_shutdown_seconds': max(0, int(state.IDLE_TIMEOUT - idle_time)),
        'time_until_shutdown_minutes': max(0, round((state.IDLE_TIMEOUT - idle_time) / 60, 1)),
        'will_shutdown_in': f"{max(0, int(state.IDLE_TIMEOUT - idle_time))}s" if idle_time < state.IDLE_TIMEOUT else "imminent",
        'last_activity': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(state.last_request_time))
    })


@health_bp.route('/health')
def health():
    """Simple health check endpoint for load balancers and smoke tests"""
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()}), 200


@health_bp.route('/api/health')
def api_health():
    """Enhanced health check for SIEM monitoring"""
    # Trading engine status
    trading_status = {}
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        if engine:
            eng_status = engine.get_status()
            trading_status = {
                'active': eng_status.get('trading_active', False),
                'kill_switch': eng_status.get('kill_switch', False),
                'budget_remaining': eng_status.get('remaining_budget', 0),
                'trades_today': eng_status.get('todays_trades', 0),
                'pending_proposals': eng_status.get('pending_proposals', 0),
            }
    except Exception:
        trading_status = {'active': False, 'error': 'Engine not available'}

    # Scan loop status
    scan_status = {}
    try:
        from ml.scan_loop import get_scan_loop
        scanner = get_scan_loop()
        if scanner:
            scan_info = scanner.get_status()
            scan_status = {
                'scheduler_running': scan_info.get('scheduler_running', False),
                'last_scan': scan_info.get('last_scan'),
                'next_scan': scan_info.get('next_scan'),
                'scan_running': scan_info.get('scan_running', False),
            }
    except Exception:
        scan_status = {'scheduler_running': False}

    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'components': {
            'analyzer': state.analyzer is not None,
            'ml_pipeline': state.ML_AVAILABLE,
            'gem_detector': state.GEM_DETECTOR_AVAILABLE,
            'adk_orchestrator': state.official_adk_available,
            'trading_engine': trading_status,
            'scan_loop': scan_status,
        },
        'cache': {
            'analysis_entries': len(state.agent_analysis_cache),
        },
        'uptime_hours': round((time.time() - state.start_time) / 3600, 2),
    }), 200


@health_bp.route('/api/metrics')
def api_metrics():
    """System metrics for SIEM dashboard"""
    import psutil
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'system': {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        },
        'application': {
            'total_coins': len(state.analyzer.coins) if state.analyzer else 0,
            'ml_available': state.ML_AVAILABLE,
            'gem_detector_available': state.GEM_DETECTOR_AVAILABLE,
            'rl_detector_available': False
        }
    }), 200


@health_bp.route('/api/debug/coins')
def debug_coins():
    """Debug endpoint to see what coins are currently loaded"""
    try:
        coins_list = [{'symbol': coin.symbol, 'name': coin.name, 'price': coin.price}
                      for coin in state.analyzer.coins[:50]]
        return jsonify({
            'total_coins': len(state.analyzer.coins),
            'coins': coins_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

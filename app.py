#!/usr/bin/env python3
"""
CryptoApp — slim entry point.

All shared state, initialisation logic, and helpers live in services/app_state.py.
Route handlers are organised into Flask Blueprints under routes/.
"""

import os
import logging
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__,
            template_folder='src/web/templates',
            static_folder='src/web/static')

app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(32)
if not os.environ.get('SECRET_KEY'):
    logger.warning('⚠️  No SECRET_KEY set — using random key (sessions won\'t persist across restarts)')

# ---------------------------------------------------------------------------
# Shared state — initialise all ML / data components
# ---------------------------------------------------------------------------
import services.app_state as state       # noqa: E402
state.init_all()                         # ML, gem detector, data pipeline, ADK, analyzer
state.start_idle_monitor()

# ---------------------------------------------------------------------------
# Register blueprints
# ---------------------------------------------------------------------------
from routes.coins import coins_bp        # noqa: E402
from routes.ml_routes import ml_bp       # noqa: E402
from routes.symbols import symbols_bp    # noqa: E402
from routes.trading import trading_bp    # noqa: E402
from routes.health import health_bp      # noqa: E402

app.register_blueprint(coins_bp)
app.register_blueprint(ml_bp)
app.register_blueprint(symbols_bp)
app.register_blueprint(trading_bp)
app.register_blueprint(health_bp)

# ---------------------------------------------------------------------------
# Top-level page routes
# ---------------------------------------------------------------------------

@app.before_request
def track_activity():
    """Track all requests to reset idle timer"""
    state.update_activity()

@app.route('/')
def index():
    """Serve the main page with dashboard improvements"""
    return render_template('index.html')

@app.route('/legacy')
def legacy():
    """Legacy route for the original 2100+ line HTML file"""
    return render_template('index.html')


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    try:
        port = int(os.environ.get('PORT', '5001'))
    except ValueError:
        port = 5001
    debug = os.environ.get('DEBUG', 'false').lower() in ('1', 'true', 'yes')
    logger.info(f'Starting on {host}:{port} (debug={debug})')
    app.run(host=host, port=port, debug=debug)

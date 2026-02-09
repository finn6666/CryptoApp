"""
Flask extensions — instantiated here to avoid circular imports.
Initialised with the app in app.py via init_app().
"""

import os
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri="memory://",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

def init_cors(app):
    """Apply CORS with allowed origins from env."""
    allowed_origins = os.environ.get('CORS_ORIGINS', 'http://127.0.0.1:5001').split(',')
    CORS(app, origins=allowed_origins, supports_credentials=True)

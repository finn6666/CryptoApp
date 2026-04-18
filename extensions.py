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
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

def init_cors(app):
    """Apply CORS with allowed origins from env."""
    allowed_origins = os.environ.get('CORS_ORIGINS', 'http://127.0.0.1:5001').split(',')
    allowed_origins = [o.strip() for o in allowed_origins if o.strip()]
    # Block wildcard with credentials — browsers reject it, but be explicit
    if '*' in allowed_origins:
        import logging
        logging.getLogger(__name__).warning(
            "CORS_ORIGINS contains '*' with supports_credentials=True — "
            "stripping wildcard. Set explicit origins instead."
        )
        allowed_origins = [o for o in allowed_origins if o != '*']
        if not allowed_origins:
            allowed_origins = ['http://127.0.0.1:5001']
    CORS(app, origins=allowed_origins, supports_credentials=True)

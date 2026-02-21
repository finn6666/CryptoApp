"""
Redis Cache Layer
Optional Redis-backed caching for agent analysis results and API responses.

When REDIS_CONNECTION_STRING is set, provides faster shared cache across
workers. Falls back gracefully to the existing dict + JSON file cache.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_CONNECTION_STRING", "")
CACHE_PREFIX = "cryptoapp:"
DEFAULT_TTL = 14400  # 4 hours

_redis_client = None
_redis_available = False


def _get_redis():
    """Lazy-init Redis connection."""
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client

    if not REDIS_URL:
        _redis_available = False
        return None

    try:
        import redis
        _redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=3,
            socket_connect_timeout=3,
            retry_on_timeout=True,
        )
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis cache connected")
        return _redis_client
    except ImportError:
        logger.info("redis package not installed — using memory cache only")
        _redis_available = False
        return None
    except Exception as e:
        logger.warning(f"Redis connection failed ({e}) — using memory cache only")
        _redis_available = False
        return None


def is_redis_available() -> bool:
    """Check if Redis is connected."""
    _get_redis()
    return _redis_available


def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
    """
    Store a value in Redis cache.

    Args:
        key: Cache key (will be prefixed with CACHE_PREFIX)
        value: JSON-serializable value
        ttl: Time-to-live in seconds

    Returns:
        True if stored in Redis, False if unavailable
    """
    r = _get_redis()
    if r is None:
        return False
    try:
        payload = json.dumps(value, default=str)
        r.setex(f"{CACHE_PREFIX}{key}", ttl, payload)
        return True
    except Exception as e:
        logger.debug(f"Redis cache_set failed for {key}: {e}")
        return False


def cache_get(key: str) -> Optional[Any]:
    """
    Retrieve a value from Redis cache.

    Args:
        key: Cache key (will be prefixed with CACHE_PREFIX)

    Returns:
        Cached value or None if miss/unavailable
    """
    r = _get_redis()
    if r is None:
        return None
    try:
        raw = r.get(f"{CACHE_PREFIX}{key}")
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug(f"Redis cache_get failed for {key}: {e}")
        return None


def cache_delete(key: str) -> bool:
    """Delete a key from Redis cache."""
    r = _get_redis()
    if r is None:
        return False
    try:
        r.delete(f"{CACHE_PREFIX}{key}")
        return True
    except Exception:
        return False


def cache_clear(pattern: str = "*") -> int:
    """Clear cache keys matching a pattern."""
    r = _get_redis()
    if r is None:
        return 0
    try:
        keys = r.keys(f"{CACHE_PREFIX}{pattern}")
        if keys:
            return r.delete(*keys)
        return 0
    except Exception:
        return 0


def get_cache_stats() -> Dict[str, Any]:
    """Get Redis cache statistics."""
    r = _get_redis()
    if r is None:
        return {
            "available": False,
            "url_configured": bool(REDIS_URL),
        }
    try:
        info = r.info("memory")
        keys = r.keys(f"{CACHE_PREFIX}*")
        return {
            "available": True,
            "total_keys": len(keys),
            "memory_used": info.get("used_memory_human", "unknown"),
            "connected_clients": r.info("clients").get("connected_clients", 0),
        }
    except Exception as e:
        return {"available": False, "error": str(e)}

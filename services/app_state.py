"""
Shared application state and helper functions.
All blueprints import from here to access global state (analyzer, ML, etc.).
"""

import os
import re
import json
import asyncio
import logging
import time
import signal
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Project root ─────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─── Globals ──────────────────────────────────────────────────
ml_pipeline = None
ml_service = None
ML_AVAILABLE = False

data_pipeline = None
SYMBOLS_AVAILABLE = False

official_adk_available = False
analyze_crypto_adk = None

agent_analysis_cache = {}
CACHE_EXPIRY_SECONDS = 43200  # 12 hours
CACHE_FILE = os.path.join(project_root, "data", "agent_analysis_cache.json")

analyzer = None  # set during init_app()

# ─── Constants ────────────────────────────────────────────────
STABLECOINS = {
    'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'USDD', 'FRAX',
    'GUSD', 'LUSD', 'SUSD', 'USDK', 'USDX', 'PAX', 'USDN', 'USD1',
    'C1USD', 'BUIDL', 'USDF', 'USDTB', 'PYUSD', 'FDUSD', 'EURT', 'EURC',
}
MIN_PRICE = 0.00000001
MAX_PRICE = 1.25
FAVORITES_FILE = os.path.join(project_root, "data", "favorites.json")

# Idle / auto-shutdown (default OFF for production — enable for dev)
IDLE_TIMEOUT = 300  # 5 minutes
start_time = time.time()
last_request_time = time.time()
shutdown_enabled = os.environ.get('AUTO_SHUTDOWN', 'false').lower() in ('1', 'true', 'yes')


# ─── Initializers ─────────────────────────────────────────────

def initialize_official_adk():
    global official_adk_available, analyze_crypto_adk
    logger.info("Attempting to initialize Official Google ADK...")
    try:
        from ml.agents.official import analyze_crypto
        analyze_crypto_adk = analyze_crypto
        official_adk_available = True
        logger.info("Official Google ADK initialized successfully")
        return True
    except Exception as e:
        logger.warning(f"Official ADK not available: {e}")
        official_adk_available = False
        return False


def initialize_ml():
    global ml_pipeline, ml_service, ML_AVAILABLE
    logger.info("Attempting to initialize ML components...")
    try:
        from ml.training_pipeline import CryptoMLPipeline
        ml_pipeline = CryptoMLPipeline()
        ml_service = None
        ML_AVAILABLE = True
        try:
            ml_pipeline.load_existing_model()
            logger.info("ML model loaded successfully")
        except Exception as e:
            logger.warning(f"ML model not available: {e}")
        logger.info("ML components initialized successfully")
        return True
    except Exception as e:
        logger.error(f"ML components not available: {e}")
        ML_AVAILABLE = False
        ml_pipeline = None
        ml_service = None
        return False


def initialize_data_pipeline():
    global data_pipeline, SYMBOLS_AVAILABLE
    logger.info("Attempting to initialize data pipeline...")
    try:
        from ml.data_pipeline import CryptoDataPipeline
        data_pipeline = CryptoDataPipeline()
        SYMBOLS_AVAILABLE = True
        logger.info("Data pipeline initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Data pipeline not available: {e}")
        SYMBOLS_AVAILABLE = False
        return False


def load_analysis_cache():
    """Load agent analysis cache from disk."""
    global agent_analysis_cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                raw = json.load(f)
            # Prune expired entries on load
            now = time.time()
            agent_analysis_cache = {
                k: v for k, v in raw.items()
                if now - v.get("_cached_at", 0) < CACHE_EXPIRY_SECONDS
            }
            logger.info(f"Loaded {len(agent_analysis_cache)} cached analyses from disk")
    except Exception as e:
        logger.warning(f"Could not load analysis cache: {e}")
        agent_analysis_cache = {}


def save_analysis_cache():
    """Persist agent analysis cache to disk."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(agent_analysis_cache, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Could not save analysis cache: {e}")


def cache_analysis(symbol: str, result: dict):
    """Store an analysis result in the cache (Redis + disk)."""
    result["_cached_at"] = time.time()
    agent_analysis_cache[symbol] = result
    # Prune stale entries so the cache doesn't grow unboundedly between restarts
    now = time.time()
    expired = [k for k, v in agent_analysis_cache.items()
               if now - v.get("_cached_at", 0) > CACHE_EXPIRY_SECONDS]
    for k in expired:
        del agent_analysis_cache[k]
    save_analysis_cache()
    # Also store in Redis if available
    try:
        from services.redis_cache import cache_set
        cache_set(f"analysis:{symbol}", result, CACHE_EXPIRY_SECONDS)
    except Exception:
        pass


def get_cached_analysis(symbol: str):
    """Return cached analysis for symbol if still valid, else None."""
    # Try in-memory first
    entry = agent_analysis_cache.get(symbol)
    if entry and time.time() - entry.get("_cached_at", 0) <= CACHE_EXPIRY_SECONDS:
        return entry
    # Try Redis
    try:
        from services.redis_cache import cache_get
        redis_entry = cache_get(f"analysis:{symbol}")
        if redis_entry:
            agent_analysis_cache[symbol] = redis_entry
            return redis_entry
    except Exception:
        pass
    # Expired or missing
    agent_analysis_cache.pop(symbol, None)
    return None


def init_all():
    """Run all startup initializers and create the analyzer."""
    global analyzer
    from src.core.crypto_analyzer import CryptoAnalyzer
    logger.info("Starting CryptoApp...")

    for fn in (initialize_ml, initialize_data_pipeline, initialize_official_adk):
        try:
            fn()
        except Exception as e:
            logger.warning(f"Startup {fn.__name__} failed: {e}")

    load_analysis_cache()

    # Auto-fetch live data if the cache file doesn't exist yet
    data_file = 'data/live_api.json'
    if not os.path.exists(data_file):
        logger.info("No live data cache found — fetching live data on first start...")
        try:
            from src.core.live_data_fetcher import fetch_and_update_data
            result = fetch_and_update_data(force_refresh=True)
            if result:
                logger.info("Live data fetched successfully on startup")
            else:
                logger.warning("Live data fetch returned no data — dashboard may show empty state")
        except Exception as e:
            logger.warning(f"Could not fetch live data on startup: {e}")

    analyzer = CryptoAnalyzer(data_file=data_file)
    logger.info(
        f"System ready - ML: {ML_AVAILABLE}, ADK: {official_adk_available}, "
        f"Coins: {len(analyzer.coins)}"
    )


# ─── Helper functions ─────────────────────────────────────────

def run_async(coro):
    """Run an async coroutine from synchronous Flask context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def safe_float(val):
    """Convert string value to float (handles currency symbols)."""
    if isinstance(val, str):
        return float(val.replace('£', '').replace('$', '').replace(',', ''))
    return float(val or 0)


def coin_to_dict(coin, include_highlights=False):
    """Convert Coin object to dictionary for analysis."""
    coin_dict = {
        'symbol': coin.symbol,
        'name': coin.name,
        'price': coin.price or 0,
        'market_cap': safe_float(getattr(coin, 'market_cap', 0)),
        'volume_24h': safe_float(getattr(coin, 'total_volume', 0)),
        'price_change_24h': coin.price_change_24h or 0,
        'price_change_7d': getattr(coin, 'price_change_7d', None) or 0,
        'market_cap_rank': coin.market_cap_rank,
        'attractiveness_score': safe_float(getattr(coin, 'attractiveness_score', 0)),
    }
    if include_highlights:
        highlights = coin.investment_highlights
        coin_dict['investment_highlights'] = ' • '.join(highlights) if isinstance(highlights, list) else highlights
    return coin_dict


def _sanitize_ai_text(text):
    """Remove raw JSON objects/fragments from text meant for UI display."""
    if not text or not isinstance(text, str):
        return text or ''
    cleaned = re.sub(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', text)
    cleaned = re.sub(r'```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    if not cleaned or len(cleaned) < 10:
        return None
    return cleaned


def _build_gem_analysis(gem_result):
    """Build a standardised analysis dict from a gem_detector result.
    Returns (analysis_dict, ai_sentiment, enhanced_score) or (None, None, None).
    """
    if not gem_result:
        return None, None, None

    gem_prob = gem_result.get('gem_probability', 0)
    is_gem = gem_prob > 0.6
    strengths = gem_result.get('key_strengths', [])
    weaknesses = gem_result.get('key_weaknesses', [])
    ai_sentiment = gem_result.get('ai_sentiment')

    summary_parts = []
    if ai_sentiment and ai_sentiment.get('key_points'):
        key_points = ai_sentiment['key_points']
        summary_parts.append(key_points[0])
        if len(key_points) > 2:
            summary_parts.append(key_points[2])
    else:
        if is_gem:
            summary_parts.append(f"Hidden gem ({gem_prob*100:.0f}% confidence)")
        if strengths:
            summary_parts.append(f"{', '.join(strengths[:1])}")
        if weaknesses:
            summary_parts.append(weaknesses[0])

    raw_summary = ' '.join(summary_parts) if summary_parts else gem_result.get('recommendation', 'Monitoring...')
    clean_summary = _sanitize_ai_text(raw_summary) or 'Monitoring...'

    analysis = {
        'recommendation': 'BUY' if is_gem else 'WATCH',
        'confidence': f"{gem_prob*100:.0f}%",
        'summary': clean_summary,
        'risk_level': gem_result.get('risk_level', 'Medium'),
        'gem_score': f"{gem_result.get('gem_score', 0)/10:.1f}/10",
        'analysis_type': 'Gem Detector',
    }
    enhanced_score = min(10, gem_result.get('gem_score', 0) / 10)
    return analysis, ai_sentiment, enhanced_score


def parse_market_cap(value):
    """Parse a market cap value that may be a string with currency symbols."""
    if isinstance(value, str):
        return float(value.replace('£', '').replace('$', '').replace(',', '').replace('N/A', '0'))
    return float(value or 0)


def parse_volume(value):
    """Parse a volume value that may be a string with currency symbols."""
    return parse_market_cap(value)


def load_favorites():
    """Load user's favorite coins from JSON file."""
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading favorites: {e}")
        return []


def save_favorites(favorites):
    """Save user's favorite coins to JSON file."""
    try:
        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
        with open(FAVORITES_FILE, 'w') as f:
            json.dump(favorites, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving favorites: {e}")
        return False


def fetch_and_add_new_symbol_data(symbol: str):
    """Fetch data for a newly added symbol and add it to the live data."""
    import requests

    cg_api_key = os.getenv('COINGECKO_API_KEY', '')
    logger.info(f"Fetching data for new symbol: {symbol}")

    if not data_pipeline:
        raise Exception("Data pipeline not available")

    headers = {'Accept': 'application/json'}
    if cg_api_key:
        headers['x-cg-demo-api-key'] = cg_api_key

    cg_base = "https://api.coingecko.com/api/v3"

    # Resolve symbol → CoinGecko ID
    search_resp = requests.get(
        f"{cg_base}/search", headers=headers, params={'query': symbol.upper()}, timeout=10
    )
    search_resp.raise_for_status()
    coin_id = None
    for c in search_resp.json().get('coins', []):
        if c.get('symbol', '').upper() == symbol.upper():
            coin_id = c.get('id')
            break

    if not coin_id:
        raise Exception(f"Symbol {symbol} not found on CoinGecko")

    # Fetch market data
    market_resp = requests.get(
        f"{cg_base}/coins/markets",
        headers=headers,
        params={
            'vs_currency': 'usd',
            'ids': coin_id,
            'sparkline': 'false',
            'price_change_percentage': '24h',
        },
        timeout=10,
    )
    market_resp.raise_for_status()
    market_data = market_resp.json()
    if not market_data:
        raise Exception(f"No market data returned for {symbol} (id={coin_id})")

    coin_data = market_data[0]
    price = coin_data.get('current_price', 0)
    market_cap = coin_data.get('market_cap', 0)
    volume = coin_data.get('total_volume', 0)

    new_coin_data = {
        "item": {
            "id": coin_id,
            "name": coin_data.get('name', symbol),
            "symbol": symbol.upper(),
            "status": "current",
            "attractiveness_score": 6.0,
            "investment_highlights": ["Recently added symbol"],
            "risk_level": "medium",
            "market_cap_rank": coin_data.get('market_cap_rank'),
            "data": {
                "price": price,
                "price_change_percentage_24h": {"usd": coin_data.get('price_change_percentage_24h', 0)},
                "market_cap": f"${market_cap:,}" if market_cap else "N/A",
                "total_volume": f"${volume:,}" if volume else "N/A",
                "content": None,
                "source": "coingecko",
            },
        }
    }

    live_data_file = "data/live_api.json"
    try:
        with open(live_data_file, 'r') as f:
            live_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        live_data = {"last_updated": datetime.now().isoformat(), "sources": ["coingecko"], "coins": []}

    existing_symbols = [coin["item"]["symbol"] for coin in live_data.get("coins", [])]
    if symbol.upper() not in existing_symbols:
        live_data["coins"].append(new_coin_data)
        live_data["last_updated"] = datetime.now().isoformat()
        with open(live_data_file, 'w') as f:
            json.dump(live_data, f, indent=2)
        analyzer.load_data()
        logger.info(f"Successfully added {symbol} data to live data file")
    else:
        logger.info(f"Symbol {symbol} already exists in live data")


def update_activity():
    """Update last activity time."""
    global last_request_time
    last_request_time = time.time()


def start_idle_monitor():
    """Start the background idle-shutdown monitor thread."""
    if not shutdown_enabled:
        return

    def _monitor():
        global last_request_time
        while True:
            time.sleep(30)
            idle_time = time.time() - last_request_time
            if idle_time > IDLE_TIMEOUT:
                logger.info(f"No activity for {int(idle_time)}s. Shutting down to save resources...")
                os.kill(os.getpid(), signal.SIGTERM)
                break

    thread = threading.Thread(target=_monitor, daemon=True)
    thread.start()
    logger.info(f"⏰ Auto-shutdown enabled: will stop after {IDLE_TIMEOUT}s ({IDLE_TIMEOUT//60} min) of idle time")

#!/usr/bin/env python3

from flask import Flask, render_template, jsonify, request
import sys
import os
import json
import asyncio
import logging
import threading
import time
import signal
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'ml'))
sys.path.insert(0, os.path.join(project_root, 'services'))

from src.core.crypto_analyzer import CryptoAnalyzer, CoinStatus
from src.core.live_data_fetcher import fetch_and_update_data
from datetime import datetime

# Initialize ML components as None by default
ml_pipeline = None
ml_service = None
ML_AVAILABLE = False

# Initialize enhanced hidden gem detector
gem_detector = None

# Agent analysis cache (to avoid quota exhaustion)
agent_analysis_cache = {}
CACHE_EXPIRY_SECONDS = 14400  # 4 hours — reduces repeat API calls
GEM_DETECTOR_AVAILABLE = False

# Initialize data pipeline for symbol management
data_pipeline = None
SYMBOLS_AVAILABLE = False

# Initialize official Google ADK agents
official_adk_available = False
analyze_crypto_adk = None

def initialize_official_adk():
    """Initialize official Google ADK multi-agent system"""
    global official_adk_available, analyze_crypto_adk
    logger.info("Attempting to initialize Official Google ADK...")
    try:
        from ml.agents.official import analyze_crypto
        
        analyze_crypto_adk = analyze_crypto
        official_adk_available = True
        logger.info("✅ Official Google ADK initialized successfully")
        return True
    except Exception as e:
        logger.warning(f"Official ADK not available: {e}")
        official_adk_available = False
        return False

def initialize_ml():
    """Try to initialize ML components in a separate function"""
    global ml_pipeline, ml_service, ML_AVAILABLE
    logger.info("Attempting to initialize ML components...")
    try:
        from ml.training_pipeline import CryptoMLPipeline
        
        logger.info("ML imports successful")
        ml_pipeline = CryptoMLPipeline()
        ml_service = None  # ml_service removed - not needed
        ML_AVAILABLE = True
        
        logger.info("ML objects created")
        
        # Try to load existing model
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
    """Try to initialize data pipeline for symbol management"""
    global data_pipeline, SYMBOLS_AVAILABLE
    logger.info("Attempting to initialize data pipeline...")
    try:
        from ml.data_pipeline import CryptoDataPipeline
        
        logger.info("Data pipeline imports successful")
        data_pipeline = CryptoDataPipeline()
        SYMBOLS_AVAILABLE = True
        
        logger.info("Data pipeline initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Data pipeline not available: {e}")
        SYMBOLS_AVAILABLE = False
        return False

def initialize_gem_detector():
    """Initialize the enhanced hidden gem detector"""
    global gem_detector, GEM_DETECTOR_AVAILABLE
    logger.info("Attempting to initialize Enhanced Hidden Gem Detector...")
    try:
        from ml.enhanced_gem_detector import HiddenGemDetector
        
        logger.info("Hidden Gem Detector imports successful")
        gem_detector = HiddenGemDetector()
        
        # Try to load existing model
        if gem_detector.load_model():
            logger.info("Hidden Gem Detector model loaded successfully")
            GEM_DETECTOR_AVAILABLE = True
        else:
            logger.info("No existing model found, will train on first use...")
            GEM_DETECTOR_AVAILABLE = True  # Available for training
        
        logger.info("Enhanced Hidden Gem Detector initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Hidden Gem Detector not available: {e}")
        GEM_DETECTOR_AVAILABLE = False
        return False

# Note: RL functionality is provided by simple_rl.py integrated into HiddenGemDetector
# No separate RL detector initialization needed

def fetch_and_add_new_symbol_data(symbol: str):
    """Fetch data for a newly added symbol and add it to the live data"""
    try:
        import requests
        
        cmc_api_key = os.getenv('COINMARKETCAP_API_KEY')
        
        logger.info(f"Fetching data for new symbol: {symbol}")
        
        # First, validate the symbol exists
        if not data_pipeline:
            raise Exception("Data pipeline not available")
        
        # Fetch current market data from CMC
        cmc_url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {'X-CMC_PRO_API_KEY': cmc_api_key}
        params = {
            'symbol': symbol.upper(),
            'convert': 'USD'
        }
        
        response = requests.get(cmc_url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        coin_data = data.get('data', {}).get(symbol.upper())
        if not coin_data:
            raise Exception(f"Symbol {symbol} not found on CoinMarketCap")
        
        # Create coin data structure
        quote = coin_data.get('quote', {}).get('USD', {})
        price = quote.get('price', 0)
        
        new_coin_data = {
            "item": {
                "id": str(coin_data.get('id')),
                "name": coin_data.get('name', symbol),
                "symbol": symbol.upper(),
                "status": "current",
                "attractiveness_score": 6.0,  # Default score for new additions
                "investment_highlights": ["Recently added symbol"],
                "risk_level": "medium",
                "market_cap_rank": coin_data.get('cmc_rank'),
                "price_btc": None,
                "data": {
                    "price": price,
                    "price_btc": None,
                    "price_change_percentage_24h": {
                        "usd": quote.get('percent_change_24h', 0)
                    },
                    "market_cap": f"${quote.get('market_cap', 0):,}" if quote.get('market_cap') else "N/A",
                    "total_volume": f"${quote.get('volume_24h', 0):,}" if quote.get('volume_24h') else "N/A",
                    "content": None,
                    "source": "coinmarketcap"
                }
            }
        }
        
        # Load existing data
        live_data_file = "data/live_api.json"
        try:
            with open(live_data_file, 'r') as f:
                live_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            live_data = {"last_updated": datetime.now().isoformat(), "sources": ["coinmarketcap"], "coins": []}
        
        # Check if symbol already exists
        existing_symbols = [coin["item"]["symbol"] for coin in live_data.get("coins", [])]
        if symbol.upper() not in existing_symbols:
            # Add the new coin to the data
            live_data["coins"].append(new_coin_data)
            live_data["last_updated"] = datetime.now().isoformat()
            
            # Save updated data
            with open(live_data_file, 'w') as f:
                json.dump(live_data, f, indent=2)
            
            # Reload analyzer with new data
            analyzer.load_data()
            
            logger.info(f"Successfully added {symbol} data to live data file")
        else:
            logger.info(f"Symbol {symbol} already exists in live data")
            
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        raise

app = Flask(__name__, 
           template_folder='src/web/templates',
           static_folder='src/web/static')

# Constants
STABLECOINS = {'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'USDD', 'FRAX', 'GUSD', 'LUSD', 'SUSD', 'USDK', 'USDX', 'PAX', 'USDN', 'USD1', 'C1USD', 'BUIDL', 'USDF', 'USDTB', 'PYUSD', 'FDUSD', 'EURT', 'EURC'}
MIN_PRICE = 0.00000001
MAX_PRICE = 1.25
IDLE_TIMEOUT = 300  # 5 minutes
start_time = time.time()
last_request_time = time.time()
shutdown_enabled = os.environ.get('AUTO_SHUTDOWN', 'true').lower() in ('1', 'true', 'yes')

def idle_monitor():
    """Monitor for idle time and shutdown if no activity"""
    global last_request_time
    if not shutdown_enabled:
        return
    
    while True:
        time.sleep(30)  # Check every 30 seconds
        idle_time = time.time() - last_request_time
        
        if idle_time > IDLE_TIMEOUT:
            logger.info(f"🛑 No activity for {int(idle_time)}s. Shutting down to save resources...")
            os.kill(os.getpid(), signal.SIGTERM)
            break

def update_activity():
    """Update last activity time"""
    global last_request_time
    last_request_time = time.time()

# Start idle monitor in background thread
if shutdown_enabled:
    monitor_thread = threading.Thread(target=idle_monitor, daemon=True)
    monitor_thread.start()
    logger.info(f"⏰ Auto-shutdown enabled: will stop after {IDLE_TIMEOUT}s ({IDLE_TIMEOUT//60} min) of idle time")

@app.before_request
def track_activity():
    """Track all requests to reset idle timer"""
    update_activity()

# Favorites functionality
FAVORITES_FILE = "data/favorites.json"

def load_favorites():
    """Load user's favorite coins from JSON file"""
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading favorites: {e}")
        return []

def save_favorites(favorites):
    """Save user's favorite coins to JSON file"""
    try:
        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
        with open(FAVORITES_FILE, 'w') as f:
            json.dump(favorites, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving favorites: {e}")
        return False

# Helper Functions
def run_async(coro):
    """Run an async coroutine from synchronous Flask context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def safe_float(val):
    """Convert string value to float (handles currency symbols)"""
    if isinstance(val, str):
        return float(val.replace('£', '').replace('$', '').replace(',', ''))
    return float(val or 0)

def coin_to_dict(coin, include_highlights=False):
    """Convert Coin object to dictionary for analysis"""
    coin_dict = {
        'symbol': coin.symbol,
        'name': coin.name,
        'price': coin.price or 0,
        'market_cap': safe_float(getattr(coin, 'market_cap', 0)),
        'volume_24h': safe_float(getattr(coin, 'total_volume', 0)),
        'price_change_24h': coin.price_change_24h or 0,
        'market_cap_rank': coin.market_cap_rank
    }
    if include_highlights:
        highlights = coin.investment_highlights
        coin_dict['investment_highlights'] = ' • '.join(highlights) if isinstance(highlights, list) else highlights
    return coin_dict

def _sanitize_ai_text(text):
    """Remove raw JSON objects/fragments from text meant for UI display."""
    import re
    if not text or not isinstance(text, str):
        return text or ''
    # Remove JSON objects like {"key": "value", ...}
    cleaned = re.sub(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', text)
    # Remove markdown code block wrappers
    cleaned = re.sub(r'```(?:json)?\s*', '', cleaned)
    # Clean up extra whitespace
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    # If we stripped everything, return a short fallback
    if not cleaned or len(cleaned) < 10:
        return None
    return cleaned


def _build_gem_analysis(gem_result):
    """Build a standardised analysis dict from a gem_detector result.

    Returns (analysis_dict, ai_sentiment, enhanced_score) or (None, None, None)
    if gem_result is falsy.
    """
    if not gem_result:
        return None, None, None

    gem_prob = gem_result.get('gem_probability', 0)
    is_gem = gem_prob > 0.6
    strengths = gem_result.get('key_strengths', [])
    weaknesses = gem_result.get('key_weaknesses', [])
    ai_sentiment = gem_result.get('ai_sentiment')

    # Build concise, individualized summary
    summary_parts = []
    if ai_sentiment and ai_sentiment.get('key_points'):
        key_points = ai_sentiment['key_points']
        summary_parts.append(f"🔥 {key_points[0]}" if is_gem else key_points[0])
        if len(key_points) > 2:
            summary_parts.append(f"⚠️ {key_points[2]}")
    else:
        if is_gem:
            summary_parts.append(f"🔥 Hidden gem ({gem_prob*100:.0f}% confidence)")
        if strengths:
            summary_parts.append(f"{', '.join(strengths[:1])}")
        if weaknesses:
            summary_parts.append(f"⚠️ {weaknesses[0]}")

    raw_summary = ' '.join(summary_parts) if summary_parts else gem_result.get('recommendation', 'Monitoring...')
    clean_summary = _sanitize_ai_text(raw_summary) or 'Monitoring...'

    analysis = {
        'recommendation': 'BUY' if is_gem else 'WATCH',
        'confidence': f"{gem_prob*100:.0f}%",
        'summary': clean_summary,
        'risk_level': gem_result.get('risk_level', 'Medium'),
        'gem_score': f"{gem_result.get('gem_score', 0)/10:.1f}/10",
        'analysis_type': 'Gem Detector'
    }
    enhanced_score = min(10, gem_result.get('gem_score', 0) / 10)
    return analysis, ai_sentiment, enhanced_score

def analyze_coin_with_ai(coin_dict, coin=None):
    """Run comprehensive AI analysis on a coin (Gem Detector with integrated RL -> ML fallback)"""
    result = {'ai_analysis': None, 'ai_sentiment': None, 'enhanced_score': coin.attractiveness_score if coin else 5.0}
    
    # Try Gem Detector (includes integrated simple_rl)
    if GEM_DETECTOR_AVAILABLE and gem_detector:
        try:
            gem_result = gem_detector.predict_hidden_gem(coin_dict)
            analysis, ai_sentiment, enhanced_score = _build_gem_analysis(gem_result)
            if analysis:
                result['ai_analysis'] = analysis
                result['enhanced_score'] = enhanced_score
                if ai_sentiment:
                    result['ai_sentiment'] = ai_sentiment
                return result
        except Exception as e:
            logger.warning(f"Gem detection failed: {e}")
    
    # Try basic ML
    if ML_AVAILABLE and ml_pipeline and ml_pipeline.model_loaded:
        try:
            features = {
                'price_change_1h': coin_dict.get('price_change_24h', 0),
                'price_change_24h': coin_dict.get('price_change_24h', 0),
                'volume_change_24h': 0, 'market_cap_change_24h': 0,
                'rsi': 50, 'macd': 0,
                'moving_avg_7d': coin_dict.get('price', 0),
                'moving_avg_30d': coin_dict.get('price', 0)
            }
            ml_result = ml_pipeline.predict_with_validation(features)
            pred_pct = ml_result.get('prediction_percentage', 0)
            direction = 'bullish' if pred_pct > 1 else 'bearish' if pred_pct < -1 else 'neutral'
            
            # More nuanced recommendation considering multiple factors
            gem_score = coin_dict.get('enhanced_score') or coin_dict.get('score', 0)
            sentiment_score = coin_dict.get('ai_sentiment', {}).get('score', 0) if coin_dict.get('ai_sentiment') else 0
            
            # Calculate weighted recommendation score
            rec_score = (pred_pct * 0.4) + (gem_score / 10 * 0.4) + (sentiment_score * 5 * 0.2)
            
            # Individualized thresholds based on gem score
            buy_threshold = 1.5 if gem_score < 60 else 0.8
            avoid_threshold = -1.5 if gem_score < 60 else -0.8
            
            if rec_score > buy_threshold:
                recommendation = 'BUY'
            elif rec_score < avoid_threshold:
                recommendation = 'AVOID'
            else:
                recommendation = 'HOLD'
            
            result['ai_analysis'] = {
                'recommendation': recommendation,
                'confidence': f"{ml_result.get('confidence', 0)*100:.0f}%",
                'summary': f"ML predicts {direction} trend with {abs(pred_pct):.1f}% expected movement.",
                'prediction': f"{pred_pct:+.1f}%",
                'analysis_type': 'ML Model'
            }
        except Exception as e:
            logger.warning(f"ML prediction failed: {e}")
    
    return result

# Initialize ML components immediately
# Try to initialize ML components on startup
logger.info("Starting CryptoApp...")
try:
    initialize_ml()
except Exception as e:
    logger.warning(f"Startup ML initialization failed: {e}")

# Try to initialize data pipeline on startup
try:
    initialize_data_pipeline()
except Exception as e:
    logger.warning(f"Startup data pipeline initialization failed: {e}")

# Try to initialize gem detector on startup
try:
    initialize_gem_detector()
except Exception as e:
    logger.warning(f"Startup gem detector initialization failed: {e}")

# Try to initialize official Google ADK on startup
try:
    initialize_official_adk()
except Exception as e:
    logger.warning(f"Startup official ADK initialization failed: {e}")

# Note: RL functionality integrated into gem_detector via simple_rl

# Initialize analyzer with live data (after all other components)
analyzer = CryptoAnalyzer(data_file='data/live_api.json')
logger.info(f"System ready - ML: {ML_AVAILABLE}, Gem Detector: {GEM_DETECTOR_AVAILABLE}, ADK: {official_adk_available}, Coins: {len(analyzer.coins)}")

# Print RL status

@app.route('/')
def index():
    """Serve the main page with dashboard improvements"""
    return render_template('index.html')

@app.route('/legacy')
def legacy():
    """Legacy route for the original 2100+ line HTML file"""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """Get portfolio statistics"""
    try:
        total_coins = len(analyzer.coins)
        current_coins = len(analyzer.filter_by_status(CoinStatus.CURRENT))
        high_potential = len(analyzer.get_high_potential_coins())
        trending_up = len([coin for coin in analyzer.coins if coin.price_change_24h and coin.price_change_24h > 0])
        
        return jsonify({
            'total_coins': total_coins,
            'current_coins': current_coins,
            'high_potential': high_potential,
            'trending_up': trending_up
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/coins')
def get_coins():
    """Get coins data (excluding favorites) with integrated multi-agent analysis"""
    try:
        # Check if agent analysis is requested
        run_agents = request.args.get('agents', 'true').lower() == 'true'
        limit = int(request.args.get('limit', 20))
        
        favorites = load_favorites()
        favorites_upper = [f.upper() for f in favorites]
        logger.info(f"Excluding favorites: {favorites_upper}")
        
        # Get recently added symbols from data pipeline
        recently_added_coins = []
        if SYMBOLS_AVAILABLE and data_pipeline:
            for symbol in data_pipeline.supported_symbols:
                # Find this symbol in the analyzer's coins
                matching_coin = next((coin for coin in analyzer.coins if coin.symbol == symbol), None)
                if matching_coin and matching_coin not in recently_added_coins:
                    recently_added_coins.append(matching_coin)
        
        # Get more coins initially to account for price filtering
        low_cap_coins = analyzer.get_low_cap_coins(50)
        
        # Combine recently added coins with low cap coins (prioritize recently added)
        selected_coins = []
        
        # First, add recently added coins under £1, excluding stablecoins, favorites, and very low prices
        for coin in recently_added_coins:
            if coin.symbol.upper() in favorites_upper:
                logger.debug(f"Skipping {coin.symbol} - in favorites")
                continue
            if (coin not in selected_coins and 
                coin.symbol not in STABLECOINS and
                coin.price and coin.price >= MIN_PRICE and
                coin.price <= MAX_PRICE):  # Under £1 equivalent (~$1.25)
                selected_coins.append(coin)
        
        # Then add low cap coins under £1 (avoiding duplicates, favorites, stablecoins, and very low prices)
        for coin in low_cap_coins:
            if coin.symbol.upper() in favorites_upper:
                logger.debug(f"Skipping {coin.symbol} - in favorites")
                continue
            if (coin not in selected_coins and len(selected_coins) < 50 and
                coin.symbol not in STABLECOINS and
                coin.price and coin.price >= MIN_PRICE and
                coin.price <= MAX_PRICE):  # Under £1 equivalent (~$1.25)
                selected_coins.append(coin)
        
        # If still need more coins, get affordable top coins by score (excluding favorites)
        if len(selected_coins) < 20:
            # Get all coins sorted by attractiveness score
            all_affordable_coins = [coin for coin in analyzer.coins 
                                  if (coin.symbol.upper() not in favorites_upper and
                                      coin.symbol not in STABLECOINS and
                                      coin.price and coin.price >= MIN_PRICE and 
                                      coin.price <= MAX_PRICE)]
            all_affordable_coins.sort(key=lambda x: x.attractiveness_score, reverse=True)
            
            for coin in all_affordable_coins:
                if coin not in selected_coins and len(selected_coins) < 50:
                    selected_coins.append(coin)
                if len(selected_coins) >= 50:
                    break
        
        coins_data = []
        for coin in selected_coins[:limit]:  # Use requested limit
            coins_data.append({
                'symbol': coin.symbol,
                'name': coin.name,
                'score': coin.attractiveness_score,
                'price': coin.price,
                'price_change_24h': coin.price_change_24h or 0,
                'market_cap_rank': coin.market_cap_rank,
                'recently_added': coin.symbol in [c.symbol for c in recently_added_coins],  # Flag for UI
                'ai_analysis': None,  # Will be populated below
                'ai_sentiment': None,  # AI sentiment from multi-agent
                'agent_analysis': None  # PHASE 4: Multi-agent analysis
            })
        
        # Add comprehensive AI analysis to each coin
        for coin_data in coins_data:
            symbol = coin_data['symbol']
            matching_coin = next((c for c in analyzer.coins if c.symbol == symbol), None)
            
            if not matching_coin:
                continue
            
            # Prepare coin dict for analysis
            # Convert market_cap from string if needed (e.g. '£243,445,620' -> 243445620)
            market_cap_value = getattr(matching_coin, 'market_cap', 0)
            if isinstance(market_cap_value, str):
                # Remove currency symbols and commas
                market_cap_value = float(market_cap_value.replace('£', '').replace('$', '').replace(',', ''))
            
            # Convert volume from string if needed
            volume_value = getattr(matching_coin, 'total_volume', 0)
            if isinstance(volume_value, str):
                volume_value = float(volume_value.replace('£', '').replace('$', '').replace(',', ''))
            
            coin_dict = {
                'symbol': matching_coin.symbol,
                'name': matching_coin.name,
                'price': matching_coin.price or 0,
                'market_cap': market_cap_value or 0,
                'volume_24h': volume_value or 0,
                'price_change_24h': matching_coin.price_change_24h or 0,
                'market_cap_rank': matching_coin.market_cap_rank
            }
            
            ai_insights = []
            ai_score = min(10, matching_coin.attractiveness_score / 10)  # Normalize from 0-100 to 0-10
            analysis_done = False
            
            # Gem Detector Analysis (includes simple_rl)
            if GEM_DETECTOR_AVAILABLE and gem_detector:
                try:
                    gem_result = gem_detector.predict_hidden_gem(coin_dict)
                    analysis, ai_sentiment, enhanced = _build_gem_analysis(gem_result)
                    if analysis:
                        coin_data['ai_analysis'] = analysis
                        if ai_sentiment:
                            coin_data['ai_sentiment'] = ai_sentiment
                        analysis_done = True
                        ai_score = enhanced
                except Exception as e:
                    logging.warning(f"Gem detection failed for {symbol}: {e}")
            
            # 3. Basic ML Prediction (last fallback - only if no analysis done yet)
            if ML_AVAILABLE and ml_pipeline and ml_pipeline.model_loaded and not analysis_done:
                try:
                    features = {
                        'price_change_1h': matching_coin.price_change_24h or 0,
                        'price_change_24h': matching_coin.price_change_24h or 0,
                        'volume_change_24h': 0,
                        'market_cap_change_24h': 0,
                        'rsi': 50,
                        'macd': 0,
                        'moving_avg_7d': matching_coin.price or 0,
                        'moving_avg_30d': matching_coin.price or 0
                    }
                    ml_result = ml_pipeline.predict_with_validation(features)
                    pred_pct = ml_result.get('prediction_percentage', 0)
                    
                    direction = 'bullish' if pred_pct > 2 else 'bearish' if pred_pct < -2 else 'neutral'
                    recommendation = 'BUY' if pred_pct > 2 else 'HOLD' if pred_pct > -2 else 'AVOID'
                    
                    coin_data['ai_analysis'] = {
                        'recommendation': recommendation,
                        'confidence': f"{ml_result.get('confidence', 0)*100:.0f}%",
                        'summary': f"ML predicts {direction} trend with {abs(pred_pct):.1f}% expected movement.",
                        'prediction': f"{pred_pct:+.1f}%",
                        'analysis_type': 'ML Model'
                    }
                    analysis_done = True
                except Exception as e:
                    logging.warning(f"ML prediction failed for {symbol}: {e}")
            
            # Update score with AI insights (ensure it's 0-10 scale)
            coin_data['enhanced_score'] = min(10, ai_score)
            
            # PHASE 4: Add multi-agent analysis if enabled and available
            if run_agents and GEM_DETECTOR_AVAILABLE and gem_detector and gem_detector.multi_agent_enabled:
                try:
                    import asyncio
                    
                    # Prepare comprehensive coin data for agent analysis
                    agent_coin_data = {
                        'symbol': matching_coin.symbol,
                        'name': matching_coin.name,
                        'price': matching_coin.price or 0,
                        'price_change_24h': matching_coin.price_change_24h or 0,
                        'price_change_7d': 0,
                        'market_cap_rank': matching_coin.market_cap_rank or 999,
                        'market_cap': market_cap_value or 0,
                        'volume_24h': volume_value or 0,
                        'attractiveness_score': matching_coin.attractiveness_score or 5.0,
                        'status': getattr(matching_coin, 'status', 'current')
                    }
                    
                    # Run async multi-agent analysis
                    agent_result = run_async(gem_detector.analyze_with_agents(agent_coin_data))
                    if agent_result:
                        coin_data['agent_analysis'] = agent_result
                        logger.info(f"Multi-agent analysis completed for {symbol}: {agent_result.get('gem_score')}%")
                        
                except Exception as agent_error:
                    logger.warning(f"Multi-agent analysis failed for {symbol}: {agent_error}")

        returned_symbols = [c['symbol'] for c in coins_data]
        logger.info(f"Returning {len(coins_data)} live coins (excluded {len(favorites)} favorites): {returned_symbols}")
        
        return jsonify({
            'coins': coins_data,
            'last_updated': datetime.now().isoformat(),
            'cache_expires_in': 300,  # 5 minutes
            'recently_added_count': len(recently_added_coins)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh', methods=['POST'])
def force_refresh():
    """Force refresh with live data"""
    try:
        # Fetch fresh live data
        live_data = fetch_and_update_data()
        if live_data:
            # Also try to fetch data for any newly added symbols from data pipeline
            if SYMBOLS_AVAILABLE and data_pipeline:
                try:
                    added_symbols = []
                    for symbol in data_pipeline.supported_symbols:
                        try:
                            # Check if symbol is already in live data
                            current_symbols = [coin.symbol for coin in analyzer.coins]
                            if symbol not in current_symbols:
                                fetch_and_add_new_symbol_data(symbol)
                                added_symbols.append(symbol)
                        except Exception as e:
                            print(f"Warning: Could not fetch data for {symbol}: {e}")
                    
                    if added_symbols:
                        print(f"Added data for new symbols: {added_symbols}")
                except Exception as e:
                    print(f"Warning: Error processing pipeline symbols: {e}")
            
            # Reload the analyzer with new data
            analyzer.load_data()
            return jsonify({'success': True, 'message': 'Live data refreshed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to fetch live data'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/favorites')
def get_favorites():
    """Get all favorite coins with their current data and comprehensive AI analysis"""
    try:
        from src.core.live_data_fetcher import fetch_specific_coin
        
        favorites = load_favorites()
        favorite_coins = []
        missing_coins = []
        
        for symbol in favorites:
            # Find the coin in our current data
            found = False
            for coin in analyzer.coins:
                if coin.symbol.upper() == symbol.upper():
                    found = True
                    coin_data = {
                        'symbol': coin.symbol,
                        'name': coin.name,
                        'price': coin.price,
                        'price_change_24h': coin.price_change_24h,
                        'score': min(10, coin.attractiveness_score / 10),
                        'market_cap': coin.market_cap,
                        'market_cap_rank': coin.market_cap_rank,
                        'ai_analysis': None,
                        'enhanced_score': min(10, coin.attractiveness_score / 10),
                        'ai_sentiment': None
                    }
                    
                    # Prepare coin dict for analysis
                    # Convert market_cap from string if needed (e.g. '£243,445,620' -> 243445620)
                    market_cap_value = getattr(coin, 'market_cap', 0)
                    if isinstance(market_cap_value, str):
                        # Remove currency symbols and commas
                        market_cap_value = float(market_cap_value.replace('£', '').replace('$', '').replace(',', ''))
                    
                    # Convert volume from string if needed
                    volume_value = getattr(coin, 'total_volume', 0)
                    if isinstance(volume_value, str):
                        volume_value = float(volume_value.replace('£', '').replace('$', '').replace(',', ''))
                    
                    coin_dict = {
                        'symbol': coin.symbol,
                        'name': coin.name,
                        'price': coin.price or 0,
                        'market_cap': market_cap_value or 0,
                        'volume_24h': volume_value or 0,
                        'price_change_24h': coin.price_change_24h or 0,
                        'market_cap_rank': coin.market_cap_rank
                    }
                    
                    analysis_done = False
                    
                    # Try Gem Detector
                    if GEM_DETECTOR_AVAILABLE and gem_detector and not analysis_done:
                        try:
                            gem_result = gem_detector.predict_hidden_gem(coin_dict)
                            analysis, ai_sentiment, enhanced = _build_gem_analysis(gem_result)
                            if analysis:
                                coin_data['ai_analysis'] = analysis
                                if ai_sentiment:
                                    coin_data['ai_sentiment'] = ai_sentiment
                                coin_data['enhanced_score'] = enhanced
                                analysis_done = True
                        except Exception as e:
                            logging.warning(f"Gem detection failed for favorite {coin.symbol}: {e}")
                    
                    # Basic ML prediction (last fallback)
                    if ML_AVAILABLE and ml_pipeline and ml_pipeline.model_loaded and not analysis_done:
                        try:
                            features = {
                                'price_change_1h': coin.price_change_24h or 0,
                                'price_change_24h': coin.price_change_24h or 0,
                                'volume_change_24h': 0,
                                'market_cap_change_24h': 0,
                                'rsi': 50,
                                'macd': 0,
                                'moving_avg_7d': coin.price or 0,
                                'moving_avg_30d': coin.price or 0
                            }
                            
                            ml_result = ml_pipeline.predict_with_validation(features)
                            pred_pct = ml_result.get('prediction_percentage', 0)
                            
                            # Individual recommendation based on multiple factors
                            gem_score = coin_data.get('enhanced_score') or coin_data.get('score', 0)
                            sentiment_score = coin_data.get('ai_sentiment', {}).get('score', 0) if coin_data.get('ai_sentiment') else 0
                            
                            rec_score = (pred_pct * 0.4) + (gem_score / 10 * 0.4) + (sentiment_score * 5 * 0.2)
                            buy_threshold = 1.5 if gem_score < 60 else 0.8
                            avoid_threshold = -1.5 if gem_score < 60 else -0.8
                            
                            if rec_score > buy_threshold:
                                recommendation = 'BUY'
                            elif rec_score < avoid_threshold:
                                recommendation = 'AVOID'
                            else:
                                recommendation = 'HOLD'
                            
                            direction = 'bullish' if pred_pct > 1 else 'bearish' if pred_pct < -1 else 'neutral'
                            
                            coin_data['ai_analysis'] = {
                                'recommendation': recommendation,
                                'confidence': f"{ml_result.get('confidence', 0)*100:.0f}%",
                                'summary': f"ML predicts {direction} trend with {abs(pred_pct):.1f}% expected movement.",
                                'prediction': f"{pred_pct:+.1f}%",
                                'analysis_type': 'ML Model'
                            }
                            analysis_done = True
                        except Exception as ml_error:
                            logging.warning(f"ML prediction failed for favorite {coin.symbol}: {ml_error}")
                    
                    favorite_coins.append(coin_data)
                    break
            
            # If not found in low-cap list, fetch it directly from API
            if not found:
                logger.info(f"Fetching {symbol} directly from API (not in low-cap list)")
                try:
                    coin_data_raw = fetch_specific_coin(symbol)
                    if coin_data_raw:
                        coin_data = {
                            'symbol': coin_data_raw['symbol'],
                            'name': coin_data_raw['name'],
                            'price': coin_data_raw['current_price'],
                            'price_change_24h': coin_data_raw['price_change_percentage_24h'],
                            'score': 5.0,  # Default score
                            'market_cap': coin_data_raw['market_cap'],
                            'market_cap_rank': coin_data_raw['market_cap_rank'],
                            'ai_analysis': None,
                            'enhanced_score': 5.0,
                            'ai_sentiment': None
                        }
                        
                        # Run gem_detector analysis on directly-fetched coins
                        coin_dict = {
                            'symbol': coin_data_raw['symbol'],
                            'name': coin_data_raw['name'],
                            'price': coin_data_raw['current_price'] or 0,
                            'market_cap': coin_data_raw['market_cap'] or 0,
                            'volume_24h': coin_data_raw['total_volume'] or 0,
                            'price_change_24h': coin_data_raw['price_change_percentage_24h'] or 0,
                            'market_cap_rank': coin_data_raw['market_cap_rank']
                        }
                        
                        analysis_done = False
                        
                        # Try gem_detector analysis (includes multi-agent AI)
                        if GEM_DETECTOR_AVAILABLE and gem_detector and not analysis_done:
                            try:
                                gem_result = gem_detector.predict_hidden_gem(coin_dict)
                                analysis, ai_sentiment, enhanced = _build_gem_analysis(gem_result)
                                if analysis:
                                    coin_data['ai_analysis'] = analysis
                                    if ai_sentiment:
                                        coin_data['ai_sentiment'] = ai_sentiment
                                    coin_data['enhanced_score'] = enhanced
                                    analysis_done = True
                            except Exception as e:
                                logging.warning(f"Gem detection failed for directly-fetched {symbol}: {e}")
                        
                        favorite_coins.append(coin_data)
                    else:
                        if symbol not in missing_coins:
                            missing_coins.append(symbol)
                        logger.warning(f"Could not fetch {symbol} from API")
                except Exception as e:
                    if symbol not in missing_coins:
                        missing_coins.append(symbol)
                    # Check if it's a rate limit error
                    if '429' in str(e):
                        logger.warning(f"Rate limit hit for {symbol} - try again in a few minutes")
                    else:
                        logger.error(f"Error fetching {symbol}: {e}")
        
        if missing_coins:
            logger.info(f"Missing favorite coins (could not fetch): {', '.join(missing_coins)}")
        
        # Add agent analysis to favorites if requested (optional for performance)
        run_agents = request.args.get('agents', 'false').lower() == 'true'
        
        if run_agents and GEM_DETECTOR_AVAILABLE and gem_detector and gem_detector.multi_agent_enabled:
            import asyncio
            
            for coin_data in favorite_coins:
                try:
                    symbol = coin_data['symbol']
                    
                    # Check cache first (1 hour expiry)
                    cache_key = f"agent_{symbol}"
                    if cache_key in agent_analysis_cache:
                        cached_data, timestamp = agent_analysis_cache[cache_key]
                        if (datetime.now().timestamp() - timestamp) < CACHE_EXPIRY_SECONDS:
                            coin_data['agent_analysis'] = cached_data
                            logger.info(f"Using cached agent analysis for favorite {symbol}")
                            continue
                    
                    # Prepare comprehensive coin data for agent analysis
                    market_cap_value = coin_data.get('market_cap', 0)
                    if isinstance(market_cap_value, str):
                        market_cap_value = float(market_cap_value.replace('£', '').replace('$', '').replace(',', '').replace('N/A', '0'))
                    
                    agent_coin_data = {
                        'symbol': coin_data['symbol'],
                        'name': coin_data['name'],
                        'price': coin_data.get('price', 0),
                        'price_change_24h': coin_data.get('price_change_24h', 0),
                        'price_change_7d': 0,
                        'market_cap_rank': coin_data.get('market_cap_rank', 999),
                        'market_cap': market_cap_value,
                        'volume_24h': 0,
                        'attractiveness_score': coin_data.get('enhanced_score', 5.0) * 10,
                        'status': 'favorite',
                        'is_favorite': True
                    }
                    
                    # Run async multi-agent analysis
                    agent_result = run_async(gem_detector.analyze_with_agents(agent_coin_data))
                    if agent_result:
                        coin_data['agent_analysis'] = agent_result
                        # Cache the result
                        agent_analysis_cache[cache_key] = (agent_result, datetime.now().timestamp())
                        logger.info(f"Multi-agent analysis completed for favorite {coin_data['symbol']}: {agent_result.get('gem_score')}%")
                        
                except Exception as agent_error:
                    logger.warning(f"Multi-agent analysis failed for favorite {coin_data['symbol']}: {agent_error}")
        
        ml_status = ML_AVAILABLE and ml_pipeline and ml_pipeline.model_loaded
        logger.info(f"[INFO] Favorites API - ML Enhanced: {ml_status}, Favorite coins: {len(favorite_coins)}, Missing: {len(missing_coins)}")
        
        return jsonify({
            'favorites': favorite_coins,
            'ml_enhanced': ml_status,
            'missing_count': len(missing_coins)
        })
    except Exception as e:
        logger.error(f"Error in get_favorites: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/favorites/add', methods=['POST'])
def add_favorite():
    """Add a coin to favorites"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        
        if not symbol:
            return jsonify({'success': False, 'error': 'Symbol is required'}), 400
            
        favorites = load_favorites()
        if symbol not in favorites:
            favorites.append(symbol)
            if save_favorites(favorites):
                return jsonify({'success': True, 'message': f'{symbol} added to favorites'})
            else:
                return jsonify({'success': False, 'error': 'Failed to save favorites'}), 500
        else:
            return jsonify({'success': False, 'error': f'{symbol} is already in favorites'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/favorites/remove', methods=['POST'])
def remove_favorite():
    """Remove a coin from favorites"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        
        if not symbol:
            return jsonify({'success': False, 'error': 'Symbol is required'}), 400
            
        favorites = load_favorites()
        if symbol in favorites:
            favorites.remove(symbol)
            if save_favorites(favorites):
                return jsonify({'success': True, 'message': f'{symbol} removed from favorites'})
            else:
                return jsonify({'success': False, 'error': 'Failed to save favorites'}), 500
        else:
            return jsonify({'success': False, 'error': f'{symbol} is not in favorites'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ml/status')
def get_ml_status():
    """Get ML model status and information"""
    try:
        logger.info(f"🔍 ML Status Check - ML_AVAILABLE: {ML_AVAILABLE}, ml_pipeline: {ml_pipeline}")
        
        if not ML_AVAILABLE or ml_pipeline is None:
            # Try to provide helpful error info
            error_details = {
                'error': 'ML components not available',
                'ML_AVAILABLE': ML_AVAILABLE,
                'ml_pipeline_exists': ml_pipeline is not None,
                'suggestion': 'Click "Train ML Model" to initialize and train the model',
                'gem_detector_available': GEM_DETECTOR_AVAILABLE,
                'rl_detector_available': False  # RL integrated into gem_detector
            }
            
            # Check if ML dependencies might be missing
            try:
                import sklearn
                import pandas as pd
                import numpy as np
                error_details['dependencies_ok'] = True
            except ImportError as ie:
                error_details['dependencies_ok'] = False
                error_details['missing_dependency'] = str(ie)
            
            return jsonify({
                'ml_status': error_details,
                'service_available': False
            })
            
        status = ml_pipeline.get_status()
        logger.info(f"📊 ML Status: {status}")
        
        return jsonify({
            'ml_status': status,
            'service_available': True
        })
        
    except Exception as e:
        logger.error(f"Error getting ML status: {e}")
        return jsonify({
            'error': str(e),
            'service_available': False
        }), 500

@app.route('/api/gemini/quota')
def check_gemini_quota():
    """Check Gemini API quota status"""
    import os
    try:
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return jsonify({
                'error': 'GOOGLE_API_KEY not found in environment',
                'instructions': 'Set GOOGLE_API_KEY in your .env file (get it at https://aistudio.google.com/apikey)'
            }), 500
        
        # Make a minimal test request to check quota
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content("Say 'OK'")
            
            return jsonify({
                'status': 'SUCCESS',
                'message': '✅ Gemini API is working!',
                'tier': 'PAID (if billing enabled) or FREE',
                'test_response': response.text,
                'next_steps': [
                    'Check https://ai.google.dev/rate-limit for current usage',
                    'If getting 429 errors, billing may not be active yet (can take a few minutes)',
                    'Verify billing at https://console.cloud.google.com/billing'
                ]
            })
        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg or 'quota' in error_msg.lower():
                return jsonify({
                    'status': 'QUOTA_ERROR',
                    'message': '⚠️ Still hitting quota limits',
                    'error': error_msg,
                    'billing_status': 'Billing may not be active yet - can take 5-10 minutes after enabling',
                    'actions': [
                        '1. Verify billing is enabled at https://console.cloud.google.com/billing',
                        '2. Check project is linked to billing account',
                        '3. Wait 5-10 minutes for changes to propagate',
                        '4. Generate a NEW API key from a billing-enabled project'
                    ]
                })
            else:
                raise
                
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to test Gemini API'
        }), 500

@app.route('/api/market/conditions')
def get_market_conditions():
    """Calculate overall market opportunity conditions based on current portfolio"""
    try:
        # Get all current coins
        all_coins = analyzer.get_all_coins()
        
        if not all_coins:
            return jsonify({
                'opportunity_level': 'UNKNOWN',
                'opportunity_score': 50,
                'opportunity_percentage': 50,
                'message': 'Insufficient data',
                'indicators': {}
            })
        
        # Calculate market metrics
        total_coins = len(all_coins)
        avg_price_change = sum(c.price_change_24h or 0 for c in all_coins) / max(total_coins, 1)
        
        # Count opportunity categories based on market cap
        nano_caps = sum(1 for c in all_coins if (c.market_cap_rank or 999) > 500)
        micro_caps = sum(1 for c in all_coins if 300 < (c.market_cap_rank or 999) <= 500)
        low_caps = sum(1 for c in all_coins if 100 < (c.market_cap_rank or 999) <= 300)
        
        # Calculate opportunity score (0-100)
        # Higher score = more opportunity
        opp_score = 50  # baseline
        
        # More small caps = more upside opportunity
        cap_opportunity = ((nano_caps * 3) + (micro_caps * 2) + (low_caps * 1)) / max(total_coins, 1) * 10
        opp_score += cap_opportunity
        
        # Strong price movement = opportunity (both directions)
        momentum_boost = abs(avg_price_change) * 1.5
        opp_score += momentum_boost
        
        # Positive market = more opportunity
        if avg_price_change > 5:
            opp_score += 15  # Strong uptrend
        elif avg_price_change > 2:
            opp_score += 10  # Uptrend
        elif avg_price_change < -5:
            opp_score += 5   # Dip = buying opportunity
        
        # Clamp score between 0-100
        opp_score = max(0, min(100, opp_score))
        
        # Determine opportunity level
        if opp_score >= 75:
            opp_level = 'EXCELLENT'
            message = '🟢 Excellent Opportunity - Strong market conditions'
        elif opp_score >= 60:
            opp_level = 'GOOD'
            message = '🟢 Good Opportunity - Favorable conditions'
        elif opp_score >= 40:
            opp_level = 'MODERATE'
            message = '🟡 Moderate Opportunity - Standard conditions'
        elif opp_score >= 25:
            opp_level = 'LIMITED'
            message = '⚪ Limited Opportunity - Quiet market'
        else:
            opp_level = 'LOW'
            message = '⚪ Low Opportunity - Waiting for movement'
        
        return jsonify({
            'opportunity_level': opp_level,
            'opportunity_score': int(opp_score),
            'opportunity_percentage': int(opp_score),
            'message': message,
            'indicators': {
                'total_coins': total_coins,
                'avg_price_change_24h': round(avg_price_change, 2),
                'nano_caps': nano_caps,
                'micro_caps': micro_caps,
                'low_caps': low_caps,
                'market_cap_diversity': f"{nano_caps}/{micro_caps}/{low_caps}"
            }
        })
        
    except Exception as e:
        logger.error(f"Market conditions error: {e}")
        return jsonify({
            'error': str(e),
            'risk_level': 'UNKNOWN',
            'risk_score': 50,
            'risk_percentage': 50
        }), 500

@app.route('/api/debug/ml')
def debug_ml_system():
    """Comprehensive ML system diagnostics"""
    try:
        models_dir = os.path.join(project_root, 'models')
        
        debug_info = {
            'ml_pipeline': {
                'ML_AVAILABLE': ML_AVAILABLE,
                'ml_pipeline_exists': ml_pipeline is not None,
                'model_loaded': ml_pipeline.model_loaded if ml_pipeline else False,
                'training_status': ml_pipeline.training_status if ml_pipeline else 'N/A',
                'last_training_time': str(ml_pipeline.last_training_time) if ml_pipeline and ml_pipeline.last_training_time else None,
            },
            'gem_detector': {
                'GEM_DETECTOR_AVAILABLE': GEM_DETECTOR_AVAILABLE,
                'gem_detector_exists': gem_detector is not None,
                'rl_integrated': True,  # simple_rl integrated into gem_detector
            },
            'model_files': {
                'models_dir_exists': os.path.exists(models_dir),
                'crypto_model_pkl': os.path.exists(os.path.join(models_dir, 'crypto_model.pkl')),
                'scaler_pkl': os.path.exists(os.path.join(models_dir, 'scaler.pkl')),
                'rl_model_pkl': os.path.exists(os.path.join(models_dir, 'rl_model.pkl')),
            },
            'analyzer': {
                'total_coins': len(analyzer.coins),
                'coins_with_price': len([c for c in analyzer.coins if c.price and c.price > 0]),
            },
            'recommendation': ''
        }
        
        # Add recommendation based on status
        if not ML_AVAILABLE:
            debug_info['recommendation'] = 'ML system failed to initialize. Check server logs for import errors.'
        elif ml_pipeline and not ml_pipeline.model_loaded:
            debug_info['recommendation'] = 'ML pipeline initialized but no model loaded. Click "Train ML Model" button.'
        elif not debug_info['model_files']['crypto_model_pkl']:
            debug_info['recommendation'] = 'Model files missing. Train the model first.'
        else:
            debug_info['recommendation'] = 'System appears healthy. Check individual analyzer status.'
            
        return jsonify(debug_info)
        
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml/predict/<symbol>')
def get_ml_prediction(symbol):
    """Get ML price prediction for a specific cryptocurrency"""
    try:
        if not ML_AVAILABLE or ml_pipeline is None or not ml_pipeline.model_loaded:
            return jsonify({'error': 'ML model not available'}), 503
        
        # Find the coin in current data
        coin = None
        for c in analyzer.coins:
            if c.symbol.upper() == symbol.upper():
                coin = c
                break
        
        if not coin:
            return jsonify({'error': f'Coin {symbol} not found in current data'}), 404
        
        # Create feature dictionary from coin data
        features = {
            'price_change_1h': coin.price_change_24h or 0,  # Using 24h as proxy for 1h
            'price_change_24h': coin.price_change_24h or 0,
            'volume_change_24h': 0,  # Default, could be enhanced with more data
            'market_cap_change_24h': 0,  # Default, could be enhanced with more data
            'rsi': 50,  # Default RSI value
            'macd': 0,  # Default MACD value
            'moving_avg_7d': coin.price or 0,  # Using current price as proxy
            'moving_avg_30d': coin.price or 0  # Using current price as proxy
        }
        
        # Get ML prediction
        prediction_result = ml_pipeline.predict_with_validation(features)
        
        # Add coin information to result
        prediction_result.update({
            'coin': {
                'symbol': coin.symbol,
                'name': coin.name,
                'current_price': coin.price,
                'attractiveness_score': coin.attractiveness_score
            }
        })
        
        return jsonify(prediction_result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/coins/enhanced')
def get_enhanced_coins():
    """Get coins data enhanced with ML predictions (excluding favorites)"""
    try:
        # Get favorites to exclude from live list
        favorites = load_favorites()
        favorites_upper = [f.upper() for f in favorites]
        logger.info(f"[Enhanced] Excluding favorites from live coins: {favorites_upper}")
        
        # Get recently added symbols from data pipeline (same logic as /api/coins)
        recently_added_coins = []
        if SYMBOLS_AVAILABLE and data_pipeline:
            for symbol in data_pipeline.supported_symbols:
                # Find this symbol in the analyzer's coins
                matching_coin = next((coin for coin in analyzer.coins if coin.symbol == symbol), None)
                if matching_coin and matching_coin not in recently_added_coins:
                    recently_added_coins.append(matching_coin)
        
        # Get more coins initially to account for price filtering
        low_cap_coins = analyzer.get_low_cap_coins(50)
        
        # Combine recently added coins with low cap coins (prioritize recently added)
        selected_coins = []
        
        # First, add recently added coins under £1, excluding stablecoins, favorites, and very low prices
        for coin in recently_added_coins:
            if coin.symbol.upper() in favorites_upper:
                logger.debug(f"[Enhanced] Skipping {coin.symbol} - in favorites")
                continue
            if (coin not in selected_coins and 
                coin.symbol not in STABLECOINS and
                coin.price and coin.price >= MIN_PRICE and
                coin.price <= MAX_PRICE):  # Under £1 equivalent (~$1.25)
                selected_coins.append(coin)
        
        # Then add low cap coins under £1 (avoiding duplicates, favorites, stablecoins, and very low prices)
        for coin in low_cap_coins:
            if coin.symbol.upper() in favorites_upper:
                logger.debug(f"[Enhanced] Skipping {coin.symbol} - in favorites")
                continue
            if (coin not in selected_coins and len(selected_coins) < 50 and
                coin.symbol not in STABLECOINS and
                coin.price and coin.price >= MIN_PRICE and
                coin.price <= MAX_PRICE):  # Under £1 equivalent (~$1.25)
                selected_coins.append(coin)
        
        # If still need more coins, get affordable top coins by score (excluding favorites)
        if len(selected_coins) < 20:
            # Get all coins sorted by attractiveness score
            all_affordable_coins = [coin for coin in analyzer.coins 
                                  if (coin.symbol.upper() not in favorites_upper and
                                      coin.symbol not in STABLECOINS and
                                      coin.price and coin.price >= MIN_PRICE and 
                                      coin.price <= MAX_PRICE)]
            all_affordable_coins.sort(key=lambda x: x.attractiveness_score, reverse=True)
            
            for coin in all_affordable_coins:
                if coin not in selected_coins and len(selected_coins) < 50:
                    selected_coins.append(coin)
                if len(selected_coins) >= 50:
                    break
        
        coins_data = []
        for coin in selected_coins[:20]:  # Show more coins now that cards are compact
            coin_data = {
                'symbol': coin.symbol,
                'name': coin.name,
                'score': min(10, coin.attractiveness_score / 10),
                'price': coin.price,
                'price_change_24h': coin.price_change_24h or 0,
                'market_cap_rank': coin.market_cap_rank,
                'recently_added': coin.symbol in [c.symbol for c in recently_added_coins],
                'ai_analysis': None,
                'enhanced_score': min(10, coin.attractiveness_score / 10)
            }
            
            # Prepare coin dict for AI analysis (same as favorites)
            market_cap_value = getattr(coin, 'market_cap', 0)
            if isinstance(market_cap_value, str):
                market_cap_value = float(market_cap_value.replace('£', '').replace('$', '').replace(',', ''))
            
            volume_value = getattr(coin, 'total_volume', 0)
            if isinstance(volume_value, str):
                volume_value = float(volume_value.replace('£', '').replace('$', '').replace(',', ''))
            
            coin_dict = {
                'symbol': coin.symbol,
                'name': coin.name,
                'price': coin.price or 0,
                'market_cap': market_cap_value or 0,
                'volume_24h': volume_value or 0,
                'price_change_24h': coin.price_change_24h or 0,
                'market_cap_rank': coin.market_cap_rank
            }
            
            # AI analysis system
            analysis_done = False
            
            # Try Gem Detector
            if GEM_DETECTOR_AVAILABLE and gem_detector and not analysis_done:
                try:
                    gem_result = gem_detector.predict_hidden_gem(coin_dict)
                    analysis, ai_sentiment, enhanced = _build_gem_analysis(gem_result)
                    if analysis:
                        coin_data['ai_analysis'] = analysis
                        coin_data['enhanced_score'] = enhanced
                        analysis_done = True
                except Exception as e:
                    logger.warning(f"Gem detection failed for {coin.symbol}: {e}")
            
            coins_data.append(coin_data)
        
        # Add agent analysis if explicitly requested (opt-in to avoid quota exhaustion)
        run_agents = request.args.get('agents', 'false').lower() == 'true'
        if run_agents and GEM_DETECTOR_AVAILABLE and gem_detector and gem_detector.multi_agent_enabled:
            for coin_data in coins_data:
                try:
                    symbol = coin_data['symbol']
                    
                    # Check cache first (1 hour expiry)
                    cache_key = f"agent_{symbol}"
                    if cache_key in agent_analysis_cache:
                        cached_data, timestamp = agent_analysis_cache[cache_key]
                        if (datetime.now().timestamp() - timestamp) < CACHE_EXPIRY_SECONDS:
                            coin_data['agent_analysis'] = cached_data
                            logger.info(f"Using cached agent analysis for {symbol}")
                            continue
                    
                    # Find the coin object
                    matching_coin = next((c for c in selected_coins if c.symbol == symbol), None)
                    if not matching_coin:
                        continue
                    
                    # Prepare data for agent analysis
                    market_cap_value = getattr(matching_coin, 'market_cap', 0)
                    if isinstance(market_cap_value, str):
                        market_cap_value = float(market_cap_value.replace('£', '').replace('$', '').replace(',', '').replace('N/A', '0'))
                    
                    volume_value = getattr(matching_coin, 'total_volume', 0)
                    if isinstance(volume_value, str):
                        volume_value = float(volume_value.replace('£', '').replace('$', '').replace(',', '').replace('N/A', '0'))
                    
                    agent_coin_data = {
                        'symbol': matching_coin.symbol,
                        'name': matching_coin.name,
                        'price': matching_coin.price or 0,
                        'price_change_24h': matching_coin.price_change_24h or 0,
                        'price_change_7d': 0,
                        'market_cap_rank': matching_coin.market_cap_rank or 999,
                        'market_cap': market_cap_value,
                        'volume_24h': volume_value,
                        'attractiveness_score': matching_coin.attractiveness_score or 5.0,
                        'status': getattr(matching_coin, 'status', 'current')
                    }
                    
                    # Run async multi-agent analysis
                    agent_result = run_async(gem_detector.analyze_with_agents(agent_coin_data))
                    if agent_result:
                        coin_data['agent_analysis'] = agent_result
                        # Cache the result
                        agent_analysis_cache[cache_key] = (agent_result, datetime.now().timestamp())
                        logger.info(f"Multi-agent analysis completed for {symbol}: {agent_result.get('gem_score')}%")
                        
                except Exception as agent_error:
                    logger.warning(f"Multi-agent analysis failed for {coin_data['symbol']}: {agent_error}")
        
        # Sort by enhanced score
        coins_data.sort(key=lambda x: x['enhanced_score'], reverse=True)
        
        returned_symbols = [c['symbol'] for c in coins_data]
        logger.info(f"[Enhanced] Returning {len(coins_data)} live coins (excluded {len(favorites)} favorites): {returned_symbols}")
        
        return jsonify({
            'coins': coins_data,
            'last_updated': datetime.now().isoformat(),
            'ml_enhanced': ML_AVAILABLE and ml_pipeline and ml_pipeline.model_loaded,
            'recently_added_count': len(recently_added_coins),
            'cache_expires_in': 300
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml/train', methods=['POST'])
def train_ml_model():
    """Trigger ML model training (for demo purposes)"""
    try:
        logger.info("🎯 ML Training requested")
        
        # Try to initialize ML if not available
        if not ML_AVAILABLE or ml_pipeline is None:
            logger.warning("ML not initialized on startup, attempting to initialize now...")
            init_success = initialize_ml()
            if not init_success:
                logger.error("ML initialization failed")
                return jsonify({
                    'success': False,
                    'error': 'ML components not available. Please check server logs or restart the service.'
                }), 503
            logger.info("ML components initialized successfully")
            
        if not os.path.exists('models'):
            os.makedirs('models')
            logger.info("Created models directory")
        
        logger.info("Creating sample training data...")
        # Create sample data for training
        sample_data_path = 'models/sample_training_data.csv'
        sample_df = ml_pipeline.create_sample_data(symbol="BTC", days=30)
        sample_df.to_csv(sample_data_path, index=False)
        logger.info(f"Sample data created: {len(sample_df)} rows")
        
        logger.info("Training model... (this may take 30-60 seconds)")
        # Train the model
        training_result = ml_pipeline.train_model(sample_data_path)
        logger.info(f"Training complete: {training_result}")
        
        # Export the trained model
        models_dir = os.path.join(project_root, 'models')
        ml_pipeline.export_model(models_dir)
        logger.info(f"Model exported to {models_dir}")
        
        return jsonify({
            'success': True,
            'message': 'Model trained successfully! Predictions are now available.',
            'training_result': training_result,
            'status': ml_pipeline.get_status(),
            'rows_trained': len(sample_df)
        })
        
    except Exception as e:
        logger.error(f"ML training failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Training failed: {str(e)}'
        }), 500

@app.route('/api/ml/initialize', methods=['POST'])
def initialize_ml_endpoint():
    """Initialize ML components on demand"""
    success = initialize_ml()
    if success:
        return jsonify({
            'success': True,
            'message': 'ML components initialized successfully',
            'ml_available': ML_AVAILABLE
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to initialize ML components',
            'ml_available': False
        })

# Symbol Management API Endpoints

@app.route('/api/search', methods=['POST'])
def search_coins():
    """Simple search endpoint for frontend - searches for coins by symbol/name"""
    if not SYMBOLS_AVAILABLE or not data_pipeline:
        return jsonify({
            'success': False,
            'error': 'Search service not available. Please try again later.'
        })
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Please enter a search term'
            })
        
        results = run_async(data_pipeline.search_symbols(query, limit=20))
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        })

@app.route('/api/symbols/search', methods=['GET'])
def search_symbols():
    """Search for symbols matching a query"""
    if not SYMBOLS_AVAILABLE or not data_pipeline:
        return jsonify({
            'success': False,
            'error': 'Symbol search service not available'
        }), 503
    
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query parameter "q" is required'
            }), 400
        
        if len(query) < 1:
            return jsonify({
                'success': False,
                'error': 'Query must be at least 1 character long'
            }), 400
        
        results = run_async(data_pipeline.search_symbols(query, limit))
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500

@app.route('/api/symbols/validate', methods=['POST'])
def validate_symbol():
    """Validate a symbol and return its details"""
    if not SYMBOLS_AVAILABLE or not data_pipeline:
        return jsonify({
            'success': False,
            'error': 'Symbol validation service not available'
        }), 503
    
    try:
        data = request.get_json()
        if not data or 'symbol' not in data:
            return jsonify({
                'success': False,
                'error': 'Symbol is required in request body'
            }), 400
        
        symbol = data['symbol'].strip().upper()
        if not symbol:
            return jsonify({
                'success': False,
                'error': 'Symbol cannot be empty'
            }), 400
        
        validation_result = run_async(data_pipeline.validate_symbol(symbol))
        
        if validation_result['status'] == 'valid':
            return jsonify({
                'success': True,
                'symbol': validation_result['symbol'],
                'cmc_id': validation_result.get('cmc_id', validation_result.get('coingecko_id')),  # Support both for now
                'name': validation_result['name'],
                'valid': True
            })
        else:
            return jsonify({
                'success': False,
                'symbol': validation_result['symbol'],
                'valid': False,
                'error': validation_result.get('error', 'Symbol not found')
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Validation failed: {str(e)}'
        }), 500

@app.route('/api/symbols/add', methods=['POST'])
def add_symbol():
    """Add a new symbol to the supported list"""
    if not SYMBOLS_AVAILABLE or not data_pipeline:
        return jsonify({
            'success': False,
            'error': 'Symbol management service not available'
        }), 503
    
    try:
        data = request.get_json()
        if not data or 'symbol' not in data:
            return jsonify({
                'success': False,
                'error': 'Symbol is required in request body'
            }), 400
        
        symbol = data['symbol'].strip().upper()
        if not symbol:
            return jsonify({
                'success': False,
                'error': 'Symbol cannot be empty'
            }), 400
        
        success = run_async(data_pipeline.add_new_symbol(symbol))
        
        if success:
            # Immediately fetch data for the new symbol and add it to live data
            try:
                logger.info(f"Adding symbol {symbol} - fetching data...")
                fetch_and_add_new_symbol_data(symbol)
                logger.info(f"Symbol {symbol} added successfully, analyzer has {len(analyzer.coins)} coins")
                return jsonify({
                    'success': True,
                    'symbol': symbol,
                    'message': f'Symbol {symbol} added successfully and data fetched'
                })
            except Exception as e:
                # Symbol was added to pipeline but data fetch failed
                logger.error(f"Failed to fetch data for {symbol}: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'symbol': symbol,
                    'error': f'Failed to fetch data for {symbol}: {str(e)}'
                }), 500
        else:
            return jsonify({
                'success': False,
                'symbol': symbol,
                'error': f'Failed to add symbol {symbol}. It may not exist or is already supported.'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to add symbol: {str(e)}'
        }), 500

@app.route('/api/symbols', methods=['GET'])
def get_supported_symbols():
    """Get list of all currently supported symbols"""
    if not SYMBOLS_AVAILABLE or not data_pipeline:
        return jsonify({
            'success': False,
            'error': 'Symbol service not available'
        }), 503
    
    try:
        symbols = data_pipeline.supported_symbols
        return jsonify({
            'success': True,
            'symbols': symbols,
            'count': len(symbols)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get symbols: {str(e)}'
        }), 500

@app.route('/api/symbols/status', methods=['GET'])
def get_symbols_status():
    """Get status of symbol management service"""
    return jsonify({
        'symbols_available': SYMBOLS_AVAILABLE,
        'supported_count': len(data_pipeline.supported_symbols) if data_pipeline else 0,
        'service_status': 'available' if SYMBOLS_AVAILABLE else 'unavailable'
    })

# Hidden Gem Detection API Endpoints

@app.route('/api/gems/detect/<symbol>')
def detect_hidden_gem(symbol):
    """Detect if a specific symbol is a hidden gem"""
    if not GEM_DETECTOR_AVAILABLE or not gem_detector:
        return jsonify({'error': 'Hidden Gem Detector not available'}), 503
    
    try:
        # Find the coin
        coin = None
        for c in analyzer.coins:
            if c.symbol.upper() == symbol.upper():
                coin = c
                break
        
        if not coin:
            return jsonify({'error': f'Coin {symbol} not found'}), 404
        
        # Convert coin object to dictionary for analysis
        coin_data = {
            'symbol': coin.symbol,
            'name': coin.name,
            'price': coin.price,
            'price_change_24h': {'usd': getattr(coin, 'price_change_24h', 0)},
            'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
            'market_cap': getattr(coin, 'market_cap', 'N/A'),
            'total_volume': getattr(coin, 'total_volume', 'N/A'),
            'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
            'status': getattr(coin, 'status', 'current')
        }
        
        # Get prediction
        prediction = gem_detector.predict_hidden_gem(coin_data)
        
        if prediction is None:
            return jsonify({'error': 'Prediction failed'}), 500
        
        # Add coin info
        prediction['coin'] = {
            'symbol': coin.symbol,
            'name': coin.name,
            'price': coin.price,
            'market_cap_rank': coin_data['market_cap_rank'],
            'attractiveness_score': coin_data['attractiveness_score']
        }
        
        return jsonify(prediction)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gems/scan')
def scan_for_hidden_gems():
    """Scan all coins for potential hidden gems"""
    if not GEM_DETECTOR_AVAILABLE or not gem_detector:
        return jsonify({'error': 'Hidden Gem Detector not available'}), 503
    
    try:
        limit = int(request.args.get('limit', 20))
        min_probability = float(request.args.get('min_probability', 0.6))
        
        hidden_gems = []
        processed_count = 0
        
        for coin in analyzer.coins[:100]:  # Scan first 100 coins
            try:
                processed_count += 1
                
                # Convert coin object to dictionary
                coin_data = {
                    'symbol': coin.symbol,
                    'name': coin.name,
                    'price': coin.price,
                    'price_change_24h': {'usd': getattr(coin, 'price_change_24h', 0)},
                    'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
                    'market_cap': getattr(coin, 'market_cap', 'N/A'),
                    'total_volume': getattr(coin, 'total_volume', 'N/A'),
                    'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
                    'status': getattr(coin, 'status', 'current')
                }
                
                prediction = gem_detector.predict_hidden_gem(coin_data)
                
                if prediction and prediction['gem_probability'] >= min_probability:
                    gem_info = {
                        'symbol': coin.symbol,
                        'name': coin.name,
                        'price': coin.price,
                        'market_cap_rank': coin_data['market_cap_rank'],
                        'attractiveness_score': coin_data['attractiveness_score'],
                        'gem_probability': prediction['gem_probability'],
                        'gem_score': prediction['gem_score'],
                        'confidence': prediction['confidence'],
                        'risk_level': prediction['risk_level'],
                        'recommendation': prediction['recommendation'],
                        'key_strengths': prediction['key_strengths'][:3],  # Top 3 strengths
                        'top_features': prediction['top_features'][:3]     # Top 3 features
                    }
                    hidden_gems.append(gem_info)
                    
            except Exception as e:
                print(f"Error scanning {coin.symbol}: {e}")
                continue
        
        # Sort by gem probability
        hidden_gems.sort(key=lambda x: x['gem_probability'], reverse=True)
        
        return jsonify({
            'hidden_gems': hidden_gems[:limit],
            'total_scanned': processed_count,
            'gems_found': len(hidden_gems),
            'min_probability_threshold': min_probability,
            'scan_summary': {
                'ultra_high_potential': len([g for g in hidden_gems if g['gem_probability'] > 0.8]),
                'high_potential': len([g for g in hidden_gems if 0.7 <= g['gem_probability'] <= 0.8]),
                'moderate_potential': len([g for g in hidden_gems if 0.6 <= g['gem_probability'] < 0.7])
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gems/train', methods=['POST'])
def train_gem_detector():
    """Train or retrain the hidden gem detector"""
    if not GEM_DETECTOR_AVAILABLE or not gem_detector:
        return jsonify({'error': 'Hidden Gem Detector not available'}), 503
    
    try:
        # Convert analyzer coins to format suitable for training
        coins_data = []
        for coin in analyzer.coins:
            coin_data = {
                'symbol': coin.symbol,
                'name': coin.name,
                'price': coin.price,
                'price_change_24h': {'usd': getattr(coin, 'price_change_24h', 0)},
                'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
                'market_cap': getattr(coin, 'market_cap', 'N/A'),
                'total_volume': getattr(coin, 'total_volume', 'N/A'),
                'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
                'status': getattr(coin, 'status', 'current')
            }
            coins_data.append(coin_data)
        
        print(f"🏋️ Training Hidden Gem Detector with {len(coins_data)} coins...")
        
        # Create training dataset
        training_df, labels = gem_detector.create_training_dataset(coins_data)
        
        # Train model
        result = gem_detector.train_model(training_df, labels)
        
        if result:
            # Save the model
            gem_detector.save_model()
            
            return jsonify({
                'success': True,
                'training_result': {
                    'accuracy': result['accuracy'],
                    'auc_score': result['auc_score'],
                    'cv_mean': result['cv_mean'],
                    'cv_std': result['cv_std'],
                    'total_coins_trained': len(coins_data),
                    'hidden_gems_identified': result['hidden_gems_found'],
                    'model_type': result['model_type'],
                    'top_features': sorted(
                        result['feature_importance'].items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:10]
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Training failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/gems/status')
def get_gem_detector_status():
    """Get status of the hidden gem detector"""
    status = {
        'available': GEM_DETECTOR_AVAILABLE,
        'model_loaded': gem_detector.model_loaded if gem_detector else False,
        'service_status': 'available' if GEM_DETECTOR_AVAILABLE else 'unavailable'
    }
    
    if gem_detector and GEM_DETECTOR_AVAILABLE:
        model_info = gem_detector.get_model_info()
        status.update(model_info)
        # Add multi-agent status
        status['multi_agent_enabled'] = gem_detector.multi_agent_enabled
        if gem_detector.multi_agent_enabled:
            status['agent_count'] = len(gem_detector.orchestrator.agents)
    
    return jsonify(status)

@app.route('/api/agents/analyze/<symbol>')
def analyze_with_agents(symbol):
    """
    PHASE 4: Analyze a coin using the multi-agent system
    This is the new comprehensive analysis endpoint
    """
    if not GEM_DETECTOR_AVAILABLE or not gem_detector:
        return jsonify({'error': 'Gem Detector not available'}), 503
    
    if not gem_detector.multi_agent_enabled:
        return jsonify({'error': 'Multi-agent system not available'}), 503
    
    try:
        # Find the coin
        coin = None
        for c in analyzer.coins:
            if c.symbol.upper() == symbol.upper():
                coin = c
                break
        
        if not coin:
            return jsonify({'error': f'Coin {symbol} not found'}), 404
        
        # Convert coin object to dictionary for analysis
        coin_data = {
            'symbol': coin.symbol,
            'name': coin.name,
            'price': coin.price,
            'price_change_24h': getattr(coin, 'price_change_24h', 0),
            'price_change_7d': 0,  # Not currently available
            'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
            'market_cap': float(str(getattr(coin, 'market_cap', '0')).replace('$', '').replace(',', '').replace('N/A', '0')),
            'volume_24h': float(str(getattr(coin, 'total_volume', '0')).replace('$', '').replace(',', '').replace('N/A', '0')),
            'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
            'status': getattr(coin, 'status', 'current')
        }
        
        # Run async analysis
        analysis = run_async(gem_detector.analyze_with_agents(coin_data))
        
        if analysis is None:
            return jsonify({'error': 'Analysis failed'}), 500
        
        # Add coin info
        analysis['coin'] = {
            'symbol': coin.symbol,
            'name': coin.name,
            'price': coin.price,
            'market_cap_rank': coin_data['market_cap_rank'],
            'attractiveness_score': coin_data['attractiveness_score']
        }
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Agent analysis error for {symbol}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/agents/scan')
def scan_with_agents():
    """
    PHASE 4: Scan coins using multi-agent system
    More comprehensive but slower than regular gem scan
    """
    if not GEM_DETECTOR_AVAILABLE or not gem_detector:
        return jsonify({'error': 'Gem Detector not available'}), 503
    
    if not gem_detector.multi_agent_enabled:
        return jsonify({'error': 'Multi-agent system not available'}), 503
    
    try:
        limit = int(request.args.get('limit', 10))  # Lower default due to cost
        min_score = float(request.args.get('min_score', 0.6))
        
        agent_gems = []
        processed_count = 0
        
        # Scan fewer coins with agents due to cost
        scan_count = min(50, len(analyzer.coins))
        
        for coin in analyzer.coins[:scan_count]:
            try:
                processed_count += 1
                
                # Convert coin object to dictionary
                coin_data = {
                    'symbol': coin.symbol,
                    'name': coin.name,
                    'price': coin.price,
                    'price_change_24h': getattr(coin, 'price_change_24h', 0),
                    'price_change_7d': 0,
                    'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
                    'market_cap': float(str(getattr(coin, 'market_cap', '0')).replace('$', '').replace(',', '').replace('N/A', '0')),
                    'volume_24h': float(str(getattr(coin, 'total_volume', '0')).replace('$', '').replace(',', '').replace('N/A', '0')),
                    'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
                }
                
                # Run async analysis
                analysis = run_async(gem_detector.analyze_with_agents(coin_data))
                
                if analysis and analysis.get('gem_score', 0) / 100 >= min_score:
                    gem_info = {
                        'symbol': coin.symbol,
                        'name': coin.name,
                        'price': coin.price,
                        'market_cap_rank': coin_data['market_cap_rank'],
                        'gem_score': analysis['gem_score'],
                        'gem_probability': analysis['gem_probability'],
                        'confidence': analysis['confidence'],
                        'risk_level': analysis['risk_level'],
                        'recommendation': analysis['recommendation'],
                        'key_strengths': analysis['key_strengths'][:3],
                        'multi_agent': True
                    }
                    agent_gems.append(gem_info)
                    
            except Exception as e:
                logger.error(f"Error scanning {coin.symbol} with agents: {e}")
                continue
        
        # Sort by gem score
        agent_gems.sort(key=lambda x: x['gem_score'], reverse=True)
        
        return jsonify({
            'agent_gems': agent_gems[:limit],
            'total_scanned': processed_count,
            'gems_found': len(agent_gems),
            'min_score_threshold': min_score,
            'scan_summary': {
                'ultra_high_potential': len([g for g in agent_gems if g['gem_score'] > 80]),
                'high_potential': len([g for g in agent_gems if 70 <= g['gem_score'] <= 80]),
                'moderate_potential': len([g for g in agent_gems if 60 <= g['gem_score'] < 70])
            }
        })
        
    except Exception as e:
        logger.error(f"Agent scan error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/agents/metrics')
def get_agent_metrics():
    """Get metrics from the multi-agent orchestrator"""
    if not GEM_DETECTOR_AVAILABLE or not gem_detector:
        return jsonify({'error': 'Gem Detector not available'}), 503
    
    if not gem_detector.multi_agent_enabled:
        return jsonify({'error': 'Multi-agent system not available'}), 503
    
    try:
        metrics = gem_detector.orchestrator.get_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting agent metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/analyze')
def analyze_portfolio():
    """
    PHASE 5: Analyze portfolio and generate recommendations
    Uses multi-agent system to evaluate multiple coins and suggest optimal allocation
    """
    if not GEM_DETECTOR_AVAILABLE or not gem_detector:
        return jsonify({'error': 'Gem Detector not available'}), 503
    
    if not gem_detector.multi_agent_enabled or not gem_detector.orchestrator:
        return jsonify({'error': 'Multi-agent system not available'}), 503
    
    try:
        from ml.portfolio_manager import PortfolioManager
        
        # Get parameters
        max_coins = int(request.args.get('max_coins', 20))
        min_score = float(request.args.get('min_score', 6.0))
        
        # Get top coins by attractiveness score
        candidates = sorted(
            analyzer.coins,
            key=lambda x: x.attractiveness_score,
            reverse=True
        )[:max_coins]
        
        # Filter by minimum score and price
        candidates = [
            c for c in candidates 
            if c.attractiveness_score >= min_score and c.price and c.price > 0
        ]
        
        # Convert to dict format
        coins_data = []
        for coin in candidates:
            market_cap_value = getattr(coin, 'market_cap', 0)
            if isinstance(market_cap_value, str):
                market_cap_value = float(market_cap_value.replace('£', '').replace('$', '').replace(',', '').replace('N/A', '0'))
            
            volume_value = getattr(coin, 'total_volume', 0)
            if isinstance(volume_value, str):
                volume_value = float(volume_value.replace('£', '').replace('$', '').replace(',', '').replace('N/A', '0'))
            
            coins_data.append({
                'symbol': coin.symbol,
                'name': coin.name,
                'price': coin.price,
                'price_change_24h': getattr(coin, 'price_change_24h', 0),
                'price_change_7d': 0,
                'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
                'market_cap': market_cap_value,
                'volume_24h': volume_value,
                'attractiveness_score': coin.attractiveness_score,
                'status': getattr(coin, 'status', 'current')
            })
        
        # Run portfolio analysis
        portfolio_mgr = PortfolioManager(gem_detector.orchestrator)
        
        recommendation = run_async(
            portfolio_mgr.analyze_portfolio(coins_data, max_coins)
        )
        
        # Convert to JSON-serializable format
        result = {
            'summary': {
                'total_analyzed': len(coins_data),
                'gems_found': recommendation.total_gems_found,
                'market_sentiment': recommendation.market_sentiment,
                'portfolio_risk': round(recommendation.portfolio_risk_score, 1),
                'diversification': round(recommendation.diversification_score, 1)
            },
            'recommendations': {
                'buy': recommendation.buy_recommendations,
                'hold': recommendation.hold_recommendations,
                'avoid': recommendation.avoid_recommendations
            },
            'top_opportunities': recommendation.top_opportunities,
            'risk_warnings': recommendation.risk_warnings,
            'allocation_strategy': recommendation.allocation_strategy
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Portfolio analysis error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/gems/top/<int:count>')
def get_top_hidden_gems(count):
    """Get top N hidden gems with full analysis"""
    if not GEM_DETECTOR_AVAILABLE or not gem_detector:
        return jsonify({'error': 'Hidden Gem Detector not available'}), 503
    
    try:
        count = min(count, 50)  # Limit to prevent overload
        
        analyzed_gems = []
        
        for coin in analyzer.coins[:count * 3]:  # Scan 3x requested to find best
            try:
                coin_data = {
                    'symbol': coin.symbol,
                    'name': coin.name,
                    'price': coin.price,
                    'price_change_24h': {'usd': getattr(coin, 'price_change_24h', 0)},
                    'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
                    'market_cap': getattr(coin, 'market_cap', 'N/A'),
                    'total_volume': getattr(coin, 'total_volume', 'N/A'),
                    'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
                    'status': getattr(coin, 'status', 'current')
                }
                
                prediction = gem_detector.predict_hidden_gem(coin_data)
                
                if prediction and prediction['gem_probability'] > 0.5:
                    gem_analysis = {
                        'symbol': coin.symbol,
                        'name': coin.name,
                        'price': coin.price,
                        'market_cap_rank': coin_data['market_cap_rank'],
                        'gem_probability': prediction['gem_probability'],
                        'gem_score': prediction['gem_score'],
                        'confidence': prediction['confidence'],
                        'risk_level': prediction['risk_level'],
                        'risk_score': prediction['risk_score'],
                        'recommendation': prediction['recommendation'],
                        'key_strengths': prediction['key_strengths'],
                        'key_weaknesses': prediction['key_weaknesses'],
                        'top_features': prediction['top_features'],
                        'feature_breakdown': prediction['feature_breakdown']
                    }
                    analyzed_gems.append(gem_analysis)
                    
            except Exception as e:
                print(f"Error analyzing {coin.symbol}: {e}")
                continue
        
        # Sort by gem score and return top N
        analyzed_gems.sort(key=lambda x: x['gem_score'], reverse=True)
        top_gems = analyzed_gems[:count]
        
        return jsonify({
            'top_hidden_gems': top_gems,
            'requested_count': count,
            'found_count': len(top_gems),
            'analysis_summary': {
                'average_gem_score': sum(g['gem_score'] for g in top_gems) / len(top_gems) if top_gems else 0,
                'risk_distribution': {
                    level: len([g for g in top_gems if g['risk_level'] == level])
                    for level in ['Low', 'Medium', 'High', 'Very High']
                }
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status/idle')
def get_idle_status():
    """Get current idle time and auto-shutdown status"""
    idle_time = time.time() - last_request_time
    return jsonify({
        'auto_shutdown_enabled': shutdown_enabled,
        'idle_timeout_seconds': IDLE_TIMEOUT,
        'idle_timeout_minutes': IDLE_TIMEOUT // 60,
        'current_idle_seconds': int(idle_time),
        'current_idle_minutes': round(idle_time / 60, 1),
        'time_until_shutdown_seconds': max(0, int(IDLE_TIMEOUT - idle_time)),
        'time_until_shutdown_minutes': max(0, round((IDLE_TIMEOUT - idle_time) / 60, 1)),
        'will_shutdown_in': f"{max(0, int(IDLE_TIMEOUT - idle_time))}s" if idle_time < IDLE_TIMEOUT else "imminent",
        'last_activity': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_request_time))
    })

@app.route('/health')
def health():
    """Simple health check endpoint for load balancers and smoke tests"""
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()}), 200

@app.route('/api/health')
def api_health():
    """Enhanced health check for SIEM monitoring"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'components': {
            'analyzer': analyzer is not None,
            'ml_pipeline': ML_AVAILABLE,
            'gem_detector': GEM_DETECTOR_AVAILABLE,
            'rl_detector': False  # integrated into gem_detector
        },
        'uptime_hours': (time.time() - start_time) / 3600 if 'start_time' in globals() else 0
    }), 200

@app.route('/api/metrics')
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
            'total_coins': len(analyzer.coins) if analyzer else 0,
            'ml_available': ML_AVAILABLE,
            'gem_detector_available': GEM_DETECTOR_AVAILABLE,
            'rl_detector_available': False  # integrated into gem_detector
        }
    }), 200

@app.route('/api/debug/coins')
def debug_coins():
    """Debug endpoint to see what coins are currently loaded"""
    try:
        coins_list = [{'symbol': coin.symbol, 'name': coin.name, 'price': coin.price} 
                     for coin in analyzer.coins[:50]]  # First 50 coins
        return jsonify({
            'total_coins': len(analyzer.coins),
            'coins': coins_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================================
# Live Trading Engine Routes
# ========================================

@app.route('/api/trades/status')
def trading_status():
    """Get trading engine status — budget, active trades, kill switch state"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return jsonify(engine.get_status()), 200
    except Exception as e:
        logger.error(f"Trading status error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/trades/pending')
def pending_proposals():
    """Get all pending trade proposals awaiting approval"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return jsonify({"proposals": engine.get_pending_proposals()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/trades/history')
def trade_history():
    """Get executed trade history"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return jsonify({"trades": engine.get_trade_history()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/trades/approve/<proposal_id>')
def approve_trade(proposal_id):
    """Approve a trade proposal (called from email link)"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        result = engine.approve_trade(proposal_id)

        # Return a nice HTML page for email click-through
        if result.get("success"):
            return f"""
            <html>
            <body style="font-family: -apple-system, sans-serif; background: #0d0d14; color: #e2e8f0; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;">
                <div style="text-align: center; background: #151520; padding: 40px; border-radius: 16px; border: 1px solid #2d3748; max-width: 400px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">✅</div>
                    <h2 style="margin: 0 0 8px; color: #48bb78;">Trade Approved & Executed</h2>
                    <p style="color: #a0aec0; margin: 0 0 16px;">
                        {result.get('side', '').upper()} {result.get('quantity', 0):.6f} {result.get('symbol', '')}
                        @ £{result.get('price', 0):.6f}
                    </p>
                    <p style="color: #a0aec0; font-size: 13px;">Amount: £{result.get('amount_gbp', 0):.4f}</p>
                    <a href="/trades" style="display: inline-block; margin-top: 16px; padding: 10px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 8px;">View Trades</a>
                </div>
            </body>
            </html>
            """
        else:
            return f"""
            <html>
            <body style="font-family: -apple-system, sans-serif; background: #0d0d14; color: #e2e8f0; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;">
                <div style="text-align: center; background: #151520; padding: 40px; border-radius: 16px; border: 1px solid #2d3748; max-width: 400px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                    <h2 style="margin: 0 0 8px; color: #ecc94b;">Could Not Execute</h2>
                    <p style="color: #a0aec0;">{result.get('error', 'Unknown error')}</p>
                    <a href="/trades" style="display: inline-block; margin-top: 16px; padding: 10px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 8px;">View Trades</a>
                </div>
            </body>
            </html>
            """
    except Exception as e:
        logger.error(f"Approve trade error: {e}")
        return f"<html><body><h2>Error: {e}</h2></body></html>", 500


@app.route('/api/trades/reject/<proposal_id>')
def reject_trade(proposal_id):
    """Reject a trade proposal (called from email link)"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        result = engine.reject_trade(proposal_id)

        return f"""
        <html>
        <body style="font-family: -apple-system, sans-serif; background: #0d0d14; color: #e2e8f0; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;">
            <div style="text-align: center; background: #151520; padding: 40px; border-radius: 16px; border: 1px solid #2d3748; max-width: 400px;">
                <div style="font-size: 48px; margin-bottom: 16px;">❌</div>
                <h2 style="margin: 0 0 8px; color: #fc8181;">Trade Rejected</h2>
                <p style="color: #a0aec0;">Proposal {proposal_id} has been rejected. No money spent.</p>
                <a href="/trades" style="display: inline-block; margin-top: 16px; padding: 10px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 8px;">View Trades</a>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Reject trade error: {e}")
        return f"<html><body><h2>Error: {e}</h2></body></html>", 500


@app.route('/api/trades/propose', methods=['POST'])
def propose_trade_api():
    """Manually propose a trade (from dashboard or agent)"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()

        data = request.json
        required = ['symbol', 'side', 'amount_gbp', 'current_price', 'reason', 'confidence']
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        result = engine.propose_trade(
            symbol=data['symbol'],
            side=data['side'],
            amount_gbp=float(data['amount_gbp']),
            current_price=float(data['current_price']),
            reason=data['reason'],
            confidence=int(data['confidence']),
            recommendation=data.get('recommendation', 'BUY'),
        )
        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        logger.error(f"Propose trade error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/trades/kill-switch', methods=['POST'])
def toggle_kill_switch():
    """Activate or deactivate the trading kill switch"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()

        action = request.json.get('action', 'activate')
        if action == 'activate':
            result = engine.activate_kill_switch()
        else:
            result = engine.deactivate_kill_switch()
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/trades/auto-evaluate', methods=['POST'])
def auto_evaluate_trade():
    """
    Run the trading agent on a coin's analysis to decide if it's worth a real trade.
    Requires the coin to already have agent_analysis.
    """
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()

        data = request.json
        symbol = data.get('symbol', '').upper()
        analysis = data.get('analysis', {})
        current_price = float(data.get('current_price', 0))

        if not symbol or not analysis or not current_price:
            return jsonify({"error": "Missing symbol, analysis, or current_price"}), 400

        remaining = engine.get_remaining_budget()
        if remaining <= 0:
            return jsonify({"error": "Daily budget exhausted", "remaining": 0}), 400

        # Run trading agent evaluation
        import asyncio
        from ml.agents.official.trading_agent import evaluate_trade

        loop = asyncio.new_event_loop()
        decision = loop.run_until_complete(
            evaluate_trade(symbol, analysis, current_price, remaining)
        )
        loop.close()

        if not decision.get("success"):
            return jsonify(decision), 500

        # Parse the trading agent's decision
        import json as _json
        import re

        decision_text = decision.get("decision_raw", "")
        parsed = None

        # Try JSON extraction
        json_match = re.search(r'\{.*\}', decision_text, re.DOTALL)
        if json_match:
            try:
                parsed = _json.loads(json_match.group())
            except _json.JSONDecodeError:
                pass

        if parsed and parsed.get("should_trade"):
            conviction = parsed.get("conviction", 0)
            allocation_pct = parsed.get("suggested_allocation_pct", 50)
            amount = remaining * (allocation_pct / 100)
            amount = min(amount, remaining)

            # Propose the trade
            result = engine.propose_trade(
                symbol=symbol,
                side=parsed.get("side", "buy"),
                amount_gbp=round(amount, 4),
                current_price=current_price,
                reason=parsed.get("reasoning", "Agent recommended trade"),
                confidence=conviction,
                recommendation=data.get("recommendation", "BUY"),
            )
            result["agent_decision"] = parsed
            return jsonify(result), 200
        else:
            return jsonify({
                "success": True,
                "should_trade": False,
                "reason": parsed.get("reasoning", "Agent decided not to trade") if parsed else "Could not parse decision",
                "risk_note": parsed.get("risk_note", "") if parsed else "",
            }), 200

    except Exception as e:
        logger.error(f"Auto-evaluate error: {e}")
        return jsonify({"error": str(e)}), 500


# ========================================
# Trade Journal & RL Learning Routes
# ========================================

@app.route('/trades')
def trades_page():
    """Trade journal page for reporting trades and RL learning"""
    return render_template('trades.html')

@app.route('/api/rl/report-trade', methods=['POST'])
def report_trade():
    """Report a trade outcome to teach the RL system"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['symbol', 'entry_price', 'exit_price', 'days_held']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        symbol = data['symbol'].upper()
        entry_price = float(data['entry_price'])
        exit_price = float(data['exit_price'])
        days_held = int(data['days_held'])
        notes = data.get('notes', '')
        
        # Calculate profit
        profit_pct = ((exit_price - entry_price) / entry_price) * 100
        
        # Get gem detector to access RL
        if not GEM_DETECTOR_AVAILABLE or not gem_detector:
            return jsonify({
                'error': 'RL not available. Gem detector not initialized.'
            }), 503
        
        # Teach RL (we'll use simplified features for now)
        # In a real scenario, you'd want to store the original analysis features
        features = {
            'profit_indicator': 1.0 if profit_pct > 0 else -1.0,
            'days_held': days_held / 100.0,  # Normalize
            'entry_price': entry_price / 10000.0,  # Normalize
        }
        
        result = gem_detector.learn_from_outcome(
            symbol=symbol,
            entry_price=entry_price,
            current_price=exit_price,
            days_held=days_held,
            features=features,
            notes=notes
        )
        
        if not result:
            return jsonify({
                'error': 'RL learning not available'
            }), 503
        
        # Store trade info for display (add to result)
        result['symbol'] = symbol
        result['entry_price'] = entry_price
        result['exit_price'] = exit_price
        result['profit_pct'] = round(profit_pct, 2)
        result['days_held'] = days_held
        result['notes'] = notes
        result['new_success_rate'] = round(result['new_success_rate'] * 100, 2)
        
        logger.info(f"Trade reported: {symbol} {profit_pct:+.1f}% over {days_held} days")
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid number format: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error reporting trade: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rl/stats')
def rl_stats():
    """Get RL learning statistics"""
    try:
        if not GEM_DETECTOR_AVAILABLE or not gem_detector:
            return jsonify({
                'success': False,
                'error': 'RL not available'
            }), 503
        
        # Import simple_rl to get stats
        from ml.simple_rl import simple_rl_learner
        
        stats = simple_rl_learner.get_stats()
        stats['success'] = True
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting RL stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/rl/trades')
def rl_trades():
    """Get recent trades from RL history"""
    try:
        from ml.simple_rl import simple_rl_learner
        
        # Get trade history
        recent_trades = simple_rl_learner.trade_history[-20:]  # Last 20 trades
        
        # Enhance with calculated values
        enhanced_trades = []
        for trade in reversed(recent_trades):  # Most recent first
            enhanced_trade = trade.copy()
            # Add any missing fields for display
            enhanced_trade['symbol'] = enhanced_trade.get('symbol', 'N/A')
            enhanced_trades.append(enhanced_trade)
        
        return jsonify({
            'success': True,
            'trades': enhanced_trades
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'trades': []
        }), 500

if __name__ == '__main__':
    # Simple, configurable runner
    # Defaults: host 0.0.0.0 so it can be reached externally on a VM,
    #           port 5001 (avoids macOS Control Center conflict),
    #           debug False (safer for public exposure)
    host = os.environ.get('HOST', '0.0.0.0')
    try:
        port = int(os.environ.get('PORT', '5001'))
    except ValueError:
        port = 5001
    debug = os.environ.get('DEBUG', 'false').lower() in ('1', 'true', 'yes')

    app.run(host=host, port=port, debug=debug)
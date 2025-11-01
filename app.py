#!/usr/bin/env python3

from flask import Flask, render_template, jsonify, request
import sys
import os
import json
import asyncio
import logging

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
GEM_DETECTOR_AVAILABLE = False

# Initialize RL components  
rl_detector = None
RL_DETECTOR_AVAILABLE = False

# Initialize data pipeline for symbol management
data_pipeline = None
SYMBOLS_AVAILABLE = False

def initialize_ml():
    """Try to initialize ML components in a separate function"""
    global ml_pipeline, ml_service, ML_AVAILABLE
    print("🔧 Attempting to initialize ML components...")
    try:
        from ml.training_pipeline import CryptoMLPipeline
        from services.ml_service import MLService
        
        print("📦 ML imports successful")
        ml_pipeline = CryptoMLPipeline()
        ml_service = MLService()
        ML_AVAILABLE = True
        
        print("🤖 ML objects created")
        
        # Try to load existing model
        try:
            ml_pipeline.load_existing_model()
            print("✅ ML model loaded successfully")
        except Exception as e:
            print(f"⚠️ ML model not available: {e}")
        
        print("🎉 ML components initialized successfully")
        return True
    except Exception as e:
        print(f"❌ ML components not available: {e}")
        import traceback
        traceback.print_exc()
        ML_AVAILABLE = False
        ml_pipeline = None
        ml_service = None
        return False

def initialize_data_pipeline():
    """Try to initialize data pipeline for symbol management"""
    global data_pipeline, SYMBOLS_AVAILABLE
    print("🔧 Attempting to initialize data pipeline...")
    try:
        from ml.data_pipeline import CryptoDataPipeline
        
        print("📦 Data pipeline imports successful")
        data_pipeline = CryptoDataPipeline()
        SYMBOLS_AVAILABLE = True
        
        print("🎉 Data pipeline initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Data pipeline not available: {e}")
        SYMBOLS_AVAILABLE = False
        return False

def initialize_gem_detector():
    """Initialize the enhanced hidden gem detector"""
    global gem_detector, GEM_DETECTOR_AVAILABLE
    print("🔧 Attempting to initialize Enhanced Hidden Gem Detector...")
    try:
        from ml.enhanced_gem_detector import HiddenGemDetector
        
        print("📦 Hidden Gem Detector imports successful")
        gem_detector = HiddenGemDetector()
        
        # Try to load existing model
        if gem_detector.load_model():
            print("✅ Hidden Gem Detector model loaded successfully")
            GEM_DETECTOR_AVAILABLE = True
        else:
            print("🏋️ No existing model found, will train on first use...")
            GEM_DETECTOR_AVAILABLE = True  # Available for training
        
        print("🎉 Enhanced Hidden Gem Detector initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Hidden Gem Detector not available: {e}")
        import traceback
        traceback.print_exc()
        GEM_DETECTOR_AVAILABLE = False
        return False

def initialize_rl_detector():
    """Initialize the RL-enhanced gem detector"""
    global rl_detector, RL_DETECTOR_AVAILABLE
    print("🔧 Attempting to initialize RL Detector...")
    try:
        from ml.rl_integration import RLLiveTrading
        
        print("📦 RL Detector imports successful")
        
        # Try to load existing RL model
        model_path = os.path.join(project_root, 'models', 'rl_model.pkl')
        if os.path.exists(model_path):
            rl_detector = RLLiveTrading(model_filepath=model_path)
            print("✅ RL model loaded successfully")
        else:
            rl_detector = RLLiveTrading()  # Start fresh
            print("🧠 Starting with new RL agent")
        
        RL_DETECTOR_AVAILABLE = True
        print("🎉 RL Detector initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ RL Detector not available: {e}")
        RL_DETECTOR_AVAILABLE = False
        return False
        gem_detector = None
        return False

def fetch_and_add_new_symbol_data(symbol: str):
    """Fetch data for a newly added symbol and add it to the live data"""
    try:
        import requests
        import json
        from datetime import datetime
        
        print(f"🔄 Fetching data for new symbol: {symbol}")
        
        # First, get the CoinGecko ID for the symbol
        if not data_pipeline:
            raise Exception("Data pipeline not available")
        
        # Use asyncio to get the coingecko ID
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            validation_result = loop.run_until_complete(data_pipeline.validate_symbol(symbol))
        finally:
            loop.close()
        
        if validation_result['status'] != 'valid':
            raise Exception(f"Symbol {symbol} is not valid")
        
        coingecko_id = validation_result['coingecko_id']
        
        # Fetch current market data for the symbol
        coingecko_url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}"
        params = {
            'localization': 'false',
            'tickers': 'false',
            'market_data': 'true',
            'community_data': 'false',
            'developer_data': 'false',
            'sparkline': 'false'
        }
        
        response = requests.get(coingecko_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Create coin data structure
        market_data = data.get('market_data', {})
        new_coin_data = {
            "item": {
                "id": coingecko_id,
                "name": data.get('name', symbol),
                "symbol": symbol.upper(),
                "status": "current",
                "attractiveness_score": 6.0,  # Default score for new additions
                "investment_highlights": ["Recently added symbol"],
                "risk_level": "medium",
                "market_cap_rank": market_data.get('market_cap_rank'),
                "price_btc": None,
                "data": {
                    "price": market_data.get('current_price', {}).get('usd', 0),
                    "price_btc": market_data.get('current_price', {}).get('btc'),
                    "price_change_percentage_24h": {
                        "usd": market_data.get('price_change_percentage_24h', 0)
                    },
                    "market_cap": f"${market_data.get('market_cap', {}).get('usd', 0):,}" if market_data.get('market_cap', {}).get('usd') else "N/A",
                    "total_volume": f"${market_data.get('total_volume', {}).get('usd', 0):,}" if market_data.get('total_volume', {}).get('usd') else "N/A",
                    "content": None,
                    "source": "coingecko"
                }
            }
        }
        
        # Load existing data
        live_data_file = "data/live_api.json"
        try:
            with open(live_data_file, 'r') as f:
                live_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            live_data = {"last_updated": datetime.now().isoformat(), "sources": ["coingecko"], "coins": []}
        
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
            
            print(f"✅ Successfully added {symbol} data to live data file")
        else:
            print(f"ℹ️ Symbol {symbol} already exists in live data")
            
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        raise

app = Flask(__name__, 
           template_folder='src/web/templates',
           static_folder='src/web/static')

# Favorites functionality
FAVORITES_FILE = "favorites.json"

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
        with open(FAVORITES_FILE, 'w') as f:
            json.dump(favorites, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving favorites: {e}")
        return False

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize ML components immediately
# Try to initialize ML components on startup
print("🚀 Starting CryptoApp...")
try:
    initialize_ml()
except Exception as e:
    print(f"⚠️ Startup ML initialization failed: {e}")

# Try to initialize data pipeline on startup
try:
    initialize_data_pipeline()
except Exception as e:
    print(f"⚠️ Startup data pipeline initialization failed: {e}")

# Try to initialize gem detector on startup
try:
    initialize_gem_detector()
except Exception as e:
    print(f"⚠️ Startup gem detector initialization failed: {e}")

# Try to initialize RL detector on startup
try:
    initialize_rl_detector()
except Exception as e:
    print(f"⚠️ Startup RL detector initialization failed: {e}")

# Initialize analyzer with live data (after all other components)
analyzer = CryptoAnalyzer(data_file='data/live_api.json')
print(f"📊 ML_AVAILABLE: {ML_AVAILABLE}")
print(f"🤖 ml_pipeline: {ml_pipeline}")
print(f"🔧 ml_service: {ml_service}")
print(f"� GEM_DETECTOR_AVAILABLE: {GEM_DETECTOR_AVAILABLE}")
print(f"🔍 gem_detector: {gem_detector}")
print(f"�📊 Analyzer loaded {len(analyzer.coins)} coins from data/live_api.json")

# Print RL status
print(f"🧠 RL_DETECTOR_AVAILABLE: {RL_DETECTOR_AVAILABLE}")
print(f"🤖 rl_detector: {rl_detector}")

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
    """Get coins data"""
    try:
        # Get recently added symbols from data pipeline
        recently_added_coins = []
        if SYMBOLS_AVAILABLE and data_pipeline:
            for symbol in data_pipeline.supported_symbols:
                # Find this symbol in the analyzer's coins
                matching_coin = next((coin for coin in analyzer.coins if coin.symbol == symbol), None)
                if matching_coin and matching_coin not in recently_added_coins:
                    recently_added_coins.append(matching_coin)
        
        # Get more coins initially to account for price filtering
        low_cap_coins = analyzer.get_low_cap_coins(25)
        
        # Combine recently added coins with low cap coins (prioritize recently added)
        selected_coins = []
        
        # First, add recently added coins under £100
        for coin in recently_added_coins:
            if (coin not in selected_coins and 
                (not coin.price or coin.price <= 125.0)):  # Under £100 equivalent
                selected_coins.append(coin)
        
        # Then add low cap coins under £100 (avoiding duplicates)
        for coin in low_cap_coins:
            if (coin not in selected_coins and len(selected_coins) < 25 and
                (not coin.price or coin.price <= 125.0)):  # Under £100 equivalent
                selected_coins.append(coin)
        
        # If still need more coins, get affordable top coins by score
        if len(selected_coins) < 15:
            # Get all coins sorted by attractiveness score
            all_affordable_coins = [coin for coin in analyzer.coins 
                                  if not coin.price or coin.price <= 125.0]
            all_affordable_coins.sort(key=lambda x: x.attractiveness_score, reverse=True)
            
            for coin in all_affordable_coins:
                if coin not in selected_coins and len(selected_coins) < 25:
                    selected_coins.append(coin)
                if len(selected_coins) >= 25:
                    break
        
        coins_data = []
        for coin in selected_coins[:8]:  # Show only 8 coins for dashboard layout
                
            coins_data.append({
                'symbol': coin.symbol,
                'name': coin.name,
                'score': coin.attractiveness_score,
                'price': coin.price,
                'price_change_24h': coin.price_change_24h or 0,
                'market_cap_rank': coin.market_cap_rank,
                'recently_added': coin.symbol in [c.symbol for c in recently_added_coins]  # Flag for UI
            })
        
        # Integrate hidden gems data into coins
        for coin_data in coins_data:
            # Add hidden gem detection
            coin_data['is_hidden_gem'] = False
            coin_data['gem_probability'] = 0.0
            coin_data['gem_reason'] = None
            
            if GEM_DETECTOR_AVAILABLE and gem_detector:
                try:
                    symbol = coin_data['symbol']
                    matching_coin = next((c for c in analyzer.coins if c.symbol == symbol), None)
                    if matching_coin:
                        coin_dict = {
                            'symbol': matching_coin.symbol,
                            'price': matching_coin.price or 0,
                            'volume_24h': getattr(matching_coin, 'volume_24h', 0),
                            'price_change_24h': matching_coin.price_change_24h or 0,
                            'market_cap': getattr(matching_coin, 'market_cap', 0),
                            'market_cap_rank': matching_coin.market_cap_rank
                        }
                        gem_result = gem_detector.predict_hidden_gem(coin_dict)
                        if gem_result:
                            coin_data['is_hidden_gem'] = gem_result.get('prediction', 0) > 0.6
                            coin_data['gem_probability'] = gem_result.get('prediction', 0)
                            if coin_data['is_hidden_gem']:
                                coin_data['gem_reason'] = gem_result.get('recommendation', 'High potential detected')
                except Exception as e:
                    logging.warning(f"Gem detection failed for {coin_data['symbol']}: {e}")

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
                        print(f"✅ Added data for new symbols: {added_symbols}")
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
    """Get all favorite coins with their current data and ML predictions"""
    try:
        favorites = load_favorites()
        favorite_coins = []
        
        for symbol in favorites:
            # Find the coin in our current data
            for coin in analyzer.coins:
                if coin.symbol.upper() == symbol.upper():
                    coin_data = {
                        'symbol': coin.symbol,
                        'name': coin.name,
                        'price': coin.price,
                        'price_change_24h': coin.price_change_24h,
                        'score': coin.attractiveness_score,
                        'market_cap': coin.market_cap,
                        'market_cap_rank': coin.market_cap_rank,
                        'ml_prediction': None
                    }
                    
                    # Add ML prediction if model is available
                    if ML_AVAILABLE and ml_pipeline and ml_pipeline.model_loaded:
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
                            coin_data['ml_prediction'] = {
                                'prediction_percentage': ml_result['prediction_percentage'],
                                'confidence': ml_result['confidence'],
                                'direction': 'bullish' if ml_result['prediction'] > 0 else 'bearish' if ml_result['prediction'] < 0 else 'stable'
                            }
                            
                            # Enhance attractiveness score with ML prediction
                            ml_weight = 0.3  # 30% weight for ML prediction
                            original_weight = 0.7  # 70% weight for original score
                            
                            # Normalize ML prediction to 0-10 scale
                            ml_contribution = min(10, max(0, 5 + ml_result['prediction_percentage'] / 2))
                            
                            coin_data['enhanced_score'] = (
                                original_weight * coin.attractiveness_score + 
                                ml_weight * ml_contribution
                            )
                            
                        except Exception as ml_error:
                            logging.warning(f"ML prediction failed for favorite {coin.symbol}: {ml_error}")
                            coin_data['enhanced_score'] = coin.attractiveness_score
                    else:
                        coin_data['enhanced_score'] = coin.attractiveness_score
                    
                    favorite_coins.append(coin_data)
                    break
        
        ml_status = ML_AVAILABLE and ml_pipeline and ml_pipeline.model_loaded
        print(f"🔍 Favorites API - ML Enhanced: {ml_status}, Favorite coins count: {len(favorite_coins)}")
        
        return jsonify({
            'favorites': favorite_coins,
            'ml_enhanced': ml_status
        })
    except Exception as e:
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
        print(f"🔍 ML Status Check - ML_AVAILABLE: {ML_AVAILABLE}, ml_pipeline: {ml_pipeline}")
        
        if not ML_AVAILABLE or ml_pipeline is None:
            return jsonify({
                'ml_status': {
                    'error': 'ML components not available',
                    'ML_AVAILABLE': ML_AVAILABLE,
                    'ml_pipeline_exists': ml_pipeline is not None
                },
                'service_available': False
            })
            
        status = ml_pipeline.get_status()
        print(f"📊 ML Status: {status}")
        return jsonify({
            'ml_status': status,
            'service_available': True
        })
    except Exception as e:
        print(f"❌ ML Status Error: {e}")
        return jsonify({
            'ml_status': {'error': str(e)},
            'service_available': False
        }), 500

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
    """Get coins data enhanced with ML predictions"""
    try:
        # Get recently added symbols from data pipeline (same logic as /api/coins)
        recently_added_coins = []
        if SYMBOLS_AVAILABLE and data_pipeline:
            for symbol in data_pipeline.supported_symbols:
                # Find this symbol in the analyzer's coins
                matching_coin = next((coin for coin in analyzer.coins if coin.symbol == symbol), None)
                if matching_coin and matching_coin not in recently_added_coins:
                    recently_added_coins.append(matching_coin)
        
        # Get more coins initially to account for price filtering
        low_cap_coins = analyzer.get_low_cap_coins(25)
        
        # Combine recently added coins with low cap coins (prioritize recently added)
        selected_coins = []
        
        # First, add recently added coins under £100
        for coin in recently_added_coins:
            if (coin not in selected_coins and 
                (not coin.price or coin.price <= 125.0)):  # Under £100 equivalent
                selected_coins.append(coin)
        
        # Then add low cap coins under £100 (avoiding duplicates)
        for coin in low_cap_coins:
            if (coin not in selected_coins and len(selected_coins) < 25 and
                (not coin.price or coin.price <= 125.0)):  # Under £100 equivalent
                selected_coins.append(coin)
        
        # If still need more coins, get affordable top coins by score
        if len(selected_coins) < 15:
            # Get all coins sorted by attractiveness score
            all_affordable_coins = [coin for coin in analyzer.coins 
                                  if not coin.price or coin.price <= 125.0]
            all_affordable_coins.sort(key=lambda x: x.attractiveness_score, reverse=True)
            
            for coin in all_affordable_coins:
                if coin not in selected_coins and len(selected_coins) < 25:
                    selected_coins.append(coin)
                if len(selected_coins) >= 25:
                    break
        
        coins_data = []
        for coin in selected_coins[:8]:  # Show only 8 coins for dashboard layout
            coin_data = {
                'symbol': coin.symbol,
                'name': coin.name,
                'score': coin.attractiveness_score,
                'price': coin.price,
                'price_change_24h': coin.price_change_24h or 0,
                'market_cap_rank': coin.market_cap_rank,
                'recently_added': coin.symbol in [c.symbol for c in recently_added_coins],  # Add this flag
                'ml_prediction': None
            }
            
            # Add ML prediction if model is available
            if ML_AVAILABLE and ml_pipeline and ml_pipeline.model_loaded:
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
                    coin_data['ml_prediction'] = {
                        'prediction_percentage': ml_result['prediction_percentage'],
                        'confidence': ml_result['confidence'],
                        'direction': 'bullish' if ml_result['prediction'] > 0 else 'bearish' if ml_result['prediction'] < 0 else 'stable'
                    }
                    
                    # Enhance attractiveness score with ML prediction
                    ml_weight = 0.3  # 30% weight for ML prediction
                    original_weight = 0.7  # 70% weight for original score
                    
                    # Normalize ML prediction to 0-10 scale
                    ml_contribution = min(10, max(0, 5 + ml_result['prediction_percentage'] / 2))
                    
                    coin_data['enhanced_score'] = (
                        original_weight * coin.attractiveness_score + 
                        ml_weight * ml_contribution
                    )
                    
                except Exception as ml_error:
                    logging.warning(f"ML prediction failed for {coin.symbol}: {ml_error}")
                    coin_data['enhanced_score'] = coin.attractiveness_score
            else:
                coin_data['enhanced_score'] = coin.attractiveness_score
            
            coins_data.append(coin_data)
        
        # Sort by enhanced score
        coins_data.sort(key=lambda x: x['enhanced_score'], reverse=True)
        
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
        if not ML_AVAILABLE or ml_pipeline is None:
            return jsonify({
                'success': False,
                'error': 'ML components not available'
            }), 503
            
        if not os.path.exists('models'):
            os.makedirs('models')
        
        # Create sample data for training
        sample_data_path = 'models/sample_training_data.csv'
        sample_df = ml_pipeline.create_sample_data(symbol="BTC", days=30)
        sample_df.to_csv(sample_data_path, index=False)
        
        # Train the model
        training_result = ml_pipeline.train_model(sample_data_path)
        
        return jsonify({
            'success': True,
            'message': 'Model trained successfully',
            'training_result': training_result,
            'status': ml_pipeline.get_status()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
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
        
        # Use asyncio to run the async search function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(data_pipeline.search_symbols(query, limit))
        finally:
            loop.close()
        
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
        
        # Use asyncio to run the async validation function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            validation_result = loop.run_until_complete(data_pipeline.validate_symbol(symbol))
        finally:
            loop.close()
        
        if validation_result['status'] == 'valid':
            return jsonify({
                'success': True,
                'symbol': validation_result['symbol'],
                'coingecko_id': validation_result['coingecko_id'],
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
        
        # Use asyncio to run the async add function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(data_pipeline.add_new_symbol(symbol))
        finally:
            loop.close()
        
        if success:
            # Immediately fetch data for the new symbol and add it to live data
            try:
                fetch_and_add_new_symbol_data(symbol)
                return jsonify({
                    'success': True,
                    'symbol': symbol,
                    'message': f'Symbol {symbol} added successfully and data fetched'
                })
            except Exception as e:
                # Symbol was added to pipeline but data fetch failed
                return jsonify({
                    'success': True,
                    'symbol': symbol,
                    'message': f'Symbol {symbol} added successfully. Data will be available on next refresh.',
                    'data_fetch_error': str(e)
                })
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
    
    return jsonify(status)

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

# ========================================
# RL-Enhanced Gem Detection Endpoints
# ========================================

@app.route('/api/rl/analyze_coin/<symbol>', methods=['GET'])
def rl_analyze_coin(symbol):
    """Analyze a coin with RL-enhanced gem detection"""
    if not RL_DETECTOR_AVAILABLE or not rl_detector:
        return jsonify({
            'error': 'RL Detector not available',
            'message': 'RL system is not initialized'
        }), 503
    
    try:
        # Get coin data
        coin = None
        for c in analyzer.coins:
            if c.symbol.upper() == symbol.upper():
                coin = c
                break
        
        if not coin:
            return jsonify({'error': f'Coin {symbol} not found'}), 404
        
        # Convert coin object to dict
        coin_data = {
            'symbol': coin.symbol,
            'name': coin.name,
            'price': coin.price,
            'market_cap': coin.market_cap,
            'price_change_24h': coin.price_change_24h
        }
        
        # Get market context
        market_context = {
            'total_market_cap': sum(float(c.market_cap or 0) for c in analyzer.coins if c.market_cap),
            'market_sentiment': 'neutral',  # Could be enhanced with sentiment analysis
            'btc_dominance': 45.0  # Could be calculated from actual data
        }
        
        # Analyze with RL
        analysis = rl_detector.analyze_live_coin(coin_data, market_context)
        
        return jsonify({
            'symbol': symbol.upper(),
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'rl_enabled': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rl/scan_gems', methods=['GET'])
def rl_scan_gems():
    """Scan for hidden gems using RL-enhanced detection"""
    if not RL_DETECTOR_AVAILABLE or not rl_detector:
        return jsonify({
            'error': 'RL Detector not available', 
            'message': 'RL system is not initialized'
        }), 503
    
    try:
        limit = int(request.args.get('limit', 20))
        min_confidence = float(request.args.get('min_confidence', 0.6))
        
        rl_gems = []
        processed = 0
        
        # Get market context
        market_context = {
            'total_market_cap': sum(float(c.market_cap or 0) for c in analyzer.coins if c.market_cap),
            'market_sentiment': 'neutral',
            'btc_dominance': 45.0
        }
        
        for coin in analyzer.coins:
            try:
                # Convert coin object to dict
                coin_data = {
                    'symbol': coin.symbol,
                    'name': coin.name,
                    'price': coin.price,
                    'market_cap': coin.market_cap,
                    'volume_24h': coin.total_volume,
                    'price_change_24h': coin.price_change_24h,
                    'price_change_7d': 0  # Not available in current model
                }
                
                # Analyze with RL
                analysis = rl_detector.analyze_live_coin(coin_data, market_context)
                
                # Filter by RL recommendation and confidence
                if (analysis['rl_recommendation'] == 'buy' and 
                    analysis['rl_confidence'] >= min_confidence):
                    
                    rl_gems.append({
                        'symbol': coin.symbol,
                        'name': coin.name,
                        'price': coin.price,
                        'market_cap': coin.market_cap,
                        'rl_confidence': analysis['rl_confidence'],
                        'rl_recommendation': analysis['rl_recommendation'],
                        'gem_score': analysis.get('gem_score', 0),
                        'risk_level': analysis['risk_assessment']['risk_level'],
                        'position_size_percent': analysis['position_size_percent'],
                        'timing_score': analysis['timing_signals']['timing_score'],
                        'rl_reasoning': analysis['rl_reasoning']
                    })
                
                processed += 1
                
            except Exception as e:
                print(f"Error analyzing {coin.symbol} with RL: {e}")
                continue
        
        # Sort by RL confidence
        rl_gems.sort(key=lambda x: x['rl_confidence'], reverse=True)
        
        return jsonify({
            'rl_gems': rl_gems[:limit],
            'stats': {
                'total_processed': processed,
                'gems_found': len(rl_gems),
                'high_confidence': len([g for g in rl_gems if g['rl_confidence'] > 0.8]),
                'medium_confidence': len([g for g in rl_gems if 0.6 <= g['rl_confidence'] <= 0.8]),
                'low_risk': len([g for g in rl_gems if g['risk_level'] == 'Low']),
                'medium_risk': len([g for g in rl_gems if g['risk_level'] == 'Medium']),
                'high_risk': len([g for g in rl_gems if g['risk_level'] == 'High'])
            },
            'filters': {
                'min_confidence': min_confidence,
                'limit': limit
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rl/performance', methods=['GET'])
def rl_performance():
    """Get RL agent performance metrics"""
    if not RL_DETECTOR_AVAILABLE or not rl_detector:
        return jsonify({
            'error': 'RL Detector not available',
            'message': 'RL system is not initialized'
        }), 503
    
    try:
        performance = rl_detector.get_rl_performance_summary()
        
        return jsonify({
            'performance': performance,
            'status': 'active' if RL_DETECTOR_AVAILABLE else 'inactive',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rl/record_trade', methods=['POST'])
def rl_record_trade():
    """Record a trade outcome for RL learning"""
    if not RL_DETECTOR_AVAILABLE or not rl_detector:
        return jsonify({
            'error': 'RL Detector not available',
            'message': 'RL system is not initialized'
        }), 503
    
    try:
        data = request.get_json()
        
        required_fields = ['symbol', 'entry_price', 'current_price', 'entry_date']
        if not all(field in data for field in required_fields):
            return jsonify({
                'error': 'Missing required fields',
                'required': required_fields
            }), 400
        
        # Parse entry date
        entry_date = datetime.fromisoformat(data['entry_date'].replace('Z', '+00:00'))
        
        # Record trade outcome
        trade_record = rl_detector.record_trade_outcome(
            symbol=data['symbol'],
            entry_price=float(data['entry_price']),
            current_price=float(data['current_price']),
            entry_date=entry_date
        )
        
        return jsonify({
            'message': 'Trade recorded successfully',
            'trade_record': trade_record,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rl/train', methods=['POST'])
def rl_train():
    """Train RL agent on historical data"""
    if not RL_DETECTOR_AVAILABLE or not rl_detector:
        return jsonify({
            'error': 'RL Detector not available',
            'message': 'RL system is not initialized'  
        }), 503
    
    try:
        from ml.rl_integration import RLCryptoTrainer
        
        trainer = RLCryptoTrainer()
        
        # Use sample training data
        csv_path = os.path.join(project_root, 'models', 'sample_training_data.csv')
        
        if not os.path.exists(csv_path):
            return jsonify({
                'error': 'Training data not found',
                'message': f'Please ensure {csv_path} exists'
            }), 404
        
        results = trainer.train_from_csv(csv_path)
        
        # Save trained model
        model_path = os.path.join(project_root, 'models', 'rl_model.pkl')
        rl_detector.save_rl_model(model_path)
        
        return jsonify({
            'message': 'RL training completed',
            'results': results,
            'model_saved': model_path,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run the Flask app on port 5001 to avoid macOS Control Center conflict
    app.run(debug=True, host='127.0.0.1', port=5001)
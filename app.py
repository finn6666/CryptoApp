#!/usr/bin/env python3
"""
Flask web application for Low Cap Crypto Analyzer
Focused on discovering hidden gems in small cap cryptocurrencies
"""

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

from core.crypto_analyzer import CryptoAnalyzer, CoinStatus
from core.live_data_fetcher import fetch_and_update_data
from datetime import datetime

# Initialize ML components as None by default
ml_pipeline = None
ml_service = None
ML_AVAILABLE = False

def initialize_ml():
    """Try to initialize ML components in a separate function"""
    global ml_pipeline, ml_service, ML_AVAILABLE
    print("🔧 Attempting to initialize ML components...")
    try:
        from training_pipeline import CryptoMLPipeline
        from ml_service import MLService
        
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

app = Flask(__name__, template_folder='src/web/templates')

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

# Initialize analyzer with live data
analyzer = CryptoAnalyzer(data_file='data/live_api.json')

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize ML components immediately
print("🚀 Starting ML initialization...")
initialize_ml()
print(f"📊 ML_AVAILABLE: {ML_AVAILABLE}")
print(f"🤖 ml_pipeline: {ml_pipeline}")
print(f"🔧 ml_service: {ml_service}")

@app.route('/')
def index():
    """Serve the main page"""
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
        # Get low cap coins first, then fill with top coins if needed
        low_cap_coins = analyzer.get_low_cap_coins(10)
        
        if len(low_cap_coins) < 10:
            # Fill remaining slots with top coins
            remaining_slots = 10 - len(low_cap_coins)
            top_coins = analyzer.get_top_coins(remaining_slots)
            # Remove any duplicates
            for coin in top_coins:
                if coin not in low_cap_coins:
                    low_cap_coins.append(coin)
                    if len(low_cap_coins) >= 10:
                        break
        
        coins_data = []
        for coin in low_cap_coins[:10]:
            coins_data.append({
                'symbol': coin.symbol,
                'name': coin.name,
                'score': coin.attractiveness_score,
                'price': coin.price,
                'price_change_24h': coin.price_change_24h or 0,
                'market_cap_rank': coin.market_cap_rank
            })
        
        return jsonify({
            'coins': coins_data,
            'last_updated': datetime.now().isoformat(),
            'cache_expires_in': 300  # 5 minutes
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
        # Get regular coins data
        low_cap_coins = analyzer.get_low_cap_coins(10)
        
        if len(low_cap_coins) < 10:
            remaining_slots = 10 - len(low_cap_coins)
            top_coins = analyzer.get_top_coins(remaining_slots)
            for coin in top_coins:
                if coin not in low_cap_coins:
                    low_cap_coins.append(coin)
                    if len(low_cap_coins) >= 10:
                        break
        
        coins_data = []
        for coin in low_cap_coins[:10]:
            coin_data = {
                'symbol': coin.symbol,
                'name': coin.name,
                'score': coin.attractiveness_score,
                'price': coin.price,
                'price_change_24h': coin.price_change_24h or 0,
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

if __name__ == '__main__':
    # Run the Flask app on port 5001 to avoid macOS Control Center conflict
    app.run(debug=True, host='127.0.0.1', port=5001)
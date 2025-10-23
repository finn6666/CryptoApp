from flask import Flask, render_template, jsonify, request
import json
from ..core.crypto_analyzer import CryptoAnalyzer, CoinStatus
from ..core.live_data_fetcher import fetch_and_update_data
import threading
import time
from datetime import datetime
import os

app = Flask(__name__)

# Global analyzer instance
analyzer = None
last_update_time = 0
CACHE_DURATION = 300  # 5 minutes cache to avoid excessive API calls
FAVORITES_FILE = "favorites.json"  # File to store user favorites

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

def initialize_analyzer():
    """Initialize the crypto analyzer"""
    global analyzer
    analyzer = CryptoAnalyzer()

def should_refresh_data():
    """Check if data should be refreshed (5-minute cooldown)"""
    global last_update_time
    current_time = time.time()
    return (current_time - last_update_time) > CACHE_DURATION

def refresh_data_if_needed():
    """Refresh data only if cache has expired"""
    global last_update_time
    
    if should_refresh_data():
        try:
            print(f"🔄 [{datetime.now()}] Refreshing crypto data (user requested)...")
            fetch_and_update_data()
            if analyzer:
                analyzer.load_data()
            last_update_time = time.time()
            print(f"✅ [{datetime.now()}] Data refreshed successfully")
            return True
        except Exception as e:
            print(f"❌ [{datetime.now()}] Error refreshing data: {e}")
            return False
    else:
        time_left = int(CACHE_DURATION - (time.time() - last_update_time))
        print(f"⏱️  Using cached data (refresh available in {time_left}s)")
        return False

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/coins')
def get_coins():
    """API endpoint to get cryptocurrency data"""
    try:
        if not analyzer:
            return jsonify({'error': 'Analyzer not initialized'}), 500
        
        # Refresh data if needed (user-triggered)
        refresh_data_if_needed()
        
        # Get trending coins
        trending = analyzer.get_trending_coins()[:10]
        
        # Convert to JSON-serializable format
        coins_data = []
        for coin in trending:
            coins_data.append({
                'symbol': coin.symbol,
                'name': coin.name,
                'price': coin.price,
                'price_change_24h': coin.price_change_24h_usd,
                'score': coin.attractiveness_score,
                'market_cap': coin.market_cap,
                'volume': coin.total_volume
            })
        
        return jsonify({
            'coins': coins_data,
            'last_updated': datetime.fromtimestamp(last_update_time).isoformat() if last_update_time > 0 else 'Never',
            'total_coins': len(analyzer.coins),
            'cache_expires_in': max(0, int(CACHE_DURATION - (time.time() - last_update_time))) if last_update_time > 0 else 0
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh', methods=['POST'])
def force_refresh():
    """Force refresh data (bypasses cache)"""
    global last_update_time
    try:
        print(f"🔄 [{datetime.now()}] Force refresh requested...")
        fetch_and_update_data()
        if analyzer:
            analyzer.load_data()
        last_update_time = time.time()
        print(f"✅ [{datetime.now()}] Force refresh completed")
        
        return jsonify({
            'success': True,
            'message': 'Data refreshed successfully',
            'last_updated': datetime.fromtimestamp(last_update_time).isoformat(),
            'total_coins': len(analyzer.coins) if analyzer else 0
        })
    except Exception as e:
        print(f"❌ [{datetime.now()}] Force refresh failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/refresh')
def refresh_data():
    """Manually refresh cryptocurrency data"""
    try:
        fetch_and_update_data()
        if analyzer:
            analyzer.load_data()
        return jsonify({'success': True, 'message': 'Data refreshed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get portfolio statistics"""
    try:
        if not analyzer:
            return jsonify({'error': 'Analyzer not initialized'}), 500
        
        total_coins = len(analyzer.coins)
        current_coins = len(analyzer.filter_by_status(CoinStatus.CURRENT))
        high_potential = len(analyzer.get_high_potential_coins())
        trending_up = len([c for c in analyzer.coins if c.price_change_24h_usd and c.price_change_24h_usd > 0])
        
        return jsonify({
            'total_coins': total_coins,
            'current_coins': current_coins,
            'high_potential': high_potential,
            'trending_up': trending_up,
            'last_updated': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for cloud deployment"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'analyzer_loaded': analyzer is not None
    })

@app.route('/api/favorites')
def get_favorites():
    """Get all favorite coins with their current data"""
    try:
        favorites = load_favorites()
        return jsonify({
            'status': 'success',
            'favorites': favorites,
            'count': len(favorites)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/favorites/add', methods=['POST'])
def add_favorite():
    """Add a coin to favorites"""
    try:
        data = request.get_json()
        coin_id = data.get('coin_id')
        coin_name = data.get('coin_name', 'Unknown')
        
        if not coin_id:
            return jsonify({
                'status': 'error',
                'message': 'coin_id is required'
            }), 400
        
        favorites = load_favorites()
        
        # Check if already in favorites
        for fav in favorites:
            if fav['id'] == coin_id:
                return jsonify({
                    'status': 'info',
                    'message': 'Coin already in favorites'
                })
        
        # Add to favorites
        favorites.append({
            'id': coin_id,
            'name': coin_name,
            'added_at': datetime.now().isoformat()
        })
        
        if save_favorites(favorites):
            return jsonify({
                'status': 'success',
                'message': f'{coin_name} added to favorites'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to save favorites'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/favorites/remove', methods=['POST'])
def remove_favorite():
    """Remove a coin from favorites"""
    try:
        data = request.get_json()
        coin_id = data.get('coin_id')
        
        if not coin_id:
            return jsonify({
                'status': 'error',
                'message': 'coin_id is required'
            }), 400
        
        favorites = load_favorites()
        original_count = len(favorites)
        
        # Remove from favorites
        favorites = [fav for fav in favorites if fav['id'] != coin_id]
        
        if len(favorites) < original_count:
            if save_favorites(favorites):
                return jsonify({
                    'status': 'success',
                    'message': 'Coin removed from favorites'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to save favorites'
                }), 500
        else:
            return jsonify({
                'status': 'info',
                'message': 'Coin not found in favorites'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    # Initialize analyzer first
    print("🔧 Initializing crypto analyzer...")
    initialize_analyzer()
    
    # Fetch initial data
    print("📊 Fetching initial cryptocurrency data...")
    try:
        fetch_and_update_data()
        if analyzer:
            analyzer.load_data()
            print(f"✅ Loaded {len(analyzer.coins)} coins successfully")
        last_update_time = time.time()  # Set initial update time
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch initial data: {e}")
        print("📱 App will continue with existing data if available")
    
    print("🔄 Data will refresh automatically when users visit the page")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=8080, debug=False)
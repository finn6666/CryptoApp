#!/usr/bin/env python3
"""
Flask web application for Low Cap Crypto Analyzer
Focused on discovering hidden gems in small cap cryptocurrencies
"""

from flask import Flask, render_template, jsonify, request
import sys
import os
import json

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from core.crypto_analyzer import CryptoAnalyzer, CoinStatus
from core.live_data_fetcher import fetch_and_update_data
from datetime import datetime

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
        trending_up = len([coin for coin in analyzer.coins if coin.price_change_24h_usd and coin.price_change_24h_usd > 0])
        
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
                'price_change_24h': coin.price_change_24h_usd or 0,
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
    """Get all favorite coins with their current data"""
    try:
        favorites = load_favorites()
        favorite_coins = []
        
        for symbol in favorites:
            # Find the coin in our current data
            for coin in analyzer.coins:
                if coin.symbol.upper() == symbol.upper():
                    favorite_coins.append({
                        'symbol': coin.symbol,
                        'name': coin.name,
                        'price': coin.price,
                        'price_change_24h': coin.price_change_24h_usd,
                        'score': coin.attractiveness_score,
                        'market_cap': coin.market_cap,
                        'market_cap_rank': coin.market_cap_rank
                    })
                    break
        
        return jsonify({'favorites': favorite_coins})
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

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True, host='127.0.0.1', port=5000)
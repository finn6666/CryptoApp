#!/usr/bin/env python3
"""
Flask web application for Crypto Investment Analyzer
"""

from flask import Flask, render_template, jsonify
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from core.crypto_analyzer import CryptoAnalyzer, CoinStatus
from datetime import datetime

app = Flask(__name__, template_folder='src/web/templates')

# Initialize analyzer with correct data path
analyzer = CryptoAnalyzer(data_file='data/api.json')

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
        # Get top coins sorted by score
        top_coins = analyzer.get_top_coins(50)  # Show top 50
        
        coins_data = []
        for coin in top_coins:
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
    """Force refresh of data"""
    try:
        # Reload local data
        analyzer.load_local_data()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True, host='127.0.0.1', port=5000)
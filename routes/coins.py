"""
Coin data, favorites, stats, and refresh routes.
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request

from services.app_state import (
    analyzer, load_favorites, save_favorites, run_async,
    _build_gem_analysis, _sanitize_ai_text, parse_market_cap, parse_volume,
    fetch_and_add_new_symbol_data,
    STABLECOINS, MIN_PRICE, MAX_PRICE, CACHE_EXPIRY_SECONDS,
    agent_analysis_cache,
)
import services.app_state as state

logger = logging.getLogger(__name__)

coins_bp = Blueprint('coins', __name__)


# ─── Helper: build coin dict for AI analysis ─────────────────

def _prepare_coin_dict(coin):
    """Convert a coin object to a dict suitable for gem/agent analysis."""
    return {
        'symbol': coin.symbol,
        'name': coin.name,
        'price': coin.price or 0,
        'market_cap': parse_market_cap(getattr(coin, 'market_cap', 0)),
        'volume_24h': parse_volume(getattr(coin, 'total_volume', 0)),
        'price_change_24h': coin.price_change_24h or 0,
        'market_cap_rank': coin.market_cap_rank,
    }


def _coin_selection(favorites_upper, pool_size=50):
    """Select coins excluding favorites, stablecoins, and price filters.
    Shared between /api/coins and /api/coins/enhanced.
    """
    recently_added_coins = []
    if state.SYMBOLS_AVAILABLE and state.data_pipeline:
        for symbol in state.data_pipeline.supported_symbols:
            match = next((c for c in state.analyzer.coins if c.symbol == symbol), None)
            if match and match not in recently_added_coins:
                recently_added_coins.append(match)

    low_cap_coins = state.analyzer.get_low_cap_coins(pool_size)

    selected = []

    for coin in recently_added_coins:
        if coin.symbol.upper() in favorites_upper:
            continue
        if (coin not in selected and coin.symbol not in STABLECOINS
                and coin.price and MIN_PRICE <= coin.price <= MAX_PRICE):
            selected.append(coin)

    for coin in low_cap_coins:
        if coin.symbol.upper() in favorites_upper:
            continue
        if (coin not in selected and len(selected) < pool_size
                and coin.symbol not in STABLECOINS
                and coin.price and MIN_PRICE <= coin.price <= MAX_PRICE):
            selected.append(coin)

    if len(selected) < 20:
        affordable = [c for c in state.analyzer.coins
                      if (c.symbol.upper() not in favorites_upper
                          and c.symbol not in STABLECOINS
                          and c.price and MIN_PRICE <= c.price <= MAX_PRICE)]
        affordable.sort(key=lambda x: x.attractiveness_score, reverse=True)
        for coin in affordable:
            if coin not in selected and len(selected) < pool_size:
                selected.append(coin)
            if len(selected) >= pool_size:
                break

    return selected, recently_added_coins


def _run_gem_analysis(coin_data_dict, coin_data_out):
    """Run gem detector analysis and update coin_data_out in-place."""
    if not state.GEM_DETECTOR_AVAILABLE or not state.gem_detector:
        return False
    try:
        gem_result = state.gem_detector.predict_hidden_gem(coin_data_dict)
        analysis, ai_sentiment, enhanced = _build_gem_analysis(gem_result)
        if analysis:
            coin_data_out['ai_analysis'] = analysis
            if ai_sentiment:
                coin_data_out['ai_sentiment'] = ai_sentiment
            coin_data_out['enhanced_score'] = enhanced
            return True
    except Exception as e:
        logger.warning(f"Gem detection failed for {coin_data_dict.get('symbol')}: {e}")
    return False


def _run_ml_fallback(coin, coin_data_out):
    """Run basic ML prediction as last-resort fallback."""
    if not state.ML_AVAILABLE or not state.ml_pipeline or not state.ml_pipeline.model_loaded:
        return False
    try:
        features = {
            'price_change_1h': coin.price_change_24h or 0,
            'price_change_24h': coin.price_change_24h or 0,
            'volume_change_24h': 0, 'market_cap_change_24h': 0,
            'rsi': 50, 'macd': 0,
            'moving_avg_7d': coin.price or 0,
            'moving_avg_30d': coin.price or 0,
        }
        ml_result = state.ml_pipeline.predict_with_validation(features)
        pred_pct = ml_result.get('prediction_percentage', 0)
        direction = 'bullish' if pred_pct > 2 else 'bearish' if pred_pct < -2 else 'neutral'
        recommendation = 'BUY' if pred_pct > 2 else 'HOLD' if pred_pct > -2 else 'AVOID'
        coin_data_out['ai_analysis'] = {
            'recommendation': recommendation,
            'confidence': f"{ml_result.get('confidence', 0)*100:.0f}%",
            'summary': f"ML predicts {direction} trend with {abs(pred_pct):.1f}% expected movement.",
            'prediction': f"{pred_pct:+.1f}%",
            'analysis_type': 'ML Model',
        }
        return True
    except Exception as e:
        logger.warning(f"ML prediction failed for {coin.symbol}: {e}")
    return False


def _run_agent_analysis(coin, coin_data_out):
    """Run multi-agent analysis on a single coin (uses cache)."""
    symbol = coin_data_out['symbol']
    cache_key = f"agent_{symbol}"
    if cache_key in agent_analysis_cache:
        cached_data, ts = agent_analysis_cache[cache_key]
        if (datetime.now().timestamp() - ts) < CACHE_EXPIRY_SECONDS:
            coin_data_out['agent_analysis'] = cached_data
            logger.info(f"Using cached agent analysis for {symbol}")
            return

    mc = parse_market_cap(getattr(coin, 'market_cap', 0))
    vol = parse_volume(getattr(coin, 'total_volume', 0))

    agent_coin_data = {
        'symbol': coin.symbol,
        'name': coin.name,
        'price': coin.price or 0,
        'price_change_24h': coin.price_change_24h or 0,
        'price_change_7d': 0,
        'market_cap_rank': coin.market_cap_rank or 999,
        'market_cap': mc,
        'volume_24h': vol,
        'attractiveness_score': coin.attractiveness_score or 5.0,
        'status': getattr(coin, 'status', 'current'),
    }

    try:
        result = run_async(state.gem_detector.analyze_with_agents(agent_coin_data))
        if result:
            coin_data_out['agent_analysis'] = result
            agent_analysis_cache[cache_key] = (result, datetime.now().timestamp())
            logger.info(f"Multi-agent analysis completed for {symbol}: {result.get('gem_score')}%")
    except Exception as e:
        logger.warning(f"Multi-agent analysis failed for {symbol}: {e}")


# ─── Routes ───────────────────────────────────────────────────

@coins_bp.route('/api/stats')
def get_stats():
    from src.core.crypto_analyzer import CoinStatus
    try:
        total = len(state.analyzer.coins)
        current = len(state.analyzer.filter_by_status(CoinStatus.CURRENT))
        high_potential = len(state.analyzer.get_high_potential_coins())
        trending_up = len([c for c in state.analyzer.coins if c.price_change_24h and c.price_change_24h > 0])
        return jsonify({'total_coins': total, 'current_coins': current, 'high_potential': high_potential, 'trending_up': trending_up})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@coins_bp.route('/api/coins')
def get_coins():
    """Get coins data (excluding favorites) with integrated multi-agent analysis."""
    try:
        run_agents = request.args.get('agents', 'true').lower() == 'true'
        limit = int(request.args.get('limit', 20))

        favorites = load_favorites()
        favorites_upper = [f.upper() for f in favorites]
        selected, recently_added = _coin_selection(favorites_upper)

        coins_data = []
        for coin in selected[:limit]:
            coins_data.append({
                'symbol': coin.symbol,
                'name': coin.name,
                'score': coin.attractiveness_score,
                'price': coin.price,
                'price_change_24h': coin.price_change_24h or 0,
                'market_cap_rank': coin.market_cap_rank,
                'recently_added': coin.symbol in [c.symbol for c in recently_added],
                'ai_analysis': None,
                'ai_sentiment': None,
                'agent_analysis': None,
            })

        # Add AI analysis
        for cd in coins_data:
            matching = next((c for c in state.analyzer.coins if c.symbol == cd['symbol']), None)
            if not matching:
                continue

            coin_dict = _prepare_coin_dict(matching)
            ai_score = min(10, matching.attractiveness_score / 10)
            done = _run_gem_analysis(coin_dict, cd)
            if done:
                ai_score = cd.get('enhanced_score', ai_score)
            if not done:
                _run_ml_fallback(matching, cd)
            cd['enhanced_score'] = min(10, ai_score)

            # Multi-agent analysis
            if run_agents and state.GEM_DETECTOR_AVAILABLE and state.gem_detector and state.gem_detector.multi_agent_enabled:
                _run_agent_analysis(matching, cd)

        return jsonify({
            'coins': coins_data,
            'last_updated': datetime.now().isoformat(),
            'cache_expires_in': 300,
            'recently_added_count': len(recently_added),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@coins_bp.route('/api/coins/enhanced')
def get_enhanced_coins():
    """Get coins data enhanced with ML predictions (excluding favorites)."""
    try:
        favorites = load_favorites()
        favorites_upper = [f.upper() for f in favorites]
        selected, recently_added = _coin_selection(favorites_upper)

        coins_data = []
        for coin in selected[:20]:
            cd = {
                'symbol': coin.symbol,
                'name': coin.name,
                'score': min(10, coin.attractiveness_score / 10),
                'price': coin.price,
                'price_change_24h': coin.price_change_24h or 0,
                'market_cap_rank': coin.market_cap_rank,
                'recently_added': coin.symbol in [c.symbol for c in recently_added],
                'ai_analysis': None,
                'enhanced_score': min(10, coin.attractiveness_score / 10),
            }
            coin_dict = _prepare_coin_dict(coin)
            _run_gem_analysis(coin_dict, cd)
            coins_data.append(cd)

        # Opt-in agent analysis
        run_agents = request.args.get('agents', 'false').lower() == 'true'
        if run_agents and state.GEM_DETECTOR_AVAILABLE and state.gem_detector and state.gem_detector.multi_agent_enabled:
            for cd in coins_data:
                matching = next((c for c in selected if c.symbol == cd['symbol']), None)
                if matching:
                    _run_agent_analysis(matching, cd)

        coins_data.sort(key=lambda x: x['enhanced_score'], reverse=True)

        return jsonify({
            'coins': coins_data,
            'last_updated': datetime.now().isoformat(),
            'ml_enhanced': state.ML_AVAILABLE and state.ml_pipeline and state.ml_pipeline.model_loaded,
            'recently_added_count': len(recently_added),
            'cache_expires_in': 300,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@coins_bp.route('/api/refresh', methods=['POST'])
def force_refresh():
    from src.core.live_data_fetcher import fetch_and_update_data
    try:
        live_data = fetch_and_update_data()
        if live_data:
            if state.SYMBOLS_AVAILABLE and state.data_pipeline:
                current_symbols = [c.symbol for c in state.analyzer.coins]
                for symbol in state.data_pipeline.supported_symbols:
                    if symbol not in current_symbols:
                        try:
                            fetch_and_add_new_symbol_data(symbol)
                        except Exception as e:
                            logger.warning(f"Could not fetch data for {symbol}: {e}")
            state.analyzer.load_data()
            return jsonify({'success': True, 'message': 'Live data refreshed successfully'})
        return jsonify({'success': False, 'error': 'Failed to fetch live data'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@coins_bp.route('/api/market/conditions')
def get_market_conditions():
    try:
        all_coins = state.analyzer.get_all_coins()
        if not all_coins:
            return jsonify({'opportunity_level': 'UNKNOWN', 'opportunity_score': 50, 'opportunity_percentage': 50, 'message': 'Insufficient data', 'indicators': {}})

        total = len(all_coins)
        avg_change = sum(c.price_change_24h or 0 for c in all_coins) / max(total, 1)
        nano = sum(1 for c in all_coins if (c.market_cap_rank or 999) > 500)
        micro = sum(1 for c in all_coins if 300 < (c.market_cap_rank or 999) <= 500)
        low = sum(1 for c in all_coins if 100 < (c.market_cap_rank or 999) <= 300)

        score = 50
        score += ((nano * 3) + (micro * 2) + low) / max(total, 1) * 10
        score += abs(avg_change) * 1.5
        if avg_change > 5:
            score += 15
        elif avg_change > 2:
            score += 10
        elif avg_change < -5:
            score += 5
        score = max(0, min(100, score))

        if score >= 75:
            lvl, msg = 'EXCELLENT', '🟢 Excellent Opportunity - Strong market conditions'
        elif score >= 60:
            lvl, msg = 'GOOD', '🟢 Good Opportunity - Favorable conditions'
        elif score >= 40:
            lvl, msg = 'MODERATE', '🟡 Moderate Opportunity - Standard conditions'
        elif score >= 25:
            lvl, msg = 'LIMITED', '⚪ Limited Opportunity - Quiet market'
        else:
            lvl, msg = 'LOW', '⚪ Low Opportunity - Waiting for movement'

        return jsonify({
            'opportunity_level': lvl, 'opportunity_score': int(score), 'opportunity_percentage': int(score),
            'message': msg,
            'indicators': {'total_coins': total, 'avg_price_change_24h': round(avg_change, 2), 'nano_caps': nano, 'micro_caps': micro, 'low_caps': low, 'market_cap_diversity': f"{nano}/{micro}/{low}"},
        })
    except Exception as e:
        logger.error(f"Market conditions error: {e}")
        return jsonify({'error': str(e), 'risk_level': 'UNKNOWN', 'risk_score': 50, 'risk_percentage': 50}), 500


# ─── Favorites ────────────────────────────────────────────────

@coins_bp.route('/api/favorites')
def get_favorites():
    """Get all favorite coins with current data and comprehensive AI analysis."""
    try:
        from src.core.live_data_fetcher import fetch_specific_coin

        favorites = load_favorites()
        favorite_coins = []
        missing_coins = []

        for symbol in favorites:
            found = False
            for coin in state.analyzer.coins:
                if coin.symbol.upper() == symbol.upper():
                    found = True
                    cd = {
                        'symbol': coin.symbol, 'name': coin.name,
                        'price': coin.price, 'price_change_24h': coin.price_change_24h,
                        'score': min(10, coin.attractiveness_score / 10),
                        'market_cap': coin.market_cap, 'market_cap_rank': coin.market_cap_rank,
                        'ai_analysis': None, 'enhanced_score': min(10, coin.attractiveness_score / 10),
                        'ai_sentiment': None,
                    }
                    coin_dict = _prepare_coin_dict(coin)
                    done = _run_gem_analysis(coin_dict, cd)
                    if not done:
                        _run_ml_fallback(coin, cd)
                    favorite_coins.append(cd)
                    break

            if not found:
                logger.info(f"Fetching {symbol} directly from API (not in low-cap list)")
                try:
                    raw = fetch_specific_coin(symbol)
                    if raw:
                        cd = {
                            'symbol': raw['symbol'], 'name': raw['name'],
                            'price': raw['current_price'],
                            'price_change_24h': raw['price_change_percentage_24h'],
                            'score': 5.0, 'market_cap': raw['market_cap'],
                            'market_cap_rank': raw['market_cap_rank'],
                            'ai_analysis': None, 'enhanced_score': 5.0, 'ai_sentiment': None,
                        }
                        coin_dict = {
                            'symbol': raw['symbol'], 'name': raw['name'],
                            'price': raw['current_price'] or 0,
                            'market_cap': raw['market_cap'] or 0,
                            'volume_24h': raw['total_volume'] or 0,
                            'price_change_24h': raw['price_change_percentage_24h'] or 0,
                            'market_cap_rank': raw['market_cap_rank'],
                        }
                        _run_gem_analysis(coin_dict, cd)
                        favorite_coins.append(cd)
                    else:
                        missing_coins.append(symbol)
                except Exception as e:
                    missing_coins.append(symbol)
                    logger.error(f"Error fetching {symbol}: {e}")

        # Opt-in agent analysis for favorites
        run_agents = request.args.get('agents', 'false').lower() == 'true'
        if run_agents and state.GEM_DETECTOR_AVAILABLE and state.gem_detector and state.gem_detector.multi_agent_enabled:
            for cd in favorite_coins:
                matching = next((c for c in state.analyzer.coins if c.symbol.upper() == cd['symbol'].upper()), None)
                if matching:
                    _run_agent_analysis(matching, cd)

        ml_status = state.ML_AVAILABLE and state.ml_pipeline and state.ml_pipeline.model_loaded
        return jsonify({'favorites': favorite_coins, 'ml_enhanced': ml_status, 'missing_count': len(missing_coins)})
    except Exception as e:
        logger.error(f"Error in get_favorites: {e}")
        return jsonify({'error': str(e)}), 500


@coins_bp.route('/api/favorites/add', methods=['POST'])
def add_favorite():
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
            return jsonify({'success': False, 'error': 'Failed to save favorites'}), 500
        return jsonify({'success': False, 'error': f'{symbol} is already in favorites'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@coins_bp.route('/api/favorites/remove', methods=['POST'])
def remove_favorite():
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
            return jsonify({'success': False, 'error': 'Failed to save favorites'}), 500
        return jsonify({'success': False, 'error': f'{symbol} is not in favorites'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

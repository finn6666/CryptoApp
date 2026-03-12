"""
ML pipeline, gem detection, agent analysis, and portfolio routes.
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request

from services.app_state import run_async, parse_market_cap, parse_volume, project_root
import services.app_state as state
from routes.trading import require_trading_auth
from extensions import limiter

logger = logging.getLogger(__name__)

ml_bp = Blueprint('ml', __name__)


# ─── ML Status & Management ──────────────────────────────────

@ml_bp.route('/api/ml/status')
def get_ml_status():
    try:
        if not state.ML_AVAILABLE or state.ml_pipeline is None:
            error_details = {
                'error': 'ML components not available',
                'ML_AVAILABLE': state.ML_AVAILABLE,
                'ml_pipeline_exists': state.ml_pipeline is not None,
                'suggestion': 'Click "Train ML Model" to initialize and train the model',
                'gem_detector_available': state.GEM_DETECTOR_AVAILABLE,
                'rl_detector_available': False,
            }
            try:
                import sklearn, pandas, numpy
                error_details['dependencies_ok'] = True
            except ImportError as ie:
                error_details['dependencies_ok'] = False
                error_details['missing_dependency'] = str(ie)
            return jsonify({'ml_status': error_details, 'service_available': False})

        status = state.ml_pipeline.get_status()
        return jsonify({'ml_status': status, 'service_available': True})
    except Exception as e:
        logger.error(f"Error getting ML status: {e}")
        return jsonify({'error': 'ML status unavailable', 'service_available': False}), 500


@ml_bp.route('/api/ml/predict/<symbol>')
def get_ml_prediction(symbol):
    try:
        if not state.ML_AVAILABLE or state.ml_pipeline is None or not state.ml_pipeline.model_loaded:
            return jsonify({'error': 'ML model not available'}), 503
        coin = next((c for c in state.analyzer.coins if c.symbol.upper() == symbol.upper()), None)
        if not coin:
            return jsonify({'error': f'Coin {symbol} not found in current data'}), 404
        features = {
            'price_change_1h': coin.price_change_24h or 0,
            'price_change_24h': coin.price_change_24h or 0,
            'volume_change_24h': 0, 'market_cap_change_24h': 0,
            'rsi': 50, 'macd': 0,
            'moving_avg_7d': coin.price or 0, 'moving_avg_30d': coin.price or 0,
        }
        result = state.ml_pipeline.predict_with_validation(features)
        result['coin'] = {'symbol': coin.symbol, 'name': coin.name, 'current_price': coin.price, 'attractiveness_score': coin.attractiveness_score}
        return jsonify(result)
    except Exception as e:
        logger.error(f"ML prediction error for {symbol}: {e}")
        return jsonify({'error': 'Prediction failed'}), 500


@ml_bp.route('/api/ml/train', methods=['POST'])
@limiter.limit('2 per hour')
@require_trading_auth
def train_ml_model():
    try:
        logger.info("🎯 ML Training requested")
        if not state.ML_AVAILABLE or state.ml_pipeline is None:
            if not state.initialize_ml():
                return jsonify({'success': False, 'error': 'ML components not available.'}), 503
        if not os.path.exists('models'):
            os.makedirs('models')
        sample_path = 'models/sample_training_data.csv'
        sample_df = state.ml_pipeline.create_sample_data(symbol="BTC", days=30)
        sample_df.to_csv(sample_path, index=False)
        training_result = state.ml_pipeline.train_model(sample_path)
        state.ml_pipeline.export_model(os.path.join(project_root, 'models'))
        return jsonify({'success': True, 'message': 'Model trained successfully!', 'training_result': training_result, 'status': state.ml_pipeline.get_status(), 'rows_trained': len(sample_df)})
    except Exception as e:
        logger.error(f"ML training failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Training failed'}), 500


@ml_bp.route('/api/ml/initialize', methods=['POST'])
@require_trading_auth
def initialize_ml_endpoint():
    success = state.initialize_ml()
    return jsonify({'success': success, 'message': 'ML components initialized successfully' if success else 'Failed to initialize ML components', 'ml_available': state.ML_AVAILABLE})


@ml_bp.route('/api/gemini/quota')
def check_gemini_quota():
    try:
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return jsonify({'error': 'GOOGLE_API_KEY not found'}), 500
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel('gemini-3-flash-preview')
            response = model.generate_content("Say 'OK'")
            return jsonify({'status': 'SUCCESS', 'message': '✅ Gemini API is working!', 'test_response': response.text})
        except Exception as e:
            if '429' in str(e) or 'quota' in str(e).lower():
                return jsonify({'status': 'QUOTA_ERROR', 'message': 'Still hitting quota limits'})
            raise
    except Exception as e:
        logger.error(f"Gemini quota check failed: {e}")
        return jsonify({'error': 'Failed to test Gemini API', 'message': 'Failed to test Gemini API'}), 500


@ml_bp.route('/api/debug/ml')
@require_trading_auth
def debug_ml_system():
    try:
        models_dir = os.path.join(project_root, 'models')
        return jsonify({
            'ml_pipeline': {
                'ML_AVAILABLE': state.ML_AVAILABLE,
                'ml_pipeline_exists': state.ml_pipeline is not None,
                'model_loaded': state.ml_pipeline.model_loaded if state.ml_pipeline else False,
                'training_status': state.ml_pipeline.training_status if state.ml_pipeline else 'N/A',
                'last_training_time': str(state.ml_pipeline.last_training_time) if state.ml_pipeline and state.ml_pipeline.last_training_time else None,
            },
            'gem_detector': {
                'GEM_DETECTOR_AVAILABLE': state.GEM_DETECTOR_AVAILABLE,
                'gem_detector_exists': state.gem_detector is not None,
                'rl_integrated': True,
            },
            'model_files': {
                'models_dir_exists': os.path.exists(models_dir),
                'crypto_model_pkl': os.path.exists(os.path.join(models_dir, 'crypto_model.pkl')),
                'scaler_pkl': os.path.exists(os.path.join(models_dir, 'scaler.pkl')),
            },
            'analyzer': {
                'total_coins': len(state.analyzer.coins),
                'coins_with_price': len([c for c in state.analyzer.coins if c.price and c.price > 0]),
            },
        })
    except Exception as e:
        logger.error(f"Debug ML error: {e}")
        return jsonify({'error': 'Debug info unavailable'}), 500


# ─── Gem Detection ────────────────────────────────────────────

@ml_bp.route('/api/gems/detect/<symbol>')
def detect_hidden_gem(symbol):
    if not state.GEM_DETECTOR_AVAILABLE or not state.gem_detector:
        return jsonify({'error': 'Hidden Gem Detector not available'}), 503
    try:
        coin = next((c for c in state.analyzer.coins if c.symbol.upper() == symbol.upper()), None)
        if not coin:
            return jsonify({'error': f'Coin {symbol} not found'}), 404
        coin_data = {
            'symbol': coin.symbol, 'name': coin.name, 'price': coin.price,
            'price_change_24h': {'usd': getattr(coin, 'price_change_24h', 0)},
            'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
            'market_cap': getattr(coin, 'market_cap', 'N/A'),
            'total_volume': getattr(coin, 'total_volume', 'N/A'),
            'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
            'status': getattr(coin, 'status', 'current'),
        }
        prediction = state.gem_detector.predict_hidden_gem(coin_data)
        if prediction is None:
            return jsonify({'error': 'Prediction failed'}), 500
        prediction['coin'] = {'symbol': coin.symbol, 'name': coin.name, 'price': coin.price, 'market_cap_rank': coin_data['market_cap_rank'], 'attractiveness_score': coin_data['attractiveness_score']}
        return jsonify(prediction)
    except Exception as e:
        logger.error(f"Gem detection error for {symbol}: {e}")
        return jsonify({'error': 'Gem detection failed'}), 500


@ml_bp.route('/api/gems/scan')
def scan_for_hidden_gems():
    if not state.GEM_DETECTOR_AVAILABLE or not state.gem_detector:
        return jsonify({'error': 'Hidden Gem Detector not available'}), 503
    try:
        from ml.exchange_manager import get_exchange_manager
        exchange_mgr = get_exchange_manager()
        limit = int(request.args.get('limit', 20))
        min_prob = float(request.args.get('min_probability', 0.6))
        gems, processed = [], 0
        for coin in state.analyzer.coins[:100]:
            # Only scan coins tradeable on Kraken
            if not exchange_mgr.is_tradeable(coin.symbol):
                continue
            try:
                processed += 1
                cd = {
                    'symbol': coin.symbol, 'name': coin.name, 'price': coin.price,
                    'price_change_24h': {'usd': getattr(coin, 'price_change_24h', 0)},
                    'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
                    'market_cap': getattr(coin, 'market_cap', 'N/A'),
                    'total_volume': getattr(coin, 'total_volume', 'N/A'),
                    'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
                    'status': getattr(coin, 'status', 'current'),
                }
                pred = state.gem_detector.predict_hidden_gem(cd)
                if pred and pred['gem_probability'] >= min_prob:
                    gems.append({
                        'symbol': coin.symbol, 'name': coin.name, 'price': coin.price,
                        'market_cap_rank': cd['market_cap_rank'], 'attractiveness_score': cd['attractiveness_score'],
                        'gem_probability': pred['gem_probability'], 'gem_score': pred['gem_score'],
                        'confidence': pred['confidence'], 'risk_level': pred['risk_level'],
                        'recommendation': pred['recommendation'],
                        'key_strengths': pred['key_strengths'][:3], 'top_features': pred['top_features'][:3],
                    })
            except Exception as e:
                logger.warning(f"Error scanning {coin.symbol}: {e}")
        gems.sort(key=lambda x: x['gem_probability'], reverse=True)
        return jsonify({
            'hidden_gems': gems[:limit], 'total_scanned': processed, 'gems_found': len(gems),
            'min_probability_threshold': min_prob,
            'scan_summary': {
                'ultra_high_potential': len([g for g in gems if g['gem_probability'] > 0.8]),
                'high_potential': len([g for g in gems if 0.7 <= g['gem_probability'] <= 0.8]),
                'moderate_potential': len([g for g in gems if 0.6 <= g['gem_probability'] < 0.7]),
            },
        })
    except Exception as e:
        logger.error(f"Gem scan error: {e}")
        return jsonify({'error': 'Gem scan failed'}), 500


@ml_bp.route('/api/gems/train', methods=['POST'])
@limiter.limit('2 per hour')
@require_trading_auth
def train_gem_detector():
    if not state.GEM_DETECTOR_AVAILABLE or not state.gem_detector:
        return jsonify({'error': 'Hidden Gem Detector not available'}), 503
    try:
        coins_data = []
        for coin in state.analyzer.coins:
            coins_data.append({
                'symbol': coin.symbol, 'name': coin.name, 'price': coin.price,
                'price_change_24h': {'usd': getattr(coin, 'price_change_24h', 0)},
                'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
                'market_cap': getattr(coin, 'market_cap', 'N/A'),
                'total_volume': getattr(coin, 'total_volume', 'N/A'),
                'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
                'status': getattr(coin, 'status', 'current'),
            })
        training_df, labels = state.gem_detector.create_training_dataset(coins_data)
        result = state.gem_detector.train_model(training_df, labels)
        if result:
            state.gem_detector.save_model()
            return jsonify({
                'success': True,
                'training_result': {
                    'accuracy': result['accuracy'], 'auc_score': result['auc_score'],
                    'cv_mean': result['cv_mean'], 'cv_std': result['cv_std'],
                    'total_coins_trained': len(coins_data),
                    'hidden_gems_identified': result['hidden_gems_found'],
                    'model_type': result['model_type'],
                    'top_features': sorted(result['feature_importance'].items(), key=lambda x: x[1], reverse=True)[:10],
                },
            })
        return jsonify({'success': False, 'error': 'Training failed'}), 500
    except Exception as e:
        logger.error(f"Gem training error: {e}")
        return jsonify({'success': False, 'error': 'Training failed'}), 500


@ml_bp.route('/api/gems/status')
def get_gem_detector_status():
    status = {
        'available': state.GEM_DETECTOR_AVAILABLE,
        'model_loaded': state.gem_detector.model_loaded if state.gem_detector else False,
        'service_status': 'available' if state.GEM_DETECTOR_AVAILABLE else 'unavailable',
    }
    if state.gem_detector and state.GEM_DETECTOR_AVAILABLE:
        status.update(state.gem_detector.get_model_info())
        status['multi_agent_enabled'] = state.gem_detector.multi_agent_enabled
        if state.gem_detector.multi_agent_enabled:
            status['agent_count'] = len(state.gem_detector.orchestrator.agents)
    return jsonify(status)


@ml_bp.route('/api/gems/top/<int:count>')
def get_top_hidden_gems(count):
    if not state.GEM_DETECTOR_AVAILABLE or not state.gem_detector:
        return jsonify({'error': 'Hidden Gem Detector not available'}), 503
    try:
        from ml.exchange_manager import get_exchange_manager
        exchange_mgr = get_exchange_manager()
        count = min(count, 50)
        analyzed = []
        for coin in state.analyzer.coins[:count * 3]:
            # Only include coins tradeable on Kraken
            if not exchange_mgr.is_tradeable(coin.symbol):
                continue
            try:
                cd = {
                    'symbol': coin.symbol, 'name': coin.name, 'price': coin.price,
                    'price_change_24h': {'usd': getattr(coin, 'price_change_24h', 0)},
                    'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
                    'market_cap': getattr(coin, 'market_cap', 'N/A'),
                    'total_volume': getattr(coin, 'total_volume', 'N/A'),
                    'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
                    'status': getattr(coin, 'status', 'current'),
                }
                pred = state.gem_detector.predict_hidden_gem(cd)
                if pred and pred['gem_probability'] > 0.5:
                    analyzed.append({
                        'symbol': coin.symbol, 'name': coin.name, 'price': coin.price,
                        'market_cap_rank': cd['market_cap_rank'],
                        'gem_probability': pred['gem_probability'], 'gem_score': pred['gem_score'],
                        'confidence': pred['confidence'], 'risk_level': pred['risk_level'],
                        'risk_score': pred['risk_score'], 'recommendation': pred['recommendation'],
                        'key_strengths': pred['key_strengths'], 'key_weaknesses': pred['key_weaknesses'],
                        'top_features': pred['top_features'], 'feature_breakdown': pred['feature_breakdown'],
                    })
            except Exception as e:
                logger.warning(f"Error analyzing {coin.symbol}: {e}")
        analyzed.sort(key=lambda x: x['gem_score'], reverse=True)
        top = analyzed[:count]
        return jsonify({
            'top_hidden_gems': top, 'requested_count': count, 'found_count': len(top),
            'analysis_summary': {
                'average_gem_score': sum(g['gem_score'] for g in top) / len(top) if top else 0,
                'risk_distribution': {lvl: len([g for g in top if g['risk_level'] == lvl]) for lvl in ['Low', 'Medium', 'High', 'Very High']},
            },
        })
    except Exception as e:
        logger.error(f"Top gems error: {e}")
        return jsonify({'error': 'Failed to get top gems'}), 500


# ─── Agent Analysis ───────────────────────────────────────────

@ml_bp.route('/api/agents/analyze/<symbol>')
def analyze_with_agents(symbol):
    if not state.GEM_DETECTOR_AVAILABLE or not state.gem_detector:
        return jsonify({'error': 'Gem Detector not available'}), 503
    if not state.gem_detector.multi_agent_enabled:
        return jsonify({'error': 'Multi-agent system not available'}), 503
    try:
        # Verify coin is tradeable on Kraken
        from ml.exchange_manager import get_exchange_manager
        exchange_mgr = get_exchange_manager()
        if not exchange_mgr.is_tradeable(symbol):
            return jsonify({'error': f'{symbol} is not available on Kraken'}), 400

        coin = next((c for c in state.analyzer.coins if c.symbol.upper() == symbol.upper()), None)
        if not coin:
            return jsonify({'error': f'Coin {symbol} not found'}), 404
        coin_data = {
            'symbol': coin.symbol, 'name': coin.name, 'price': coin.price,
            'price_change_24h': getattr(coin, 'price_change_24h', 0), 'price_change_7d': 0,
            'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
            'market_cap': parse_market_cap(getattr(coin, 'market_cap', 0)),
            'volume_24h': parse_volume(getattr(coin, 'total_volume', 0)),
            'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
            'status': getattr(coin, 'status', 'current'),
        }
        analysis = run_async(state.gem_detector.analyze_with_agents(coin_data))
        if analysis is None:
            return jsonify({'error': 'Analysis failed'}), 500
        analysis['coin'] = {'symbol': coin.symbol, 'name': coin.name, 'price': coin.price, 'market_cap_rank': coin_data['market_cap_rank'], 'attractiveness_score': coin_data['attractiveness_score']}
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Agent analysis error for {symbol}: {e}", exc_info=True)
        return jsonify({'error': 'Agent analysis failed'}), 500


@ml_bp.route('/api/agents/scan')
def scan_with_agents():
    if not state.GEM_DETECTOR_AVAILABLE or not state.gem_detector:
        return jsonify({'error': 'Gem Detector not available'}), 503
    if not state.gem_detector.multi_agent_enabled:
        return jsonify({'error': 'Multi-agent system not available'}), 503
    try:
        limit = int(request.args.get('limit', 10))
        min_score = float(request.args.get('min_score', 0.6))
        agent_gems, processed = [], 0
        for coin in state.analyzer.coins[:min(50, len(state.analyzer.coins))]:
            try:
                processed += 1
                cd = {
                    'symbol': coin.symbol, 'name': coin.name, 'price': coin.price,
                    'price_change_24h': getattr(coin, 'price_change_24h', 0), 'price_change_7d': 0,
                    'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
                    'market_cap': parse_market_cap(getattr(coin, 'market_cap', 0)),
                    'volume_24h': parse_volume(getattr(coin, 'total_volume', 0)),
                    'attractiveness_score': getattr(coin, 'attractiveness_score', 5.0),
                }
                analysis = run_async(state.gem_detector.analyze_with_agents(cd))
                if analysis and analysis.get('gem_score', 0) / 100 >= min_score:
                    agent_gems.append({
                        'symbol': coin.symbol, 'name': coin.name, 'price': coin.price,
                        'market_cap_rank': cd['market_cap_rank'], 'gem_score': analysis['gem_score'],
                        'gem_probability': analysis['gem_probability'], 'confidence': analysis['confidence'],
                        'risk_level': analysis['risk_level'], 'recommendation': analysis['recommendation'],
                        'key_strengths': analysis['key_strengths'][:3], 'multi_agent': True,
                    })
            except Exception as e:
                logger.error(f"Error scanning {coin.symbol} with agents: {e}")
        agent_gems.sort(key=lambda x: x['gem_score'], reverse=True)
        return jsonify({
            'agent_gems': agent_gems[:limit], 'total_scanned': processed, 'gems_found': len(agent_gems),
            'min_score_threshold': min_score,
            'scan_summary': {
                'ultra_high_potential': len([g for g in agent_gems if g['gem_score'] > 80]),
                'high_potential': len([g for g in agent_gems if 70 <= g['gem_score'] <= 80]),
                'moderate_potential': len([g for g in agent_gems if 60 <= g['gem_score'] < 70]),
            },
        })
    except Exception as e:
        logger.error(f"Agent scan error: {e}", exc_info=True)
        return jsonify({'error': 'Agent scan failed'}), 500


@ml_bp.route('/api/agents/metrics')
def get_agent_metrics():
    if not state.GEM_DETECTOR_AVAILABLE or not state.gem_detector or not state.gem_detector.multi_agent_enabled:
        return jsonify({'error': 'Multi-agent system not available'}), 503
    try:
        return jsonify(state.gem_detector.orchestrator.get_metrics())
    except Exception as e:
        logger.error(f"Agent metrics error: {e}")
        return jsonify({'error': 'Metrics unavailable'}), 500


# ─── Portfolio ────────────────────────────────────────────────

@ml_bp.route('/api/portfolio/analyze')
def analyze_portfolio():
    if not state.GEM_DETECTOR_AVAILABLE or not state.gem_detector:
        return jsonify({'error': 'Gem Detector not available'}), 503
    if not state.gem_detector.multi_agent_enabled or not state.gem_detector.orchestrator:
        return jsonify({'error': 'Multi-agent system not available'}), 503
    try:
        from ml.portfolio_manager import PortfolioManager
        max_coins = int(request.args.get('max_coins', 20))
        min_score = float(request.args.get('min_score', 6.0))
        candidates = sorted(state.analyzer.coins, key=lambda x: x.attractiveness_score, reverse=True)[:max_coins]
        candidates = [c for c in candidates if c.attractiveness_score >= min_score and c.price and c.price > 0]

        coins_data = []
        for coin in candidates:
            coins_data.append({
                'symbol': coin.symbol, 'name': coin.name, 'price': coin.price,
                'price_change_24h': getattr(coin, 'price_change_24h', 0), 'price_change_7d': 0,
                'market_cap_rank': getattr(coin, 'market_cap_rank', 999),
                'market_cap': parse_market_cap(getattr(coin, 'market_cap', 0)),
                'volume_24h': parse_volume(getattr(coin, 'total_volume', 0)),
                'attractiveness_score': coin.attractiveness_score,
                'status': getattr(coin, 'status', 'current'),
            })

        mgr = PortfolioManager(state.gem_detector.orchestrator)
        rec = run_async(mgr.analyze_portfolio(coins_data, max_coins))

        return jsonify({
            'summary': {
                'total_analyzed': len(coins_data), 'gems_found': rec.total_gems_found,
                'market_sentiment': rec.market_sentiment,
                'portfolio_risk': round(rec.portfolio_risk_score, 1),
                'diversification': round(rec.diversification_score, 1),
            },
            'recommendations': {'buy': rec.buy_recommendations, 'hold': rec.hold_recommendations, 'avoid': rec.avoid_recommendations},
            'top_opportunities': rec.top_opportunities,
            'risk_warnings': rec.risk_warnings,
            'allocation_strategy': rec.allocation_strategy,
        })
    except Exception as e:
        logger.error(f"Portfolio analysis error: {e}", exc_info=True)
        return jsonify({'error': 'Portfolio analysis failed'}), 500


# ─── Gem Score History ────────────────────────────────────────

@ml_bp.route('/api/gems/history')
def gem_score_history():
    """Get historical gem score predictions. Optional ?symbol=X filter."""
    try:
        from ml.gem_score_tracker import get_gem_score_tracker
        tracker = get_gem_score_tracker()
        symbol = request.args.get('symbol')
        limit = min(int(request.args.get('limit', 200)), 1000)
        history = tracker.get_history(symbol=symbol, limit=limit)
        return jsonify({"entries": len(history), "history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ml_bp.route('/api/gems/history/<symbol>/trend')
def gem_score_trend(symbol):
    """Get trend analysis for a specific coin's gem scores over time."""
    try:
        from ml.gem_score_tracker import get_gem_score_tracker
        tracker = get_gem_score_tracker()
        trend = tracker.get_symbol_trend(symbol.upper())
        return jsonify(trend)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ml_bp.route('/api/gems/accuracy')
def gem_accuracy_report():
    """Get overall gem detector accuracy metrics."""
    try:
        from ml.gem_score_tracker import get_gem_score_tracker
        tracker = get_gem_score_tracker()
        report = tracker.get_accuracy_report()
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

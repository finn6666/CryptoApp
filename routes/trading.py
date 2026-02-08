"""
Live trading engine and RL learning routes.
"""

import json as _json
import re
import logging
import asyncio
from flask import Blueprint, jsonify, request, render_template

import services.app_state as state

logger = logging.getLogger(__name__)

trading_bp = Blueprint('trading', __name__)


# ========================================
# Live Trading Engine Routes
# ========================================

@trading_bp.route('/api/trades/status')
def trading_status():
    """Get trading engine status — budget, active trades, kill switch state"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return jsonify(engine.get_status()), 200
    except Exception as e:
        logger.error(f"Trading status error: {e}")
        return jsonify({"error": str(e)}), 500


@trading_bp.route('/api/trades/pending')
def pending_proposals():
    """Get all pending trade proposals awaiting approval"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return jsonify({"proposals": engine.get_pending_proposals()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@trading_bp.route('/api/trades/history')
def trade_history():
    """Get executed trade history"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return jsonify({"trades": engine.get_trade_history()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@trading_bp.route('/api/trades/approve/<proposal_id>')
def approve_trade(proposal_id):
    """Approve a trade proposal (called from email link)"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        result = engine.approve_trade(proposal_id)

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


@trading_bp.route('/api/trades/reject/<proposal_id>')
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


@trading_bp.route('/api/trades/propose', methods=['POST'])
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


@trading_bp.route('/api/trades/kill-switch', methods=['POST'])
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


@trading_bp.route('/api/trades/auto-evaluate', methods=['POST'])
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
        from ml.agents.official.trading_agent import evaluate_trade

        loop = asyncio.new_event_loop()
        decision = loop.run_until_complete(
            evaluate_trade(symbol, analysis, current_price, remaining)
        )
        loop.close()

        if not decision.get("success"):
            return jsonify(decision), 500

        # Parse the trading agent's decision
        decision_text = decision.get("decision_raw", "")
        parsed = None

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

@trading_bp.route('/trades')
def trades_page():
    """Trade journal page for reporting trades and RL learning"""
    return render_template('trades.html')


@trading_bp.route('/api/rl/report-trade', methods=['POST'])
def report_trade():
    """Report a trade outcome to teach the RL system"""
    try:
        data = request.json

        required_fields = ['symbol', 'entry_price', 'exit_price', 'days_held']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        symbol = data['symbol'].upper()
        entry_price = float(data['entry_price'])
        exit_price = float(data['exit_price'])
        days_held = int(data['days_held'])
        notes = data.get('notes', '')

        profit_pct = ((exit_price - entry_price) / entry_price) * 100

        if not state.GEM_DETECTOR_AVAILABLE or not state.gem_detector:
            return jsonify({'error': 'RL not available. Gem detector not initialized.'}), 503

        features = {
            'profit_indicator': 1.0 if profit_pct > 0 else -1.0,
            'days_held': days_held / 100.0,
            'entry_price': entry_price / 10000.0,
        }

        result = state.gem_detector.learn_from_outcome(
            symbol=symbol,
            entry_price=entry_price,
            current_price=exit_price,
            days_held=days_held,
            features=features,
            notes=notes
        )

        if not result:
            return jsonify({'error': 'RL learning not available'}), 503

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


@trading_bp.route('/api/rl/stats')
def rl_stats():
    """Get RL learning statistics"""
    try:
        if not state.GEM_DETECTOR_AVAILABLE or not state.gem_detector:
            return jsonify({'success': False, 'error': 'RL not available'}), 503

        from ml.simple_rl import simple_rl_learner
        stats = simple_rl_learner.get_stats()
        stats['success'] = True
        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error getting RL stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@trading_bp.route('/api/rl/trades')
def rl_trades():
    """Get recent trades from RL history"""
    try:
        from ml.simple_rl import simple_rl_learner

        recent_trades = simple_rl_learner.trade_history[-20:]
        enhanced_trades = []
        for trade in reversed(recent_trades):
            enhanced_trade = trade.copy()
            enhanced_trade['symbol'] = enhanced_trade.get('symbol', 'N/A')
            enhanced_trades.append(enhanced_trade)

        return jsonify({'success': True, 'trades': enhanced_trades}), 200

    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({'success': False, 'error': str(e), 'trades': []}), 500

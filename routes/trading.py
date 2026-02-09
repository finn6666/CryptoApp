"""
Live trading engine and RL learning routes.
"""

import os
import json as _json
import re
import logging
import asyncio
from functools import wraps
from flask import Blueprint, jsonify, request, render_template
from itsdangerous import SignatureExpired, BadSignature

from extensions import limiter
import services.app_state as state

logger = logging.getLogger(__name__)

trading_bp = Blueprint('trading', __name__)


# ========================================
# Auth decorator for trading POST endpoints
# ========================================

def require_trading_auth(f):
    """Require a valid TRADING_API_KEY in the Authorization header.
    Format: Authorization: Bearer <key>
    The /api/trades/confirm/<token> route is exempt — it's protected by HMAC signature.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = os.environ.get('TRADING_API_KEY')
        if not api_key:
            logger.error('TRADING_API_KEY not set — blocking request for safety')
            return jsonify({'error': 'Trading auth not configured'}), 503

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or malformed Authorization header'}), 401

        provided = auth_header[7:]  # strip "Bearer "
        if not provided or provided != api_key:
            logger.warning(f'Rejected trading request — bad API key from {request.remote_addr}')
            return jsonify({'error': 'Invalid API key'}), 403

        return f(*args, **kwargs)
    return decorated


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
        return jsonify({"error": "Failed to get trading status"}), 500


@trading_bp.route('/api/trades/pending')
def pending_proposals():
    """Get all pending trade proposals awaiting approval"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return jsonify({"proposals": engine.get_pending_proposals()}), 200
    except Exception as e:
        logger.error(f"Pending proposals error: {e}")
        return jsonify({"error": "Failed to get pending proposals"}), 500


@trading_bp.route('/api/trades/history')
def trade_history():
    """Get executed trade history"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return jsonify({"trades": engine.get_trade_history()}), 200
    except Exception as e:
        logger.error(f"Trade history error: {e}")
        return jsonify({"error": "Failed to get trade history"}), 500


@trading_bp.route('/api/trades/confirm/<token>', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def confirm_trade(token):
    """
    GET  — Verify signed token and show confirmation page with Approve / Reject buttons.
    POST — Execute the approve or reject action after user clicks the button.
    Token is HMAC-signed with itsdangerous (1-hour expiry) so email scanners
    clicking the link can only see the confirmation page, never execute a trade.
    Rate limited: 10 confirm attempts per minute to prevent brute-force.
    """
    from ml.trading_engine import get_trading_engine

    engine = get_trading_engine()

    # ── Verify token ──────────────────────────────────────────
    try:
        payload = engine.verify_proposal_token(token)
        proposal_id = payload['id']
        action = payload['action']          # 'approve' or 'reject'
    except SignatureExpired:
        return _error_page("Link Expired",
                           "This approval link has expired (1 hour). "
                           "Request a new proposal if needed."), 410
    except BadSignature:
        return _error_page("Invalid Link",
                           "This link is invalid or has been tampered with."), 403

    # ── Look up the proposal ──────────────────────────────────
    pending = {p['id']: p for p in engine.get_pending_proposals()}
    proposal = pending.get(proposal_id)

    if proposal is None:
        return _error_page("Proposal Not Found",
                           f"Proposal {proposal_id} has already been actioned "
                           "or does not exist."), 404

    # ── GET: show confirmation page ───────────────────────────
    if request.method == 'GET':
        action_colour = '#38a169' if action == 'approve' else '#e53e3e'
        action_label = '✅ CONFIRM APPROVE' if action == 'approve' else '❌ CONFIRM REJECT'
        action_desc = ('Approve and execute this trade' if action == 'approve'
                       else 'Reject this trade — no money will be spent')

        return f"""
        <html>
        <body style="font-family: -apple-system, sans-serif; background: #0d0d14; color: #e2e8f0;
                     display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;">
            <div style="background: #151520; padding: 40px; border-radius: 16px; border: 1px solid #2d3748;
                        max-width: 420px; width: 100%;">
                <h2 style="margin: 0 0 20px; color: #e2e8f0; font-size: 18px;">
                    {'🟢' if proposal['side'] == 'buy' else '🔴'}
                    {proposal['side'].upper()} {proposal['symbol']}
                </h2>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr><td style="padding:6px 0; color:#a0aec0;">Amount</td>
                        <td style="text-align:right; font-weight:700;">£{proposal['amount_gbp']:.4f}</td></tr>
                    <tr><td style="padding:6px 0; color:#a0aec0;">Price</td>
                        <td style="text-align:right;">£{proposal['price_at_proposal']:.6f}</td></tr>
                    <tr><td style="padding:6px 0; color:#a0aec0;">Confidence</td>
                        <td style="text-align:right;">{proposal['confidence']}%</td></tr>
                </table>
                <p style="color: #a0aec0; font-size: 13px; margin-bottom: 20px;">{action_desc}</p>
                <form method="POST">
                    <button type="submit"
                            style="width: 100%; padding: 14px; background: {action_colour}; color: white;
                                   border: none; border-radius: 8px; font-size: 15px; font-weight: 700;
                                   cursor: pointer;">
                        {action_label}
                    </button>
                </form>
                <a href="/trades" style="display: block; text-align: center; margin-top: 12px;
                                         color: #667eea; text-decoration: none; font-size: 13px;">
                    ← Back to trades
                </a>
            </div>
        </body>
        </html>
        """

    # ── POST: execute the action ──────────────────────────────
    try:
        if action == 'approve':
            result = engine.approve_trade(proposal_id)
            if result.get("success"):
                return f"""
                <html>
                <body style="font-family: -apple-system, sans-serif; background: #0d0d14; color: #e2e8f0;
                             display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;">
                    <div style="text-align: center; background: #151520; padding: 40px; border-radius: 16px;
                                border: 1px solid #2d3748; max-width: 400px;">
                        <div style="font-size: 48px; margin-bottom: 16px;">✅</div>
                        <h2 style="margin: 0 0 8px; color: #48bb78;">Trade Approved &amp; Executed</h2>
                        <p style="color: #a0aec0; margin: 0 0 16px;">
                            {result.get('side', '').upper()} {result.get('quantity', 0):.6f} {result.get('symbol', '')}
                            @ £{result.get('price', 0):.6f}
                        </p>
                        <p style="color: #a0aec0; font-size: 13px;">Amount: £{result.get('amount_gbp', 0):.4f}</p>
                        <a href="/trades" style="display: inline-block; margin-top: 16px; padding: 10px 24px;
                                                 background: #667eea; color: white; text-decoration: none;
                                                 border-radius: 8px;">View Trades</a>
                    </div>
                </body>
                </html>
                """
            else:
                return _error_page("Could Not Execute",
                                   result.get('error', 'Unknown error'))
        else:
            engine.reject_trade(proposal_id)
            return f"""
            <html>
            <body style="font-family: -apple-system, sans-serif; background: #0d0d14; color: #e2e8f0;
                         display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;">
                <div style="text-align: center; background: #151520; padding: 40px; border-radius: 16px;
                            border: 1px solid #2d3748; max-width: 400px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">❌</div>
                    <h2 style="margin: 0 0 8px; color: #fc8181;">Trade Rejected</h2>
                    <p style="color: #a0aec0;">No money was spent.</p>
                    <a href="/trades" style="display: inline-block; margin-top: 16px; padding: 10px 24px;
                                             background: #667eea; color: white; text-decoration: none;
                                             border-radius: 8px;">View Trades</a>
                </div>
            </body>
            </html>
            """
    except Exception as e:
        logger.error(f"Trade confirmation error: {e}")
        return _error_page("Error", "Something went wrong processing this trade."), 500


def _error_page(title: str, message: str) -> str:
    """Render a simple branded error page — never leaks internal details."""
    return f"""
    <html>
    <body style="font-family: -apple-system, sans-serif; background: #0d0d14; color: #e2e8f0;
                 display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;">
        <div style="text-align: center; background: #151520; padding: 40px; border-radius: 16px;
                    border: 1px solid #2d3748; max-width: 400px;">
            <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
            <h2 style="margin: 0 0 8px; color: #ecc94b;">{title}</h2>
            <p style="color: #a0aec0;">{message}</p>
            <a href="/trades" style="display: inline-block; margin-top: 16px; padding: 10px 24px;
                                     background: #667eea; color: white; text-decoration: none;
                                     border-radius: 8px;">View Trades</a>
        </div>
    </body>
    </html>
    """


@trading_bp.route('/api/trades/propose', methods=['POST'])
@limiter.limit('10 per hour')
@require_trading_auth
def propose_trade_api():
    """Manually propose a trade (from dashboard or agent)"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()

        data = request.json
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        required = ['symbol', 'side', 'amount_gbp', 'current_price', 'reason', 'confidence']
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        # ── Validate side ──
        side = str(data['side']).lower().strip()
        if side not in ('buy', 'sell'):
            return jsonify({"error": "side must be 'buy' or 'sell'"}), 400

        # ── Validate amount ──
        try:
            amount_gbp = float(data['amount_gbp'])
        except (ValueError, TypeError):
            return jsonify({"error": "amount_gbp must be a number"}), 400
        if amount_gbp <= 0:
            return jsonify({"error": "amount_gbp must be positive"}), 400

        remaining = engine.get_remaining_budget()
        if amount_gbp > remaining:
            return jsonify({"error": f"amount_gbp exceeds remaining budget (£{remaining:.4f})"}), 400

        # ── Validate price ──
        try:
            current_price = float(data['current_price'])
        except (ValueError, TypeError):
            return jsonify({"error": "current_price must be a number"}), 400
        if current_price <= 0:
            return jsonify({"error": "current_price must be positive"}), 400

        # ── Validate confidence ──
        try:
            confidence = int(data['confidence'])
        except (ValueError, TypeError):
            return jsonify({"error": "confidence must be an integer"}), 400
        if not 0 <= confidence <= 100:
            return jsonify({"error": "confidence must be 0–100"}), 400

        # ── Validate symbol — basic sanity check ──
        symbol = str(data['symbol']).upper().strip()
        if not symbol or len(symbol) > 20:
            return jsonify({"error": "Invalid symbol"}), 400

        # ── Validate reason ──
        reason = str(data['reason']).strip()
        if not reason:
            return jsonify({"error": "reason is required"}), 400

        result = engine.propose_trade(
            symbol=symbol,
            side=side,
            amount_gbp=round(amount_gbp, 4),
            current_price=current_price,
            reason=reason[:500],            # cap at 500 chars
            confidence=confidence,
            recommendation=data.get('recommendation', 'BUY'),
        )
        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        logger.error(f"Propose trade error: {e}")
        return jsonify({"error": "Failed to create trade proposal"}), 500


@trading_bp.route('/api/trades/kill-switch', methods=['POST'])
@limiter.limit('5 per minute')
@require_trading_auth
def toggle_kill_switch():
    """Activate or deactivate the trading kill switch"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()

        data = request.json or {}
        action = str(data.get('action', 'activate')).lower().strip()
        if action not in ('activate', 'deactivate'):
            return jsonify({"error": "action must be 'activate' or 'deactivate'"}), 400

        if action == 'activate':
            result = engine.activate_kill_switch()
        else:
            result = engine.deactivate_kill_switch()
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Kill switch error: {e}")
        return jsonify({"error": "Failed to toggle kill switch"}), 500


@trading_bp.route('/api/trades/auto-evaluate', methods=['POST'])
@limiter.limit('10 per hour')
@require_trading_auth
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
        return jsonify({"error": "Failed to evaluate trade"}), 500


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
        return jsonify({'error': 'Invalid number format in trade data'}), 400
    except Exception as e:
        logger.error(f"Error reporting trade: {e}")
        return jsonify({'error': 'Failed to report trade'}), 500


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
        return jsonify({'success': False, 'error': 'Failed to get RL stats'}), 500


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
        return jsonify({'success': False, 'error': 'Failed to get trades', 'trades': []}), 500

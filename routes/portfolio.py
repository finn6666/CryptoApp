"""
Portfolio, exchange, and dashboard routes.
"""

import os
import json as _json
import logging
from flask import Blueprint, jsonify, request, Response, stream_with_context

from extensions import limiter
import services.app_state as state
from routes.trading import require_trading_auth

logger = logging.getLogger(__name__)

portfolio_bp = Blueprint('portfolio', __name__)

"""
Live trading engine and RL learning routes.
"""

import os
import hmac
import html as _html
import json as _json
import re
import secrets
import logging
from functools import wraps
from flask import Blueprint, jsonify, request, redirect, Response, stream_with_context, session
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
        if not provided or not hmac.compare_digest(provided, api_key):
            logger.warning(f'Rejected trading request — bad API key from {request.remote_addr}')
            return jsonify({'error': 'Invalid API key'}), 403

        return f(*args, **kwargs)
    return decorated


# ========================================
# Live Trading Engine Routes
# ========================================

@portfolio_bp.route('/api/trades/status')
@require_trading_auth
def trading_status():
    """Get trading engine status — budget, active trades, kill switch state"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return jsonify(engine.get_status()), 200
    except Exception as e:
        logger.error(f"Trading status error: {e}")
        return jsonify({"error": "Failed to get trading status"}), 500


@portfolio_bp.route('/api/trades/pending')
@require_trading_auth
def pending_proposals():
    """Get all pending trade proposals awaiting approval"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return jsonify({"proposals": engine.get_pending_proposals()}), 200
    except Exception as e:
        logger.error(f"Pending proposals error: {e}")
        return jsonify({"error": "Failed to get pending proposals"}), 500


@portfolio_bp.route('/api/trades/history')
@require_trading_auth
def trade_history():
    """Get executed trade history"""
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return jsonify({"trades": engine.get_trade_history()}), 200
    except Exception as e:
        logger.error(f"Trade history error: {e}")
        return jsonify({"error": "Failed to get trade history"}), 500


@portfolio_bp.route('/api/trades/confirm/<token>', methods=['GET', 'POST'])
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
        # Generate a one-time CSRF nonce and store in session
        csrf_nonce = secrets.token_hex(32)
        session['csrf_nonce'] = csrf_nonce

        action_colour = '#38a169' if action == 'approve' else '#e53e3e'
        action_label = 'CONFIRM APPROVE' if action == 'approve' else 'CONFIRM REJECT'
        action_desc = ('Approve and execute this trade' if action == 'approve'
                       else 'Reject this trade — no money will be spent')

        p_side   = _html.escape(str(proposal['side']).upper())
        p_symbol = _html.escape(str(proposal['symbol']))
        p_conf   = _html.escape(str(proposal['confidence']))
        side_dot = '&#x1F7E2;' if proposal['side'] == 'buy' else '&#x1F534;'

        return f"""
        <html>
        <body style="font-family: -apple-system, sans-serif; background: #0d0d14; color: #e2e8f0;
                     display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;">
            <div style="background: #151520; padding: 40px; border-radius: 16px; border: 1px solid #2d3748;
                        max-width: 420px; width: 100%;">
                <h2 style="margin: 0 0 20px; color: #e2e8f0; font-size: 18px;">
                    {side_dot} {p_side} {p_symbol}
                </h2>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr><td style="padding:6px 0; color:#a0aec0;">Amount</td>
                        <td style="text-align:right; font-weight:700;">&#xA3;{proposal['amount_gbp']:.4f}</td></tr>
                    <tr><td style="padding:6px 0; color:#a0aec0;">Price</td>
                        <td style="text-align:right;">&#xA3;{proposal['price_at_proposal']:.6f}</td></tr>
                    <tr><td style="padding:6px 0; color:#a0aec0;">Confidence</td>
                        <td style="text-align:right;">{p_conf}%</td></tr>
                </table>
                <p style="color: #a0aec0; font-size: 13px; margin-bottom: 20px;">{_html.escape(action_desc)}</p>
                <form method="POST">
                    <input type="hidden" name="csrf_nonce" value="{csrf_nonce}">
                    <button type="submit"
                            style="width: 100%; padding: 14px; background: {action_colour}; color: white;
                                   border: none; border-radius: 8px; font-size: 15px; font-weight: 700;
                                   cursor: pointer;">
                        {_html.escape(action_label)}
                    </button>
                </form>
                <a href="/trades" style="display: block; text-align: center; margin-top: 12px;
                                         color: #667eea; text-decoration: none; font-size: 13px;">
                    &larr; Back to trades
                </a>
            </div>
        </body>
        </html>
        """

    # ── POST: execute the action ──────────────────────────────
    # Verify CSRF nonce from session
    expected_nonce = session.pop('csrf_nonce', None)
    submitted_nonce = request.form.get('csrf_nonce', '')
    if not expected_nonce or not hmac.compare_digest(expected_nonce, submitted_nonce):
        return _error_page("Invalid Request",
                           "CSRF validation failed. Please go back and try again."), 403

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
                        <h2 style="margin: 0 0 8px; color: #48bb78;">Trade Approved &amp; Executed</h2>
                        <p style="color: #a0aec0; margin: 0 0 16px;">
                            {_html.escape(result.get('side', '').upper())} {result.get('quantity', 0):.6f} {_html.escape(result.get('symbol', ''))}
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
            return """
            <html>
            <body style="font-family: -apple-system, sans-serif; background: #0d0d14; color: #e2e8f0;
                         display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;">
                <div style="text-align: center; background: #151520; padding: 40px; border-radius: 16px;
                            border: 1px solid #2d3748; max-width: 400px;">
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
    safe_title = _html.escape(str(title))
    safe_message = _html.escape(str(message))
    return f"""
    <html>
    <body style="font-family: -apple-system, sans-serif; background: #0d0d14; color: #e2e8f0;
                 display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;">
        <div style="text-align: center; background: #151520; padding: 40px; border-radius: 16px;
                    border: 1px solid #2d3748; max-width: 400px;">
            <h2 style="margin: 0 0 8px; color: #ecc94b;">{safe_title}</h2>
            <p style="color: #a0aec0;">{safe_message}</p>
            <a href="/trades" style="display: inline-block; margin-top: 16px; padding: 10px 24px;
                                     background: #667eea; color: white; text-decoration: none;
                                     border-radius: 8px;">View Trades</a>
        </div>
    </body>
    </html>
    """


# ========================================
# In-App Approve / Reject (no email token needed)
# ========================================

@portfolio_bp.route('/api/trades/approve/<proposal_id>', methods=['POST'])
@limiter.limit('10 per minute')
@require_trading_auth
def approve_trade_api(proposal_id):
    """Approve a pending trade proposal from the web UI."""
    if not re.match(r'^[a-f0-9]{12}$', proposal_id):
        return jsonify({'success': False, 'error': 'Invalid proposal ID format'}), 400
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        result = engine.approve_trade(proposal_id)
        if result.get('success'):
            return jsonify(result), 200
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"Approve trade error: {e}")
        return jsonify({'success': False, 'error': 'Failed to approve trade'}), 500


@portfolio_bp.route('/api/trades/reject/<proposal_id>', methods=['POST'])
@limiter.limit('10 per minute')
@require_trading_auth
def reject_trade_api(proposal_id):
    """Reject a pending trade proposal from the web UI."""
    if not re.match(r'^[a-f0-9]{12}$', proposal_id):
        return jsonify({'success': False, 'error': 'Invalid proposal ID format'}), 400
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        result = engine.reject_trade(proposal_id)
        if result.get('success'):
            return jsonify(result), 200
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"Reject trade error: {e}")
        return jsonify({'success': False, 'error': 'Failed to reject trade'}), 500


@portfolio_bp.route('/api/trades/propose', methods=['POST'])
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
            amount_gbp=round(amount_gbp, 2),
            current_price=current_price,
            reason=reason[:500],            # cap at 500 chars
            confidence=confidence,
            recommendation=data.get('recommendation', 'BUY'),
        )
        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        logger.error(f"Propose trade error: {e}")
        return jsonify({"error": "Failed to create trade proposal"}), 500


@portfolio_bp.route('/api/trades/kill-switch', methods=['POST'])
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


@portfolio_bp.route('/api/trades/auto-evaluate', methods=['POST'])
@limiter.limit('10 per hour')
@require_trading_auth
def auto_evaluate_trade():
    """
    Run the full multi-agent orchestrator (including trading_specialist sub-agent)
    on a coin to decide if it's worth a real trade.
    Uses the ADK multi-agent system: 4 analysts + 1 trading specialist.
    """
    try:
        from ml.trading_engine import get_trading_engine
        import services.app_state as state
        engine = get_trading_engine()

        data = request.json
        symbol = data.get('symbol', '').upper()
        current_price = float(data.get('current_price', 0))

        if not symbol or not current_price:
            return jsonify({"error": "Missing symbol or current_price"}), 400

        # Verify coin is tradeable on Kraken before analysis
        from ml.exchange_manager import get_exchange_manager
        exchange_mgr = get_exchange_manager()
        if not exchange_mgr.is_tradeable(symbol):
            return jsonify({"error": f"{symbol} is not available on Kraken"}), 400

        remaining = engine.get_remaining_budget()
        if engine.is_budget_exhausted():
            return jsonify({"error": "Daily budget exhausted", "remaining": round(remaining, 2)}), 400

        # Run the full multi-agent orchestrator (includes trading_specialist)
        if not state.official_adk_available or not state.analyze_crypto_adk:
            return jsonify({"error": "ADK multi-agent system not available"}), 500

        # Build coin_data for the orchestrator
        coin_data = {
            "symbol": symbol,
            "price": current_price,
            "name": data.get("name", symbol),
            "price_change_24h": data.get("price_change_24h", 0),
            "price_change_7d": data.get("price_change_7d", 0),
            "market_cap_rank": data.get("market_cap_rank"),
            "market_cap": data.get("market_cap"),
            "volume_24h": data.get("volume_24h"),
            "attractiveness_score": data.get("attractiveness_score", 0),
        }

        result = state.run_async(
            state.analyze_crypto_adk(symbol, coin_data)
        )

        if not result or not result.get("success"):
            return jsonify(result or {"error": "Analysis failed"}), 500

        # Extract trade decision from the multi-agent orchestrator output
        trade_decision = result.get("trade_decision", {})
        should_trade = trade_decision.get("should_trade", False)
        conviction = trade_decision.get("trade_conviction", 0)
        allocation_pct = trade_decision.get("trade_allocation_pct", 0)
        trade_reasoning = trade_decision.get("trade_reasoning", "")
        trade_side = trade_decision.get("trade_side", "buy")
        trade_risk_note = trade_decision.get("trade_risk_note", "")

        # Fallback: parse analysis text if trade_decision is empty
        if not trade_decision:
            analysis_text = result.get("analysis", "")
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', analysis_text, re.DOTALL)
            if json_match:
                try:
                    parsed = _json.loads(json_match.group())
                    should_trade = parsed.get("should_trade", False)
                    conviction = parsed.get("trade_conviction", parsed.get("conviction", 0))
                    allocation_pct = parsed.get("trade_allocation_pct", parsed.get("suggested_allocation_pct", 0))
                    trade_reasoning = parsed.get("trade_reasoning", parsed.get("reasoning", ""))
                    trade_side = parsed.get("trade_side", parsed.get("side", "buy"))
                    trade_risk_note = parsed.get("trade_risk_note", parsed.get("risk_note", ""))
                except _json.JSONDecodeError:
                    pass

        if should_trade and conviction >= 75:
            from ml.trading_engine import compute_allocation_pct
            sized_pct = compute_allocation_pct(conviction, allocation_pct, coin_data)
            amount = remaining * (sized_pct / 100)
            amount = min(amount, remaining)

            proposal = engine.propose_trade(
                symbol=symbol,
                side=trade_side,
                amount_gbp=round(amount, 2),
                current_price=current_price,
                reason=trade_reasoning[:500] if trade_reasoning else "Multi-agent system recommended trade",
                confidence=conviction,
                recommendation="BUY" if trade_side == "buy" else "SELL",
            )
            proposal["agent_decision"] = trade_decision
            proposal["agents_used"] = result.get("agents_used", [])
            return jsonify(proposal), 200
        else:
            return jsonify({
                "success": True,
                "should_trade": False,
                "reason": trade_reasoning or "Multi-agent system decided not to trade",
                "trade_risk_note": trade_risk_note,
                "agents_used": result.get("agents_used", []),
            }), 200

    except Exception as e:
        logger.error(f"Auto-evaluate error: {e}")
        return jsonify({"error": "Failed to evaluate trade"}), 500


# ========================================
# Scan Loop Routes
# ========================================

@portfolio_bp.route('/api/trades/scan-now', methods=['POST'])
@limiter.limit('5 per hour')
@require_trading_auth
def scan_now():
    """Trigger an on-demand scan of all tradeable coins."""
    try:
        from ml.scan_loop import get_scan_loop
        scanner = get_scan_loop()
        result = scanner.run_scan(triggered_by="manual_api")
        return jsonify(result), 200 if result.get("success") else 429
    except Exception as e:
        logger.error(f"Scan-now error: {e}")
        return jsonify({"error": "Failed to run scan"}), 500


@portfolio_bp.route('/api/trades/scan-status')
@require_trading_auth
def scan_status():
    """Get scan loop status and recent scan results."""
    try:
        from ml.scan_loop import get_scan_loop
        scanner = get_scan_loop()
        return jsonify({
            "status": scanner.get_status(),
            "recent_logs": scanner.get_recent_logs(days=3),
        }), 200
    except Exception as e:
        logger.error(f"Scan status error: {e}")
        return jsonify({"error": "Failed to get scan status"}), 500


@portfolio_bp.route('/api/trades/audit-trail')
@require_trading_auth
def audit_trail():
    """Get recent audit trail entries."""
    try:
        from ml.scan_loop import get_scan_loop
        scanner = get_scan_loop()
        limit = min(request.args.get('limit', 100, type=int), 500)
        return jsonify({"entries": scanner.get_audit_trail(limit=limit)}), 200
    except Exception as e:
        logger.error(f"Audit trail error: {e}")
        return jsonify({"error": "Failed to get audit trail"}), 500


# ========================================
# Market Monitor Routes
# ========================================

@portfolio_bp.route('/api/monitor/status')
@require_trading_auth
def monitor_status():
    """Get market monitor status — intervals, stats, alerts."""
    try:
        from ml.market_monitor import get_market_monitor
        monitor = get_market_monitor()
        return jsonify(monitor.get_status()), 200
    except Exception as e:
        logger.error(f"Monitor status error: {e}")
        return jsonify({"error": "Market monitor not available"}), 500


@portfolio_bp.route('/api/monitor/alerts')
@require_trading_auth
def monitor_alerts():
    """Get recent market monitor alerts."""
    try:
        from ml.market_monitor import get_market_monitor
        monitor = get_market_monitor()
        limit = request.args.get('limit', 50, type=int)
        return jsonify({"alerts": monitor.get_recent_alerts(limit=limit)}), 200
    except Exception as e:
        logger.error(f"Monitor alerts error: {e}")
        return jsonify({"error": "Failed to get monitor alerts"}), 500


@portfolio_bp.route('/api/monitor/price-history/<symbol>')
@require_trading_auth
def monitor_price_history(symbol):
    """Get recent price snapshots for a symbol from the monitor."""
    try:
        from ml.market_monitor import get_market_monitor
        monitor = get_market_monitor()
        return jsonify({"symbol": symbol.upper(), "history": monitor.get_price_history(symbol)}), 200
    except Exception as e:
        logger.error(f"Price history error: {e}")
        return jsonify({"error": "Failed to get price history"}), 500


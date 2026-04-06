"""
Debate Orchestrator — Bull vs Bear architecture.
Three-agent pipeline: bull advocate -> bear advocate -> referee.

Each coin costs 3 Gemini calls (vs 6 for the 5-agent orchestrator), allowing
more coins to reach full analysis per scan within the same API budget.

Returns the same dict shape as analyze_crypto() for drop-in compatibility.
"""

import os
import re
import json
import logging
from typing import Dict, Any, Optional

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

logger = logging.getLogger(__name__)

_DEBATE_MODEL = os.getenv("DEBATE_AGENT_MODEL", os.getenv("ORCHESTRATOR_MODEL", "gemini-2.0-flash"))


# ─── Agent Definitions ────────────────────────────────────────

bull_advocate = Agent(
    name="bull_advocate",
    description="Builds the strongest possible buy case for a coin",
    model=_DEBATE_MODEL,
    instruction="""You are a passionate crypto bull analyst. Your sole job is to build the strongest possible case for buying a coin. Be direct, specific, and opinionated. Reference actual numbers from the data.

Return JSON with exactly 2 fields:
{
  "bull_case": "3-5 sentences. Reference specific price levels, % changes, volume, market cap, catalysts. No hedging.",
  "bull_conviction": 0-100
}

bull_conviction guide:
- 80-100: Compelling — strong momentum, clear catalysts, attractive valuation
- 60-79: Good case — clear upside, worth a punt at this price
- 40-59: Moderate — some positive signals but speculative
- 0-39: Weak — only minor positives even from the bull side

Focus on: momentum signals, undervaluation vs peers, upcoming catalysts, community strength, asymmetric risk/reward.
Do NOT hedge. Make the bull case as strong as the data allows. Primary focus is low-cap gems (sub-$100M mcap) but a genuinely compelling mid-cap setup is equally valid.""",
)

bear_advocate = Agent(
    name="bear_advocate",
    description="Dismantles the bull case and surfaces every risk",
    model=_DEBATE_MODEL,
    instruction="""You are a sharp crypto skeptic. You receive a bull case for a coin and your job is to dismantle it. Find every reason this trade could go wrong.

Return JSON with exactly 2 fields:
{
  "bear_case": "3-5 sentences attacking the bull argument. Reference specific weaknesses in the data. No hedging.",
  "bear_conviction": 0-100
}

bear_conviction guide (how strong is the case AGAINST buying):
- 80-100: Serious red flags — likely to lose money
- 60-79: Meaningful risks that aren't compensated by the upside case
- 40-59: Some valid concerns but manageable
- 0-39: Weak bear case — risks are minor, bull case holds up

Read the bull case carefully and target its weakest arguments. Look for: overvalued vs peers, fading volume, project red flags, better alternatives, pump-and-dump signals, lack of real utility, thin liquidity.""",
)

referee_agent = Agent(
    name="referee",
    description="Portfolio-aware judge that weighs bull and bear cases to make a final trade decision",
    model=_DEBATE_MODEL,
    instruction="""You are a portfolio-aware trading referee. You receive a bull case and bear case for a coin, plus current portfolio state, and must make the final trade decision.

Return JSON with exactly these fields:
{
  "should_trade": true or false,
  "trade_side": "buy",
  "trade_conviction": 0-100,
  "trade_reasoning": "2-3 sentences. Explain which side won and why, referencing both cases.",
  "trade_risk_note": "One sentence on the single biggest risk.",
  "trade_allocation_pct": 0-100
}

Decision rules:
- BULL regime: bull_conviction must exceed bear_conviction by 10+ points to proceed
- NEUTRAL regime: bull_conviction must exceed bear_conviction by 20+ points to proceed
- BEAR regime: bull_conviction must exceed bear_conviction by 30+ points to proceed
- If portfolio already holds 4+ positions: require 10 extra conviction points
- Existing position shown: apply HOLD bias — only recommend SELL if thesis clearly broken

trade_conviction: Your independent conviction score (not an average of bull/bear scores)
trade_allocation_pct:
- 55-69 conviction: 40-60% of daily budget
- 70-84 conviction: 60-80%
- 85+ conviction: up to 100%
- 0 if should_trade is false""",
)


# ─── Helpers ──────────────────────────────────────────────────

def _run_agent(agent: Agent, prompt: str, session_id: str) -> str:
    """Run a single ADK agent synchronously and return its full text output."""
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="debate_app",
        agent=agent,
        session_service=session_service,
        auto_create_session=True,
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    result_text = ""
    for event in runner.run(user_id="debate_user", session_id=session_id, new_message=message):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    result_text += part.text
    return result_text


def _parse_json(text: str) -> Optional[Dict]:
    """Parse JSON from agent response, handling markdown code fences."""
    clean = re.sub(r'```(?:json)?\s*', '', text).strip().strip('`').strip()
    try:
        return json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        pass
    match = re.search(r'\{.*\}', clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _detect_regime() -> str:
    """Detect market regime from BTC 7-day price change."""
    try:
        import services.app_state as state
        if state.analyzer and state.analyzer.coins:
            for coin in state.analyzer.coins:
                if getattr(coin, "symbol", "").upper() in ("BTC", "WBTC"):
                    pct = float(getattr(coin, "price_change_7d", 0) or 0)
                    if pct > 10:
                        return "bull"
                    if pct < -10:
                        return "bear"
                    return "neutral"
    except Exception:
        pass
    return "neutral"


# ─── Main Debate Function ─────────────────────────────────────

async def analyze_crypto_debate(
    symbol: str,
    coin_data: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    market_regime: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run bull-vs-bear debate analysis on a coin.

    Three sequential Gemini calls:
    1. BullAdvocate builds the strongest buy case
    2. BearAdvocate reads the bull case and dismantles it
    3. Referee weighs both cases with portfolio context and decides

    Returns the same shape as analyze_crypto() for drop-in compatibility.
    """
    import time
    session_id = session_id or f"debate_{symbol}_{int(time.time())}"
    regime = market_regime or _detect_regime()

    # Build market data string (same format as full orchestrator)
    from .orchestrator import _build_market_data_str, _build_position_context, _build_trade_history_context
    market_data_str = _build_market_data_str(coin_data, symbol)
    position_block = _build_position_context(coin_data)
    trade_history_ctx = _build_trade_history_context()

    play_type = coin_data.get("play_type", "accumulate") if coin_data else "accumulate"

    logger.info(f"[Debate] Starting bull/bear debate for {symbol} (regime={regime})")

    # ── Step 1: Bull Advocate ──────────────────────────────────
    bull_prompt = (
        f"Coin: {symbol} | Play type: {play_type} | Market regime: {regime}\n"
        f"Data: {market_data_str}{position_block}\n\n"
        f"Build the strongest possible buy case for {symbol} right now.\n"
        f'Return JSON: {{"bull_case": "...", "bull_conviction": 0-100}}'
    )

    bull_text = ""
    bull_case = ""
    bull_conviction = 0
    try:
        bull_text = _run_agent(bull_advocate, bull_prompt, f"{session_id}_bull")
        parsed = _parse_json(bull_text)
        if parsed:
            bull_case = str(parsed.get("bull_case", ""))
            bull_conviction = int(parsed.get("bull_conviction", 0))
        logger.info(f"[Debate] {symbol}: bull conviction={bull_conviction}")
    except Exception as e:
        logger.warning(f"[Debate] Bull advocate failed for {symbol}: {e}")
        return {
            "success": False,
            "symbol": symbol,
            "error": f"Bull advocate failed: {e}",
            "orchestrator": "debate_orchestrator",
        }

    # ── Step 2: Bear Advocate ──────────────────────────────────
    bear_prompt = (
        f"Coin: {symbol} | Market regime: {regime}\n"
        f"Data: {market_data_str}\n\n"
        f"Bull case to dismantle:\n{bull_case}\n"
        f"Bull conviction: {bull_conviction}/100\n\n"
        f"Find every reason this trade could go wrong.\n"
        f'Return JSON: {{"bear_case": "...", "bear_conviction": 0-100}}'
    )

    bear_text = ""
    bear_case = ""
    bear_conviction = 0
    try:
        bear_text = _run_agent(bear_advocate, bear_prompt, f"{session_id}_bear")
        parsed = _parse_json(bear_text)
        if parsed:
            bear_case = str(parsed.get("bear_case", ""))
            bear_conviction = int(parsed.get("bear_conviction", 0))
        logger.info(f"[Debate] {symbol}: bear conviction={bear_conviction}")
    except Exception as e:
        logger.warning(f"[Debate] Bear advocate failed for {symbol}: {e}")
        bear_case = "Bear advocate unavailable."
        bear_conviction = 0

    # ── Step 3: Referee ────────────────────────────────────────
    portfolio_summary = {}
    try:
        from ml.portfolio_tracker import get_portfolio_tracker
        portfolio_summary = get_portfolio_tracker().get_portfolio_summary_for_agents()
    except Exception:
        pass

    history_block = f"\n\n{trade_history_ctx}" if trade_history_ctx else ""
    portfolio_block = (
        f"\n\nCurrent portfolio: {portfolio_summary.get('position_count', 0)} positions, "
        f"symbols: {', '.join(portfolio_summary.get('held_symbols', [])) or 'none'}, "
        f"total cost: £{portfolio_summary.get('total_cost_gbp', 0):.2f}"
        if portfolio_summary else ""
    )

    referee_prompt = (
        f"Coin: {symbol} | Market regime: {regime}\n"
        f"Data: {market_data_str}{position_block}{portfolio_block}{history_block}\n\n"
        f"BULL CASE (conviction {bull_conviction}/100):\n{bull_case}\n\n"
        f"BEAR CASE (conviction {bear_conviction}/100):\n{bear_case}\n\n"
        f"Weigh both cases and decide. Apply regime rules and portfolio concentration check.\n"
        f'Return JSON: {{"should_trade": bool, "trade_side": "buy", "trade_conviction": 0-100, '
        f'"trade_reasoning": "...", "trade_risk_note": "...", "trade_allocation_pct": 0-100}}'
    )

    verdict = {}
    referee_text = ""
    try:
        referee_text = _run_agent(referee_agent, referee_prompt, f"{session_id}_ref")
        parsed = _parse_json(referee_text)
        if parsed:
            verdict = {
                "should_trade": bool(parsed.get("should_trade", False)),
                "trade_side": str(parsed.get("trade_side", "buy")),
                "trade_conviction": int(parsed.get("trade_conviction", 0)),
                "trade_reasoning": str(parsed.get("trade_reasoning", "")),
                "trade_risk_note": str(parsed.get("trade_risk_note", "")),
                "trade_allocation_pct": float(parsed.get("trade_allocation_pct", 0)),
            }
    except Exception as e:
        logger.warning(f"[Debate] Referee failed for {symbol}: {e}")

    # Fallback verdict from bull/bear convictions if referee failed
    if not verdict:
        margin = {"bull": 10, "neutral": 20, "bear": 30}.get(regime, 20)
        concentration_penalty = 10 if portfolio_summary.get("position_count", 0) >= 4 else 0
        net_bull = bull_conviction - bear_conviction - concentration_penalty
        should_trade = net_bull >= margin
        verdict = {
            "should_trade": should_trade,
            "trade_side": "buy",
            "trade_conviction": bull_conviction if should_trade else 0,
            "trade_reasoning": f"Bull {bull_conviction} vs Bear {bear_conviction} in {regime} regime (referee unavailable).",
            "trade_risk_note": bear_case[:120] if bear_case else "Unknown.",
            "trade_allocation_pct": max(0, min(60, bull_conviction - 10)) if should_trade else 0,
        }

    final_conviction = verdict.get("trade_conviction", 0)
    logger.info(
        f"[Debate] {symbol}: referee verdict — should_trade={verdict.get('should_trade')}, "
        f"conviction={final_conviction}"
    )

    return {
        "success": True,
        "symbol": symbol,
        "session_id": session_id,
        "recommendation": "BUY" if verdict.get("should_trade") else "SKIP",
        "analysis": f"BULL CASE:\n{bull_case}\n\nBEAR CASE:\n{bear_case}\n\nREFEREE:\n{verdict.get('trade_reasoning', '')}",
        "all_agent_texts": {
            "bull_advocate": bull_text,
            "bear_advocate": bear_text,
            "referee": referee_text,
        },
        "trade_decision": verdict,
        "confidence": final_conviction,
        "orchestrator": "debate_orchestrator",
        "agents_used": ["bull_advocate", "bear_advocate", "referee"],
        "memory_enabled": False,
        "debate": {
            "bull_conviction": bull_conviction,
            "bear_conviction": bear_conviction,
            "regime": regime,
            "portfolio_positions": portfolio_summary.get("position_count", 0),
        },
    }

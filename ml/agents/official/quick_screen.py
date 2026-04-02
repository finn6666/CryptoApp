"""
Quick Screen Agent — Tier 1 lightweight LLM filter.
Single Gemini call to triage coins before the full multi-agent pipeline.
Saves ~80% of API calls by filtering out obvious skips early.
"""

import os
import logging
from typing import Dict, Any, Optional
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_session_service = InMemorySessionService()

# Use a lighter/cheaper model for quick screen — it's a binary triage filter,
# not a deep analysis. Override via QUICK_SCREEN_MODEL env var if needed.
_QUICK_SCREEN_MODEL = os.getenv("QUICK_SCREEN_MODEL", "gemini-2.0-flash")


class QuickScreenResult(BaseModel):
    """Lightweight screen result — just enough to decide pass/skip."""
    action: str = Field(description="PASS or SKIP")
    confidence: int = Field(ge=0, le=100, description="How confident 0-100 that this coin is worth full analysis")
    one_liner: str = Field(description="One sentence explanation")
    play_type: str = Field(default="accumulate", description="accumulate or swing — only relevant when action is PASS")


quick_screen_agent = Agent(
    name="quick_screener",
    description="Fast single-pass coin screener for triage",
    model=_QUICK_SCREEN_MODEL,
    instruction="""You are a fast crypto screener. Given a coin's market data, decide in ONE call whether it deserves deep multi-agent analysis.

Return JSON with exactly 3 fields:
- action: "PASS" (worth analysing further) or "SKIP" (not interesting)
- confidence: 0-100 how confident you are this coin is worth buying
- one_liner: one sentence why

PASS criteria (be generous — we want to find gems):
- Active project with real use case or strong community hype
- Price action showing momentum or a dip in a fundamentally strong coin
- Low cap with asymmetric upside potential
- New coin with genuine buzz (even without track record)

SKIP criteria:
- Dead project (no volume, no development, flatlined price)
- Pure scam/rugpull signals (tiny mcap + no community + suspicious tokenomics)
- Stagnant coin with no catalysts and declining volume
- Already overextended (massive recent pump with no substance)

When action is PASS, also set play_type:
- "swing": strong short-term momentum signal (large 24h spike, volume surge) but limited fundamental story. Best held hours to a few days.
- "accumulate": strong fundamentals, undervalued, growing ecosystem — hold weeks to months. Default if uncertain.

Keep your reasoning to ONE sentence. Speed matters — don't overthink it.
Remember: primary focus is low-cap gems (under £1, sub-$100M mcap) for asymmetric upside. But if a mid-cap or higher-priced coin has a legitimately strong setup — strong momentum, upcoming catalyst, clear fundamentals — do NOT skip it just because of price or market cap. A great trade is a great trade. Be biased toward finding opportunities.""",
)


async def quick_screen_coin(
    symbol: str,
    coin_data: Dict[str, Any],
    trade_history_ctx: str = "",
) -> Dict[str, Any]:
    """
    Run a single-call quick screen on a coin.

    Returns:
        {"pass": bool, "confidence": int, "one_liner": str}
    """
    runner = Runner(
        app_name="quick_screen_app",
        agent=quick_screen_agent,
        session_service=_session_service,
        auto_create_session=True,
    )

    # Build a compact data line
    parts = [
        f"{coin_data.get('name', symbol)} ({symbol})",
        f"£{coin_data.get('price', '?')}",
        f"24h: {coin_data.get('price_change_24h', '?')}%",
        f"7d: {coin_data.get('price_change_7d', '?')}%",
        f"Rank: #{coin_data.get('market_cap_rank', '?')}",
        f"MCap: £{coin_data.get('market_cap', '?')}",
        f"Vol: £{coin_data.get('volume_24h', '?')}",
    ]
    gem_score = coin_data.get("gem_score")
    if gem_score is not None:
        parts.append(f"GemScore: {gem_score:.1f}")

    data_line = " | ".join(parts)
    history_block = f"\n{trade_history_ctx}" if trade_history_ctx else ""

    prompt = f"""Quick screen: {data_line}{history_block}
Return JSON: {{"action": "PASS"|"SKIP", "confidence": 0-100, "play_type": "accumulate"|"swing", "one_liner": "..."}}"""

    try:
        message = types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        )

        result_text = ""
        for event in runner.run(
            user_id="screener",
            session_id=f"screen_{symbol}",
            new_message=message,
        ):
            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        result_text += part.text

        # Parse JSON from response.
        # Handle markdown code fences (```json ... ```) and nested objects.
        # The old flat regex \{[^{}]*\} broke on any nested field the model returned.
        import json, re
        parsed = None
        # Strip markdown code fences first
        clean = re.sub(r'```(?:json)?\s*', '', result_text).strip().strip('`').strip()
        # Try direct parse
        try:
            parsed = json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            pass
        # Fallback: greedy outermost {} — handles extra text around the JSON
        if not parsed:
            json_match = re.search(r'\{.*\}', clean, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                except (json.JSONDecodeError, ValueError):
                    pass

        if parsed:
            action = str(parsed.get("action", "SKIP")).upper().strip()
            confidence = int(parsed.get("confidence", 0))
            one_liner = str(parsed.get("one_liner", ""))
            return {
                "pass": action == "PASS",
                "confidence": max(0, min(100, confidence)),
                "one_liner": one_liner,
                "play_type": str(parsed.get("play_type", "accumulate")).lower(),
            }

        logger.warning(f"Quick screen for {symbol}: could not parse response — passing to be safe")
        # Pass through so parse failures never silently block coins from analysis.
        # Confidence=100 ensures this reaches the full pipeline regardless of the
        # SCAN_QUICK_SCREEN_MIN threshold.
        return {"pass": True, "confidence": 100, "one_liner": "Could not parse screen result — passing to be safe", "play_type": "accumulate"}

    except Exception as e:
        logger.warning(f"Quick screen failed for {symbol}: {e}")
        # On error, pass through to avoid missing opportunities
        return {"pass": True, "confidence": 100, "one_liner": f"Screen error: {e}", "play_type": "accumulate"}

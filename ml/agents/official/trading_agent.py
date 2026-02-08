"""
Official Google ADK Trading Agent
Evaluates agent analysis and proposes real trades with safety checks.
"""

import logging
from typing import Dict, Any
from google.adk import Agent
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TradeDecision(BaseModel):
    """Structured output for trade decisions"""
    should_trade: bool = Field(description="Whether to propose a trade")
    side: str = Field(description="Trade side: buy or sell")
    conviction: int = Field(ge=0, le=100, description="How strongly the agent feels about this trade 0-100")
    reasoning: str = Field(description="2-3 sentence explanation of WHY this trade, specific to this coin")
    risk_note: str = Field(description="One sentence on the biggest risk")
    suggested_allocation_pct: float = Field(
        ge=0, le=100,
        description="What % of the daily budget to use on this trade (0-100)"
    )


# Create official ADK trading agent
trading_agent = Agent(
    name="trading_specialist",
    description="Cryptocurrency trade execution specialist — decides whether analysis warrants a real trade",
    model="gemini-3-flash-preview",
    instruction="""You are a crypto trade execution specialist. You receive analysis from the research team and decide whether it warrants spending REAL money.

**Context:** The user has a TINY daily budget (around 5p). Every penny counts. Only propose trades when you're genuinely convinced.

**Rules:**
1. Only propose BUY trades with conviction ≥75% — this is real money
2. Never propose trades on coins you don't recognise or can't find real info about
3. Be specific about WHY — "it's going up" is not a reason. "Dogecoin has 3x'd in meme seasons before and social sentiment is spiking" IS a reason
4. The suggested_allocation_pct should reflect confidence: 75% conviction = 30-50% of budget, 90%+ = up to 100%
5. Set should_trade=false if the analysis is mediocre, generic, or based on placeholder data
6. For SELL decisions, only propose if the user holds the coin and the outlook has turned negative
7. Always include the specific risk — "anonymous team", "single exchange", "whale dump risk", etc.

**Think like you're spending your own beer money.** If you wouldn't put YOUR 5p on this, don't propose it.

Return valid JSON matching TradeDecision schema.""",
    output_schema=TradeDecision,
)


async def evaluate_trade(
    symbol: str,
    analysis: Dict[str, Any],
    current_price: float,
    daily_budget_remaining: float,
) -> Dict[str, Any]:
    """
    Evaluate whether an analysis warrants a real trade.
    
    Args:
        symbol: Coin symbol
        analysis: Agent analysis results (gem_score, recommendation, etc.)
        current_price: Current price in GBP
        daily_budget_remaining: How much budget is left today
        
    Returns:
        Trade decision dict
    """
    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    session_service = InMemorySessionService()
    runner = Runner(
        app_name="trade_decision_app",
        agent=trading_agent,
        session_service=session_service,
        auto_create_session=True,
    )

    # Build prompt with real data
    gem_score = analysis.get("gem_score", 0)
    recommendation = analysis.get("recommendation", "HOLD")
    confidence = analysis.get("confidence", 0)
    risk_level = analysis.get("risk_level", "Unknown")
    summary = analysis.get("summary", "No summary")
    strengths = analysis.get("key_strengths", [])
    weaknesses = analysis.get("key_weaknesses", [])

    prompt = f"""Should I spend real money on {symbol}?

Price: £{current_price:.6f}
Budget remaining today: £{daily_budget_remaining:.4f}
Agent gem score: {gem_score}/100
Agent recommendation: {recommendation}
Agent confidence: {confidence}%
Risk level: {risk_level}

Summary: {summary}

Strengths: {'; '.join(strengths[:3]) if strengths else 'None listed'}
Weaknesses: {'; '.join(weaknesses[:3]) if weaknesses else 'None listed'}

Based on this analysis, should I place a real trade? Remember this is real money — be honest."""

    try:
        user_message = types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        )

        response_text = ""
        for event in runner.run(
            user_id="trader",
            session_id=f"trade_{symbol}",
            new_message=user_message,
        ):
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text

        return {
            "success": True,
            "symbol": symbol,
            "decision_raw": response_text,
        }

    except Exception as e:
        logger.error(f"Trade evaluation failed for {symbol}: {e}")
        return {"success": False, "error": str(e)}

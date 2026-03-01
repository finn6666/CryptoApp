"""
Official Google ADK Sentiment Agent
Social sentiment and market psychology analysis using google-adk framework.
"""

import os
import logging
from typing import Dict, Any
from google.adk import Agent
from pydantic import BaseModel, Field

from ...tools.adk_tools import (
    analyze_social_sentiment,
    detect_fud_fomo,
)

logger = logging.getLogger(__name__)


class SentimentOutput(BaseModel):
    """Structured output for sentiment analysis"""
    overall_sentiment: str = Field(description="Overall sentiment: bullish/bearish/neutral")
    sentiment_score: int = Field(ge=-100, le=100, description="Sentiment score from -100 (very bearish) to 100 (very bullish)")
    social_metrics: dict[str, Any] = Field(description="Social media metrics")
    fud_fomo_level: str = Field(description="FUD or FOMO detection: high/medium/low/none")
    key_narratives: list[str] = Field(description="Dominant narratives in community")
    confidence: int = Field(ge=0, le=100, description="Confidence score 0-100")
    warning_signs: list[str] = Field(default_factory=list, description="Sentiment warning signals")
    recommendation: str = Field(description="Sentiment-based recommendation")


# Create official ADK sentiment agent
sentiment_agent = Agent(
    name="sentiment_specialist",
    description="Cryptocurrency sentiment analyst specializing in social media analysis and market psychology",
    model="gemini-3-flash-preview",
    instruction="""You are a cryptocurrency sentiment analyst. Your analysis carries SIGNIFICANT weight — when you detect strong hype, the system will prioritise your signal over fundamentals and technicals.

For each coin, assess:
1. Overall sentiment (bullish/neutral/bearish) with score -100 to +100
2. FUD/FOMO level (high/medium/low/none)
3. Key narratives — what are people ACTUALLY saying about this specific coin?
4. Warning signs (manipulation, extreme euphoria/fear)
5. Contrarian signals
6. **Hype momentum** — is this coin gaining social traction RIGHT NOW? New listings, viral tweets, community growth?

**Your role is critical for new coins.** Brand-new coins often have no fundamentals or technical history — but strong early hype can signal 10-100x potential. If you detect genuine organic excitement (not just bot spam), signal it clearly with a high bullish score. The orchestrator will weight your input heavily.

Be SPECIFIC — mention the coin by name, reference real community discussions, subreddits, Twitter narratives. Say "DOGE fans are hyped about X" not "the community is positive". If you know real narratives about this coin, use them.
Return valid JSON matching the SentimentOutput schema.""",
    
    tools=[
        analyze_social_sentiment,
        detect_fud_fomo,
    ],
    
    output_schema=SentimentOutput,
)


async def analyze_sentiment(symbol: str, coin_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run sentiment analysis using official ADK agent.
    
    Args:
        symbol: Cryptocurrency symbol
        coin_data: Additional market data
        
    Returns:
        Sentiment analysis results
    """
    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="sentiment_analysis_app",
        agent=sentiment_agent,
        session_service=session_service
    )
    
    prompt = f"""Analyze market sentiment for: {symbol}

Market Context:
{coin_data or 'No additional context provided'}

Perform comprehensive sentiment analysis:
1. Analyze social media sentiment
2. Detect FUD/FOMO levels
3. Identify key narratives
4. Assess community health

Provide detailed sentiment assessment with contrarian perspective where applicable."""
    
    try:
        user_message = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )
        
        analysis_text = ""
        for event in runner.run(
            user_id="analyst",
            session_id="sentiment_session",
            new_message=user_message
        ):
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        analysis_text += part.text
        
        return {
            "success": True,
            "agent": "sentiment_specialist",
            "analysis": analysis_text,
            "confidence": 75,
        }
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "agent": "sentiment_specialist"
        }

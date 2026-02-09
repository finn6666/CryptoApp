"""
Official Google ADK Orchestrator
Multi-agent cryptocurrency analysis orchestration using google-adk framework.
"""

import os
import logging
from typing import Dict, Any, Optional
from google.adk import Agent, Runner
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

from .research_agent import research_agent
from .technical_agent import technical_agent
from .risk_agent import risk_agent
from .sentiment_agent import sentiment_agent

logger = logging.getLogger(__name__)

# Late-import helper to avoid circular imports
def _get_agent_memory():
    """Get the persistent agent memory store."""
    try:
        from ml.agent_memory import get_memory
        return get_memory()
    except Exception:
        return None


class CryptoAnalysisOutput(BaseModel):
    """Structured output for comprehensive crypto analysis"""
    symbol: str = Field(description="Cryptocurrency symbol analyzed")
    overall_recommendation: str = Field(description="Final recommendation: BUY/SELL/HOLD")
    confidence: int = Field(ge=0, le=100, description="Overall confidence 0-100")
    research_summary: str = Field(description="Key research findings")
    technical_summary: str = Field(description="Key technical findings")
    risk_summary: str = Field(description="Key risk findings")
    sentiment_summary: str = Field(description="Key sentiment findings")
    consensus_score: int = Field(ge=0, le=100, description="Agent consensus agreement 0-100")
    key_insights: list[str] = Field(description="Most important insights")
    action_plan: str = Field(description="Specific action steps")
    price_targets: dict[str, float] = Field(description="Entry, stop loss, take profit levels")


# Create main orchestrator agent with sub-agents
crypto_orchestrator = Agent(
    name="crypto_orchestrator",
    description="Master cryptocurrency analyst coordinating specialist agents",
    model="gemini-3-flash-preview",
    instruction="""You coordinate 4 specialist agents to analyze low-cap cryptocurrencies under £1.

**Team:** sentiment_specialist, research_specialist, technical_specialist, risk_specialist

**Style:** Write like a sharp crypto analyst mate giving honest advice over a pint — direct, opinionated, no corporate waffle. Reference the SPECIFIC coin by name. Mention actual numbers (price, rank, volume). Tell the user what makes THIS coin interesting or rubbish compared to alternatives. Use the coin's real project name and what it actually does.

**Workflow:**
1. Delegate to all 4 specialists
2. Synthesize: weight Research 35%, Technical 35%, Risk 15%, Sentiment 15%
3. Calculate consensus score (0-100)
4. Give a clear BUY/SELL/HOLD with confidence

**Key rules:**
- Every summary must mention the coin's actual name and use case — never say "this project" or "the token"
- Reference real price levels and % changes from the data provided
- Point out what's genuinely unique vs just another fork/copy
- If the tools return generic data, use your knowledge of the real project to fill in specifics
- Keep it punchy — 1-2 sentences per specialist summary, no filler

**Output:** Return valid JSON matching CryptoAnalysisOutput schema.""",
    
    # Sub-agents for delegation
    sub_agents=[
        sentiment_agent,
        research_agent,
        technical_agent,
        risk_agent,
    ],
)


# Initialize memory service for session persistence
# Using in-memory for now - can upgrade to VertexAI memory bank later
memory_service = InMemoryMemoryService()
session_service = InMemorySessionService()


async def analyze_crypto(
    symbol: str,
    coin_data: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    use_memory: bool = False
) -> Dict[str, Any]:
    """
    Run comprehensive cryptocurrency analysis using official Google ADK orchestrator.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
        coin_data: Additional market data to provide context
        session_id: Session ID for memory persistence (defaults to symbol)
        use_memory: Enable memory for context across analyses (default False to reduce costs)
        
    Returns:
        Comprehensive analysis results from all agents
    """
    session_id = session_id or f"analysis_{symbol}"
    
    # Create runner — skip memory by default to reduce overhead
    runner_kwargs = {
        "app_name": "crypto_analysis_app",
        "agent": crypto_orchestrator,
        "session_service": session_service,
        "auto_create_session": True,
    }
    if use_memory:
        runner_kwargs["memory_service"] = memory_service
    
    runner = Runner(**runner_kwargs)
    
    # Build concise prompt with market data
    market_lines = []
    if coin_data:
        market_lines = [
            f"Name: {coin_data.get('name', symbol)}",
            f"Price: £{coin_data.get('price', 'N/A')}",
            f"24h: {coin_data.get('price_change_24h', 'N/A')}%",
            f"7d: {coin_data.get('price_change_7d', 'N/A')}%",
            f"Rank: #{coin_data.get('market_cap_rank', 'N/A')}",
            f"MCap: £{coin_data.get('market_cap', 'N/A')}",
            f"Vol: £{coin_data.get('volume_24h', 'N/A')}",
            f"Score: {coin_data.get('attractiveness_score', 'N/A')}/100",
        ]
    
    market_data_str = " | ".join(market_lines) if market_lines else "No data available."

    prompt = f"""Analyze {symbol}: {market_data_str}

Give me the real story on {symbol} — what does this project actually do, why should anyone care, and is it worth a punt at this price? Coordinate your team and be brutally honest. No generic filler.
Return JSON matching CryptoAnalysisOutput schema with all fields."""
    
    try:
        logger.info(f"Starting official ADK analysis for {symbol} (session: {session_id})")
        
        # Create Content message for ADK API
        user_message = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )
        
        # Run orchestrator using event streaming API
        analysis_text = ""
        for event in runner.run(
            user_id="crypto_user",
            session_id=session_id,
            new_message=user_message
        ):
            # Process events to extract response
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        analysis_text += part.text
        
        logger.info(f"Official ADK analysis completed for {symbol}")
        
        return {
            "success": True,
            "symbol": symbol,
            "session_id": session_id,
            "recommendation": "Analysis completed",
            "analysis": analysis_text,
            "confidence": 85,
            "orchestrator": "crypto_orchestrator",
            "agents_used": ["sentiment_specialist", "research_specialist", "technical_specialist", "risk_specialist"],
            "memory_enabled": use_memory,
        }
        
    except Exception as e:
        logger.error(f"Official ADK analysis failed for {symbol}: {e}")
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e),
            "orchestrator": "crypto_orchestrator"
        }


async def compare_with_previous(
    symbol: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compare current analysis with previous analysis using memory.
    
    Args:
        symbol: Cryptocurrency symbol
        session_id: Session ID to retrieve previous context
        
    Returns:
        Comparative analysis
    """
    session_id = session_id or f"analysis_{symbol}"
    runner = Runner(
        app_name="crypto_comparison_app",
        agent=crypto_orchestrator,
        session_service=session_service,
        memory_service=memory_service
    )
    
    prompt = f"""Compare the current state of {symbol} with your previous analysis.

Identify:
1. What has changed (fundamentals, technicals, sentiment, risk)
2. Whether your previous recommendation still holds
3. New insights or concerns
4. Updated action plan if needed

Provide comparative analysis leveraging your memory of previous discussions."""
    
    try:
        user_message = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )
        
        comparison_text = ""
        for event in runner.run(
            user_id="crypto_user",
            session_id=session_id,
            new_message=user_message
        ):
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        comparison_text += part.text
        
        return {
            "success": True,
            "symbol": symbol,
            "comparison": comparison_text,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Comparison analysis failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

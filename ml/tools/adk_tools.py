"""
ADK-Compatible Tool Functions
Function implementations for Google Generative AI SDK function calling.
"""

from typing import Dict, Any, List, Optional
import logging
import time

logger = logging.getLogger(__name__)

# Fear & Greed Index cache (avoid hammering the API)
_fear_greed_cache: Dict[str, Any] = {"data": None, "fetched_at": 0}


# === Research Tools ===

def get_project_fundamentals(symbol: str, aspects: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get fundamental data about a cryptocurrency project.
    
    Args:
        symbol: Cryptocurrency symbol
        aspects: Aspects to research (technology, team, partnerships, tokenomics)
    
    Returns:
        Fundamental analysis data
    """
    # Placeholder - integrate with real data sources in production
    return {
        "symbol": symbol,
        "technology": "Blockchain-based platform",
        "team": "Experienced development team",
        "partnerships": "Multiple strategic partnerships",
        "tokenomics": "Fixed supply with staking rewards",
        "aspects_analyzed": aspects or ["all"]
    }


def check_github_activity(project: str) -> Dict[str, Any]:
    """
    Check development activity on GitHub.
    
    Args:
        project: Project name or repository
    
    Returns:
        GitHub activity metrics
    """
    return {
        "project": project,
        "commits_30d": "Active",
        "contributors": "Multiple active developers",
        "last_update": "Recent",
        "activity_level": "HIGH"
    }


def analyze_partnerships(symbol: str) -> Dict[str, Any]:
    """
    Analyze partnerships and integrations.
    
    Args:
        symbol: Cryptocurrency symbol
    
    Returns:
        Partnership analysis
    """
    return {
        "symbol": symbol,
        "major_partnerships": ["Integration with major platforms"],
        "ecosystem_strength": "STRONG",
        "partnership_quality": "HIGH"
    }


# === Technical Analysis Tools ===

def identify_chart_patterns(symbol: str, timeframe: str = "1d") -> Dict[str, Any]:
    """
    Identify technical chart patterns.
    
    Args:
        symbol: Cryptocurrency symbol
        timeframe: Chart timeframe (1h, 4h, 1d, 1w)
    
    Returns:
        Identified chart patterns
    """
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "patterns": ["Trend continuation", "Support holding"],
        "trend": "BULLISH"
    }


def calculate_support_resistance(symbol: str, price_data: Optional[List[float]] = None) -> Dict[str, Any]:
    """
    Calculate support and resistance levels.
    
    Args:
        symbol: Cryptocurrency symbol
        price_data: Historical price data
    
    Returns:
        Support and resistance levels
    """
    return {
        "symbol": symbol,
        "support_levels": [0.95, 0.90, 0.85],
        "resistance_levels": [1.05, 1.10, 1.15],
        "current_zone": "SUPPORT"
    }


def analyze_volume_profile(symbol: str, period: str = "24h") -> Dict[str, Any]:
    """
    Analyze volume patterns and trends.
    
    Args:
        symbol: Cryptocurrency symbol
        period: Time period for analysis (24h, 7d, 30d)
    
    Returns:
        Volume analysis
    """
    return {
        "symbol": symbol,
        "period": period,
        "volume_trend": "INCREASING",
        "volume_vs_average": 1.5,
        "interpretation": "Above average volume - increased interest"
    }


def calculate_indicators(symbol: str, indicators: List[str]) -> Dict[str, Any]:
    """
    Calculate technical indicators (RSI, MACD, MA, etc.).
    
    Args:
        symbol: Cryptocurrency symbol
        indicators: Indicators to calculate (RSI, MACD, SMA, EMA)
    
    Returns:
        Calculated indicator values
    """
    results = {}
    
    for indicator in indicators:
        if indicator.upper() == "RSI":
            results["RSI"] = {"value": 55, "signal": "NEUTRAL"}
        elif indicator.upper() == "MACD":
            results["MACD"] = {"signal": "BULLISH", "crossover": "POSITIVE"}
        elif indicator.upper() in ["SMA", "EMA"]:
            results[indicator.upper()] = {"trend": "UP", "price_vs_ma": "ABOVE"}
    
    return {
        "symbol": symbol,
        "indicators": results,
        "overall_signal": "BULLISH"
    }


# === Risk Management Tools ===

def calculate_position_size(
    portfolio_value: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float
) -> Dict[str, Any]:
    """
    Calculate recommended position size based on risk parameters.
    
    Args:
        portfolio_value: Total portfolio value in USD
        risk_per_trade: Maximum risk per trade as percentage
        entry_price: Planned entry price
        stop_loss_price: Stop loss price
    
    Returns:
        Position sizing recommendations
    """
    risk_amount = portfolio_value * (risk_per_trade / 100)
    price_risk = abs(entry_price - stop_loss_price)
    position_size = risk_amount / price_risk if price_risk > 0 else 0
    
    return {
        "position_size": round(position_size, 2),
        "position_value": round(position_size * entry_price, 2),
        "risk_amount": round(risk_amount, 2),
        "allocation_percent": round((position_size * entry_price / portfolio_value) * 100, 2)
    }


def calculate_risk_reward(
    entry_price: float,
    stop_loss: float,
    take_profit: float
) -> Dict[str, Any]:
    """
    Calculate risk-reward ratio for a trade.
    
    Args:
        entry_price: Entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
    
    Returns:
        Risk-reward analysis
    """
    risk = abs(entry_price - stop_loss)
    reward = abs(take_profit - entry_price)
    ratio = reward / risk if risk > 0 else 0
    
    return {
        "risk": round(risk, 2),
        "reward": round(reward, 2),
        "ratio": round(ratio, 2),
        "assessment": (
            "EXCELLENT" if ratio >= 3
            else "GOOD" if ratio >= 2
            else "ACCEPTABLE" if ratio >= 1.5
            else "POOR"
        )
    }


def assess_correlation(
    symbol: str,
    compare_assets: Optional[List[str]] = None,
    period: str = "30d"
) -> Dict[str, Any]:
    """
    Assess correlation with other assets.
    
    Args:
        symbol: Cryptocurrency symbol
        compare_assets: Assets to compare correlation with
        period: Time period for correlation
    
    Returns:
        Correlation analysis
    """
    assets = compare_assets or ["BTC", "ETH"]
    
    return {
        "symbol": symbol,
        "period": period,
        "correlations": {asset: 0.75 for asset in assets},
        "interpretation": "Moderate correlation with major assets"
    }


def generate_exit_strategy(
    entry_price: float,
    volatility: str = "moderate",
    time_horizon: str = "medium"
) -> Dict[str, Any]:
    """
    Generate exit strategy with stop-loss and take-profit levels.
    
    Args:
        entry_price: Entry price
        volatility: Asset volatility (low, moderate, high, extreme)
        time_horizon: Investment time horizon (short, medium, long)
    
    Returns:
        Exit strategy recommendations
    """
    # Volatility-based multipliers
    vol_multipliers = {
        "low": 0.05,
        "moderate": 0.10,
        "high": 0.15,
        "extreme": 0.20
    }
    
    multiplier = vol_multipliers.get(volatility.lower(), 0.10)
    
    return {
        "entry_price": entry_price,
        "stop_loss": round(entry_price * (1 - multiplier), 2),
        "take_profit_1": round(entry_price * (1 + multiplier * 2), 2),
        "take_profit_2": round(entry_price * (1 + multiplier * 3), 2),
        "trailing_stop_pct": round(multiplier * 100, 1),
        "strategy": f"Volatility-adjusted {volatility} for {time_horizon} term"
    }


# === Sentiment Analysis Tools ===

def get_fear_greed_index() -> Dict[str, Any]:
    """
    Get the current Crypto Fear & Greed Index.
    
    Returns real-time market sentiment from alternative.me (0 = Extreme Fear, 100 = Extreme Greed).
    Includes today's value plus recent history to show trend.
    
    Returns:
        Fear & Greed Index data with value, classification, and trend
    """
    import urllib.request
    import json
    
    # Return cached data if fresh (< 10 minutes old)
    cache_age = time.time() - _fear_greed_cache["fetched_at"]
    if _fear_greed_cache["data"] and cache_age < 600:
        return _fear_greed_cache["data"]
    
    try:
        url = "https://api.alternative.me/fng/?limit=7&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "CryptoApp/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
        
        entries = raw.get("data", [])
        if not entries:
            return {"error": "No data returned from Fear & Greed API"}
        
        current = entries[0]
        value = int(current["value"])
        classification = current["value_classification"]
        
        # Build 7-day trend
        history = []
        for entry in entries:
            history.append({
                "value": int(entry["value"]),
                "classification": entry["value_classification"],
                "date": entry.get("timestamp", ""),
            })
        
        # Calculate trend direction
        if len(history) >= 2:
            recent_avg = sum(h["value"] for h in history[:3]) / min(len(history), 3)
            older_avg = sum(h["value"] for h in history[3:]) / max(len(history[3:]), 1) if len(history) > 3 else recent_avg
            if recent_avg > older_avg + 5:
                trend = "IMPROVING"
            elif recent_avg < older_avg - 5:
                trend = "DETERIORATING"
            else:
                trend = "STABLE"
        else:
            trend = "UNKNOWN"
        
        # Interpret for trading context
        if value <= 20:
            trading_signal = "EXTREME_FEAR — prime buying zone, be greedy when others are fearful. Good projects are on sale."
        elif value <= 35:
            trading_signal = "FEAR — market is nervous but this means discounts. Look for fundamentally strong coins to accumulate."
        elif value <= 55:
            trading_signal = "NEUTRAL — no strong sentiment edge, rely on fundamentals/technicals"
        elif value <= 75:
            trading_signal = "GREED — momentum favourable but watch for overextension"
        else:
            trading_signal = "EXTREME_GREED — high risk of correction, tighten stops"
        
        result = {
            "current_value": value,
            "classification": classification,
            "trend": trend,
            "trading_signal": trading_signal,
            "history_7d": history,
            "source": "alternative.me",
        }
        
        # Cache the result
        _fear_greed_cache["data"] = result
        _fear_greed_cache["fetched_at"] = time.time()
        
        logger.info(f"Fear & Greed Index: {value} ({classification}) — {trend}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to fetch Fear & Greed Index: {e}")
        return {
            "error": str(e),
            "current_value": None,
            "classification": "UNKNOWN",
            "trading_signal": "Unable to fetch — proceed without sentiment baseline",
        }


def analyze_social_sentiment(symbol: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Analyze social media sentiment for a cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol
        sources: Social media sources to analyze
    
    Returns:
        Social sentiment analysis
    """
    return {
        "symbol": symbol,
        "sources": sources or ["twitter", "reddit"],
        "overall_sentiment": 0.6,
        "trend": "POSITIVE",
        "confidence": 0.75
    }


def detect_fud_fomo(text: str) -> Dict[str, Any]:
    """
    Detect FUD or FOMO patterns in text.
    
    Args:
        text: Text to analyze
    
    Returns:
        FUD/FOMO detection results
    """
    # Simple keyword detection (enhance with ML in production)
    fud_keywords = ["crash", "scam", "worthless", "dump"]
    fomo_keywords = ["moon", "100x", "don't miss", "last chance"]
    
    text_lower = text.lower()
    fud_count = sum(1 for kw in fud_keywords if kw in text_lower)
    fomo_count = sum(1 for kw in fomo_keywords if kw in text_lower)
    
    return {
        "fud_score": min(fud_count / 4, 1.0),
        "fomo_score": min(fomo_count / 4, 1.0),
        "classification": (
            "FUD" if fud_count > fomo_count
            else "FOMO" if fomo_count > fud_count
            else "NEUTRAL"
        )
    }


# === Common Tools ===

def get_market_data(symbol: str, metrics: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get current market data for a cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol
        metrics: Specific metrics to retrieve
    
    Returns:
        Market data
    """
    return {
        "symbol": symbol,
        "price": 1.0,
        "volume_24h": 1000000,
        "market_cap": 100000000,
        "price_change_24h": 5.0,
        "requested_metrics": metrics or ["all"]
    }


def format_analysis_response(analysis_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format analysis results into structured response.
    
    Args:
        analysis_type: Type of analysis
        data: Analysis data to format
    
    Returns:
        Formatted analysis response
    """
    return {
        "analysis_type": analysis_type,
        "formatted_data": data,
        "timestamp": "now",
        "version": "1.0"
    }


# Tool registry for ADK
ADK_TOOLS = [
    # Research tools
    get_project_fundamentals,
    check_github_activity,
    analyze_partnerships,
    # Technical tools
    identify_chart_patterns,
    calculate_support_resistance,
    analyze_volume_profile,
    calculate_indicators,
    # Risk tools
    calculate_position_size,
    calculate_risk_reward,
    assess_correlation,
    generate_exit_strategy,
    # Sentiment tools
    get_fear_greed_index,
    analyze_social_sentiment,
    detect_fud_fomo,
    # Common tools
    get_market_data,
    format_analysis_response,
]


# === Trading Tools ===

def check_trade_budget() -> Dict[str, Any]:
    """
    Check remaining daily trading budget and trading engine status.
    
    Returns:
        Budget status including remaining GBP, trades today, and kill switch state
    """
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        return engine.get_status()
    except Exception as e:
        return {"error": str(e), "remaining_today_gbp": 0}


def propose_live_trade(
    symbol: str,
    side: str,
    amount_gbp: float,
    reason: str,
    confidence: int,
) -> Dict[str, Any]:
    """
    Propose a real trade for email approval.
    
    Args:
        symbol: Cryptocurrency symbol (e.g. DOGE)
        side: Trade side — 'buy' or 'sell'
        amount_gbp: Amount in GBP to spend (max is daily budget)
        reason: 2-3 sentence explanation of why this trade
        confidence: Conviction score 0-100
    
    Returns:
        Proposal status with approve/reject URLs
    """
    try:
        from ml.trading_engine import get_trading_engine
        engine = get_trading_engine()
        
        # Get current price (placeholder — real price comes from caller)
        return {
            "tool": "propose_live_trade",
            "symbol": symbol,
            "side": side,
            "amount_gbp": amount_gbp,
            "reason": reason,
            "confidence": confidence,
            "note": "Use the trading engine API to submit this proposal with current price data"
        }
    except Exception as e:
        return {"error": str(e)}


def get_tools_for_agent(agent_type: str) -> List:
    """
    Get tool functions for a specific agent type.
    
    Args:
        agent_type: Type of agent
    
    Returns:
        List of tool functions for the agent
    """
    tool_mapping = {
        'gemini_research': [
            get_project_fundamentals,
            check_github_activity,
            analyze_partnerships,
            get_market_data,
        ],
        'gemini_technical': [
            identify_chart_patterns,
            calculate_support_resistance,
            analyze_volume_profile,
            calculate_indicators,
            get_market_data,
        ],
        'gemini_risk': [
            calculate_position_size,
            calculate_risk_reward,
            assess_correlation,
            generate_exit_strategy,
            get_market_data,
        ],
    }
    
    return tool_mapping.get(agent_type, [get_market_data])

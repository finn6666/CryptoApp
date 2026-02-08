# ML System

## Overview

The ML system has four layers:

1. **Multi-Agent System** -- 4 AI agents via Google ADK reach consensus on each coin
2. **Gem Detection** -- Random Forest + Gradient Boosting classify hidden gems
3. **Reinforcement Learning** -- Q-Learning refines scores from reported trade outcomes
4. **Portfolio Manager** -- Batch analysis with opportunity-weighted allocation

---

## Multi-Agent System

### Agents

| Agent | Model | Weight | Role |
|-------|-------|--------|------|
| Gemini Research | gemini-2.5-flash | 35% | Fundamentals, team, tech, roadmap |
| Gemini Technical | gemini-2.5-flash | 35% | Charts, trends, support/resistance |
| Position Manager | gemini-2.5-flash | 15% | Position sizing, exit strategy |
| Sentiment Analyst | deepseek-chat | 15% | Social sentiment, FUD/FOMO detection |

The orchestrator runs on `gemini-3-flash-preview` and coordinates all agents.

### Consensus

Agents run in parallel (max 3 concurrent). The orchestrator combines scores using weighted voting:

| Consensus | Confidence |
|-----------|------------|
| 90-100% agreement | Very high |
| 70-89% | High |
| 50-69% | Medium |
| <50% | Low -- skip or request more data |

**Recommendations:** BUY (research >70, bullish technicals, consensus >70%), SELL (research <40, bearish, consensus >70%), HOLD (mixed signals or low consensus).

### Conflict Resolution

- Research bullish + Technical bearish: wait for better entry
- Sentiment extreme + Fundamentals strong: contrarian opportunity, lean in
- Position sizing suggests caution: reduce size but enter if thesis holds
- Low consensus: skip trade

### 16 Agent Tools

| Category | Tools |
|----------|-------|
| Research | `get_project_fundamentals`, `check_github_activity`, `analyze_partnerships` |
| Technical | `identify_chart_patterns`, `calculate_support_resistance`, `analyze_volume_profile`, `calculate_indicators` |
| Position | `calculate_position_size`, `calculate_risk_reward`, `assess_correlation`, `generate_exit_strategy` |
| Sentiment | `analyze_social_sentiment`, `detect_fud_fomo` |
| Common | `get_market_data`, `format_analysis_response` |

### Memory

- Short-term: 6 hours (quick reference)
- Long-term: 30 days (trend analysis)

### Caching

| Agent | Cache TTL |
|-------|-----------|
| Research | 2 hours |
| Technical | 30 minutes |
| Position Manager | 1 hour |
| Sentiment | 1 hour |

---

## Gem Detection

**File:** `ml/enhanced_gem_detector.py`

### Models

Random Forest and Gradient Boosting trained on market features:
- Price momentum (24h, 7d, 30d)
- Volume patterns and volume/market-cap ratio
- Market cap rank and category
- Volatility metrics

### Opportunity Labels

| Score | Label |
|-------|-------|
| > 0.7 | Extreme Moonshot |
| > 0.5 | High Upside |
| > 0.3 | Growth Play |
| <= 0.3 | Stable |

Score factors: nano-cap (+0.35), micro-cap (+0.25), low-cap (+0.15), low liquidity (+0.2), low exchange diversity (+0.15), high volatility (+0.1).

### Gem Threshold

`gem_probability > 0.40` classifies a coin as a hidden gem.

### Recommendations

- `> 0.70` -- STRONG BUY (moonshot potential)
- `> 0.55` -- BUY
- `> 0.40` -- HOLD
- Below -- not recommended

---

## Reinforcement Learning

**File:** `ml/simple_rl.py`

Q-Learning (no neural network). Learns from reported trades.

### Flow

1. User reports trade via `/api/rl/report-trade`
2. System calculates profit %
3. Features extracted (momentum, volume, cap category, volatility)
4. Q-table updated
5. Saved to `models/rl_simple_learner.json`

### Parameters

| Parameter | Value |
|-----------|-------|
| Learning rate | 0.1 |
| Discount factor | 0.95 |
| Exploration (epsilon) | 0.1 |

### Reward

| Profit | Reward |
|--------|--------|
| > 10% | +1.0 |
| > 0% | +0.5 |
| > -5% | -0.5 |
| <= -5% | -1.0 |

Time-adjusted: faster gains score higher.

RL contributes up to +10 points to gem score.

---

## Portfolio Manager

**File:** `ml/portfolio_manager.py`

Analyses batches of coins and generates allocation strategy.

### Allocation

- Top 5 buy recommendations get allocation weights
- Weight = `(gem_score / 100) * (confidence / 100)`
- High-upside/moonshot plays get a minor 0.9x adjustment (not heavy penalty)
- Normalised to 100%

### Market Notes (not risk warnings)

- Heavy moonshot exposure: suggests position sizing
- Low confidence: flags limited data
- Selective market: notes coins without strong setups

### Sentiment Labels

Bullish, Cautiously Bullish, Neutral, Cautiously Bearish, Bearish -- based on buy/avoid ratio.

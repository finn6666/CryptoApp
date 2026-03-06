# ML System

## Multi-Agent System (Google ADK + Gemini)

Five agents coordinated by an orchestrator (`gemini-3.0-flash`):

| Agent | Model | Weight | Role |
|-------|-------|--------|------|
| Research | gemini-3-flash-preview | 40% | Fundamentals, team, roadmap |
| Technical | gemini-3-flash-preview | 40% | Charts, indicators, S/R |
| Risk | gemini-3-flash-preview | 20% | Position sizing, exits |
| Sentiment | gemini-3-flash-preview | Integrated | Social sentiment, FUD/FOMO |
| Trading | gemini-3-flash-preview | Decision | Final buy/sell (conviction ≥75%) |

Agents run in parallel (max 3 concurrent). Scores combined via weighted voting.

### 16 Agent Tools

| Category | Tools |
|----------|-------|
| Research | `get_project_fundamentals`, `check_github_activity`, `analyze_partnerships` |
| Technical | `identify_chart_patterns`, `calculate_support_resistance`, `analyze_volume_profile`, `calculate_indicators` |
| Position | `calculate_position_size`, `calculate_risk_reward`, `assess_correlation`, `generate_exit_strategy` |
| Sentiment | `analyze_social_sentiment`, `detect_fud_fomo` |
| Common | `get_market_data`, `format_analysis_response` |

### Cache TTLs

Research 2h, Technical 30m, Position/Sentiment 1h.

### Memory

Short-term: 6h in-memory. Long-term: 30d on disk.

## Gem Detection

`ml/enhanced_gem_detector.py` — Random Forest + Gradient Boosting on market features.

| Score | Label |
|-------|-------|
| > 0.7 | Extreme Moonshot |
| > 0.5 | High Upside |
| > 0.3 | Growth Play |
| ≤ 0.3 | Stable |

Gem threshold: `gem_probability > 0.40`. Recommendations: >0.70 STRONG BUY, >0.55 BUY, >0.40 HOLD.

## Q-Learning RL

`ml/q_learning.py` — tabular Q-learning that learns from trade outcomes.

**State** (discretised): `gem_tier|vol_mcap_ratio|weekly_change|mcap_tier`

**Actions:** buy, skip

**Reward shaping:**
- Base: `tanh(pnl/30)` scaled to [-1, 1]
- Asymmetric: losses weighted 1.5×
- Repeat-loser penalty: progressive for same pattern (−0.1, −0.2, ...)
- Opportunity cost: −0.05 for stagnant holds >1 week

**Integration:**
- Scan loop: adjusts agent conviction by −20 to +15 before threshold check
- Sell automation: records outcomes (realised) + periodic checkpoints (unrealised, dampened)
- ε-greedy: starts 0.3, decays 0.995/episode to min 0.05

Persists to `data/q_table.json` + `data/trade_outcomes.jsonl`.

## ML Pipeline

`ml/training_pipeline.py` — RandomForest trained on price/volume features, exported to ONNX for fast inference. Weekly retrain (Sunday 2AM). ONNX fast-path with sklearn fallback.

## Portfolio Manager

`ml/portfolio_manager.py` — Batch analysis, opportunity-weighted allocation, diversification scoring (Herfindahl index).

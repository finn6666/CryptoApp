# ML System

> For the full agent architecture (orchestrator, sub-agents, tools, weighting), see [architecture/agents.md](architecture/agents.md).

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

`ml/training_pipeline.py` — RandomForest trained on price/volume features, exported to ONNX for fast inference.

- Weekly retrain Sunday 2AM via `MLScheduler`
- ONNX fast-path with sklearn fallback (`ml/onnx_inference.py`)
- Features: price, volume, market cap, percent changes

## Portfolio Manager

`ml/portfolio_manager.py` — Batch analysis, opportunity-weighted allocation, diversification scoring (Herfindahl index).


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

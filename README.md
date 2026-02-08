# CryptoApp

AI-powered low-cap cryptocurrency analysis with multi-agent intelligence and reinforcement learning. Opportunity-first design -- upside potential and gem discovery come before risk aversion.

## Quick Start

```bash
uv sync
cp .env.example .env   # Add CoinMarketCap + Gemini API keys
python app.py           # http://localhost:5001
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Setup](documentation/setup/README.md) | Installation, API keys, config |
| [API Reference](documentation/api/README.md) | All 40 endpoints |
| [ML System](documentation/ml-system/README.md) | Agents, gem detection, RL |
| [Deployment](documentation/deployment/README.md) | Raspberry Pi setup |

## Features

- **Multi-Agent AI** -- 4 agents (Gemini + DeepSeek) reach weighted consensus
- **Gem Detection** -- Random Forest + Gradient Boosting identify hidden gems
- **Reinforcement Learning** -- Q-Learning improves from reported trade outcomes
- **Portfolio Analysis** -- Batch analysis with opportunity-weighted allocation
- **Market Opportunity Bar** -- Real-time opportunity scoring (not risk)
- **Trade Journal** -- Report trades to train the RL system

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask, Python 3.13 |
| AI Agents | Google ADK (gemini-2.5-flash), DeepSeek |
| Orchestrator | gemini-3-flash-preview |
| ML | Random Forest, Gradient Boosting, Q-Learning |
| Data | CoinMarketCap API |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Raspberry Pi 4/5, systemd, nginx |

## Multi-Agent Weights

| Agent | Weight | Role |
|-------|--------|------|
| Gemini Research | 35% | Fundamentals, team, roadmap |
| Gemini Technical | 35% | Charts, trends, levels |
| Position Manager | 15% | Sizing, exits |
| Sentiment Analyst | 15% | Social sentiment, FUD/FOMO |

## Opportunity Labels

| Threshold | Label |
|-----------|-------|
| > 0.7 | Extreme Moonshot |
| > 0.5 | High Upside |
| > 0.3 | Growth Play |
| <= 0.3 | Stable |

## Costs

| Component | Monthly |
|-----------|---------|
| CoinMarketCap | Free tier |
| Google Gemini | ~$2 |
| DeepSeek | ~$0.60 |
| Raspberry Pi power | ~$0.50 |
| **Total** | **~$3/month** |

## API Keys

| Provider | URL |
|----------|-----|
| CoinMarketCap | https://coinmarketcap.com/api/ |
| Google Gemini | https://makersuite.google.com/app/apikey |
| DeepSeek (optional) | https://platform.deepseek.com/ |

## Project Structure

```
CryptoApp/
+-- app.py                  # Flask app (40 routes)
+-- ml/                     # AI & ML
|   +-- agents/official/    # 4 ADK agents + orchestrator
|   +-- tools/adk_tools.py  # 16 agent tools
|   +-- enhanced_gem_detector.py
|   +-- portfolio_manager.py
|   +-- simple_rl.py
+-- src/core/               # Data fetcher, analyzer
+-- src/web/                # Frontend
+-- models/                 # ONNX model, RL state
+-- data/                   # Cache, favorites, agent memory
+-- raspberry_pi/           # Pi monitoring dashboard
+-- documentation/          # Full docs
```

## Disclaimer

Educational purpose only. Not financial advice. Cryptocurrency trading carries significant risk.

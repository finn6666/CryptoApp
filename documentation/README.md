# CryptoApp Documentation

AI-powered low-cap cryptocurrency analysis. Opportunity-first design — the system prioritises upside potential and gem discovery over risk aversion.

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Setup](setup/README.md) | Installation, API keys, configuration |
| [API Reference](api/README.md) | All 40 endpoints with examples |
| [ML System](ml-system/README.md) | Multi-agent AI, gem detection, RL |
| [Deployment](deployment/README.md) | Raspberry Pi systemd + nginx setup |

---

## Quick Start

```bash
uv sync
cp .env.example .env   # Add API keys
python app.py           # http://localhost:5001
```

---

## Architecture

```
Flask App (app.py)
+-- Live Data Fetcher (CoinMarketCap)
+-- ML Engine
|   +-- Agent Orchestrator (Google ADK)
|   |   +-- Gemini Research      (35%)
|   |   +-- Gemini Technical     (35%)
|   |   +-- Gemini Sentiment     (15%)
|   |   +-- Position Manager     (15%)
|   +-- Gem Detector (Random Forest + Gradient Boosting)
|   +-- Simple RL (Q-Learning from trade outcomes)
|   +-- Portfolio Manager
+-- Frontend (vanilla HTML/CSS/JS)
```

## Design Philosophy

- Market Opportunity Bar shows opportunity score, not risk
- Coins labelled by upside: Extreme Moonshot, High Upside, Growth Play, Stable
- High-upside plays get a minor 10% allocation adjustment, not heavy penalties
- Agent weights favour research and technicals (35% each) over position management and sentiment (15% each)

## Costs

| Component | Monthly |
|-----------|---------|
| CoinMarketCap | Free tier |
| Google Gemini (4 agents) | ~$2 |
| DeepSeek (sentiment) | ~$0.60 |
| Raspberry Pi power | ~$0.50 |
| **Total** | **~$3/month** |

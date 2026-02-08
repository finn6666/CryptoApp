# Setup Guide

## Prerequisites

- Python 3.11+ (3.13 recommended)
- [uv](https://github.com/astral-sh/uv) package manager
- API keys: CoinMarketCap (required), Google Gemini (required), DeepSeek (optional)

## Installation

```bash
git clone <repo-url> && cd CryptoApp
uv sync
cp .env.example .env
```

## Environment Variables

```bash
# Required
COINMARKETCAP_API_KEY=your-key
GOOGLE_API_KEY=your-gemini-key

# Optional
DEEPSEEK_API_KEY=your-deepseek-key

# Email reports (optional)
REPORT_EMAIL_FROM=you@gmail.com
REPORT_EMAIL_TO=you@gmail.com
SMTP_PASSWORD=app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

## API Keys

| Provider | URL | Cost |
|----------|-----|------|
| CoinMarketCap | https://coinmarketcap.com/api/ | Free tier (30 calls/day) |
| Google Gemini | https://makersuite.google.com/app/apikey | Free tier (1500 req/day) |
| DeepSeek | https://platform.deepseek.com/ | ~$0.60/month with caching |

## Verify

```bash
python app.py
# => Running on http://0.0.0.0:5001

curl http://localhost:5001/health
curl http://localhost:5001/api/coins
```

## Project Structure

```
CryptoApp/
+-- app.py                  # Flask application (40 routes)
+-- pyproject.toml           # Dependencies
+-- .env                     # API keys (gitignored)
+-- data/                    # Cache, favorites, agent memory
+-- ml/                      # AI & ML systems
|   +-- agents/official/     # 4 ADK agents + orchestrator
|   +-- tools/adk_tools.py   # 16 agent tools
|   +-- enhanced_gem_detector.py
|   +-- portfolio_manager.py
|   +-- simple_rl.py
+-- models/                  # ONNX model, RL learner
+-- src/core/                # Config, analyzer, data fetcher
+-- src/web/                 # Frontend (HTML/CSS/JS)
+-- raspberry_pi/            # Pi monitoring dashboard
```

## Configuration

Key settings in `ml/agent_config.py`:

| Setting | Default |
|---------|---------|
| Agent timeout | 30-45s per agent |
| Orchestrator timeout | 120s |
| Cache TTL | 30m-2h (varies by agent) |
| Monthly budget limit | $5.00 |
| Max parallel agents | 3 |
| Gemini rate limit | 5 req/min |

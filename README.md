# CryptoApp

AI-powered low-cap crypto analysis with multi-agent intelligence (Google ADK + Gemini), gem detection, and live Kraken trading. Runs on a Raspberry Pi for ~£2.50/month.

## Quick Start

```bash
uv sync
cp .env.example .env   # Add API keys
python app.py           # http://localhost:5001
```

## Docs

| Guide | Contents |
|-------|----------|
| [Setup](docs/SETUP.md) | Installation, env vars, API keys |
| [Deployment](docs/DEPLOYMENT.md) | Raspberry Pi systemd + nginx |
| [API](docs/API.md) | All endpoints |
| [ML](docs/ML.md) | Agents, gem detection, RL |
| [Architecture](docs/architecture/overview.md) | Codebase structure, flows |

## Disclaimer

Educational purpose only. Not financial advice.

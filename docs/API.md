# API Reference

Base URL: `http://localhost:5001`

Trading endpoints require `Authorization: Bearer <TRADING_API_KEY>` header.

## Pages

| Route | Description |
|-------|-------------|
| `/` | Main dashboard |
| `/trades` | Trade journal |
| `/health-dashboard` | Server health |

## Coin Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/refresh` | Force data refresh |
| GET | `/api/favorites` | Favorites with AI analysis |
| POST | `/api/favorites/add` | Add `{"symbol": "SOL"}` |
| POST | `/api/favorites/remove` | Remove `{"symbol": "SOL"}` |

## Symbol Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search` | Search coins |
| GET | `/api/symbols/search?query=btc` | Symbol search |
| POST | `/api/symbols/validate` | Validate symbol |
| GET | `/api/symbols` | All tracked symbols |

## Agent Analysis

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/agents/analyze/<symbol>` | No | Multi-agent analysis (Kraken-tradeable only) |
| GET | `/api/agents/scan` | No | Scan all for opportunities |
| GET | `/api/agents/metrics` | No | Agent performance |

## Gem Detection

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/gems/scan` | Batch gem scan (Kraken-tradeable only) |
| GET | `/api/gems/detect/<symbol>` | Single gem detection |
| GET | `/api/gems/top/<count>` | Top N gems (Kraken-tradeable only) |
| GET | `/api/gems/status` | Detector status |
| POST | `/api/gems/train` | Retrain gem models |

## ML

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ml/predict/<symbol>` | ONNX/sklearn prediction |
| GET | `/api/ml/status` | Pipeline status |
| POST | `/api/ml/train` | Retrain models |

## Trading

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/trades/status` | No | Engine status + budget |
| GET | `/api/trades/pending` | No | Pending proposals |
| GET | `/api/trades/history` | No | Executed trades |
| GET/POST | `/api/trades/confirm/<token>` | Token | Email approve/reject |
| POST | `/api/trades/propose` | Yes | Manual trade proposal |
| POST | `/api/trades/agent-trade` | Yes | Agent → proposal (Kraken-tradeable only) |
| POST | `/api/trades/auto-evaluate` | Yes | Full agent → proposal |
| POST | `/api/trades/scan-now` | Yes | On-demand scan |
| GET | `/api/trades/scan-status` | No | Scan loop status |
| POST | `/api/trades/kill-switch` | Yes | Emergency halt |

## Portfolio

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/portfolio/holdings` | Holdings + live P&L |
| GET | `/api/portfolio/sell-signals` | Active sell signals |
| GET | `/api/portfolio/analyze` | Full portfolio analysis |

## Exchange

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/exchanges/status` | Kraken connectivity + tradeable pairs |

## RL & Trade Journal

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rl/report-trade` | Report trade outcome |
| GET | `/api/rl/stats` | RL learning stats |
| GET | `/api/rl/trades` | Trade history |

## Retraining

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/retrain/status` | No | Retrain scheduler status |
| POST | `/api/retrain/trigger` | Yes | Manual retrain |

## Backtesting

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/backtest/run` | Yes | Run backtest |

## Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/api/health` | Detailed component status |
| GET | `/api/metrics` | CPU, memory, disk |

## Market

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/market/conditions` | Opportunity level + score |

## Error Format

```json
{"error": "Description", "details": "Context"}
```

Status codes: 200, 400, 404, 500, 503.

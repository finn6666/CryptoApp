# API Reference

Base URL: `http://localhost:5001`

---

## Coin Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/coins` | All analysed coins (add `?agents=true` for AI analysis) |
| GET | `/api/coins/enhanced` | Enhanced coin data with ML scores |
| POST | `/api/refresh` | Force data refresh |
| GET | `/api/stats` | Market statistics |

### GET `/api/coins`

```bash
curl "http://localhost:5001/api/coins?agents=true&limit=10"
```

```json
{
  "coins": [{
    "symbol": "BTC",
    "price": 50000,
    "gem_score": 85,
    "ml_confidence": 0.82,
    "agent_analysis": {
      "overall_recommendation": "STRONG_BUY",
      "confidence": 0.85,
      "summary": "..."
    }
  }],
  "stats": { "total_coins": 100, "gems_found": 15 }
}
```

---

## Multi-Agent Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents/analyze/<symbol>` | Single coin AI analysis |
| GET | `/api/agents/scan` | Scan all coins for opportunities |
| GET | `/api/agents/metrics` | Agent performance metrics |

### GET `/api/agents/analyze/<symbol>`

```bash
curl http://localhost:5001/api/agents/analyze/ETH
```

Returns consensus from all 4 agents (Research, Technical, Sentiment, Position Manager) with individual scores and a weighted recommendation.

---

## Gem Detection

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/gems/scan` | Scan for hidden gems |
| GET | `/api/gems/detect/<symbol>` | Single coin gem analysis |
| GET | `/api/gems/top/<count>` | Top N gems |
| GET | `/api/gems/status` | Detector status |
| POST | `/api/gems/train` | Retrain gem models |

---

## Portfolio

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/portfolio/analyze` | Portfolio analysis with allocation strategy |

Returns buy/hold/avoid recommendations, opportunity-weighted allocation percentages, and market notes.

---

## Market Conditions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/market/conditions` | Current market opportunity level |

```json
{
  "opportunity_level": "GOOD",
  "opportunity_score": 68,
  "opportunity_percentage": 68,
  "message": "Good Opportunity - Favorable conditions",
  "indicators": {
    "total_coins": 200,
    "avg_price_change_24h": 3.2,
    "nano_caps": 45,
    "micro_caps": 80,
    "low_caps": 50
  }
}
```

Opportunity levels: EXCELLENT (75+), GOOD (60+), MODERATE (40+), LIMITED (25+), LOW (<25).

---

## Favorites

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/favorites` | List favorites |
| POST | `/api/favorites/add` | Add coin `{"symbol": "SOL"}` |
| POST | `/api/favorites/remove` | Remove coin `{"symbol": "SOL"}` |

---

## Symbol Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search` | Search coins |
| GET | `/api/symbols/search` | Symbol search `?query=btc` |
| POST | `/api/symbols/validate` | Validate symbol exists |
| POST | `/api/symbols/add` | Add symbol to tracking |
| GET | `/api/symbols` | All tracked symbols |
| GET | `/api/symbols/status` | Symbol tracking status |

---

## Trade Journal & RL

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rl/report-trade` | Report trade outcome |
| GET | `/api/rl/stats` | RL learning statistics |
| GET | `/api/rl/trades` | Trade history |

### POST `/api/rl/report-trade`

```json
{
  "symbol": "BTC",
  "entry_price": 45000,
  "exit_price": 50000,
  "days_held": 7,
  "notes": "Bought on technical breakout"
}
```

---

## ML Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ml/status` | ML pipeline status |
| GET | `/api/ml/predict/<symbol>` | Single prediction |
| POST | `/api/ml/train` | Retrain ML models |
| POST | `/api/ml/initialize` | Initialize ML pipeline |
| GET | `/api/gemini/quota` | Gemini API quota status |
| GET | `/api/debug/ml` | ML debug info |
| GET | `/api/debug/coins` | Debug coin data |

---

## Health & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/api/health` | Detailed health with component status |
| GET | `/api/metrics` | System metrics (CPU, memory, disk) |
| GET | `/api/status/idle` | Idle status for auto-shutdown |

---

## Pages

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main dashboard |
| GET | `/legacy` | Legacy view |
| GET | `/trades` | Trade journal page |

---

## Error Format

```json
{
  "error": "Description",
  "details": "Additional context"
}
```

Status codes: 200 (success), 400 (bad request), 404 (not found), 500 (server error), 503 (component not ready).

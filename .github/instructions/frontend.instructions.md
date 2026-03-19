---
description: Vanilla JS + Jinja2 frontend — templates, JS modules, auth, and API endpoints used.
applyTo: "src/web/**"
---

# Frontend

Vanilla JS + Jinja2 templates. No build step, no framework. Three pages: dashboard, trades, health.

## Pages

| Template | JS | Purpose |
|----------|----|---------|
| `src/web/templates/index.html` | `dashboard.js`, `api-service.js`, `portfolio.js` | Main dashboard |
| `src/web/templates/trades.html` | Inline `<script>` (~700 lines) | Trade journal + live trading |
| `src/web/templates/health.html` | `health.js` | Server health, auto-refreshes 10s |

## JS Modules

| File | Purpose |
|------|---------|
| `src/web/static/js/dashboard.js` | Overview cards, auto-refresh |
| `src/web/static/js/api-service.js` | API calls, data refresh, background agent loading |
| `src/web/static/js/portfolio.js` | Portfolio analysis (AI-powered) |
| `src/web/static/js/health.js` | Health page rendering |
| `src/web/static/js/utils.js` | `formatPrice`, `formatPercent`, `timeAgo` |
| `src/web/static/js/ui-components.js` | Shared UI helpers |
| `src/web/static/css/main.css` | Single stylesheet, dark theme, CSS variables |

## Authentication

```js
getApiKey()     // prompts user, stores in sessionStorage (cleared on tab close)
authHeaders()   // returns { 'Authorization': 'Bearer <key>', 'Content-Type': 'application/json' }
```

All trading POST endpoints require the Bearer token.

## Key API Endpoints

```
GET  /api/favorites              — coin list with optional agent analysis
GET  /api/market/conditions      — market sentiment
GET  /api/ml/status              — ML pipeline status
GET  /api/portfolio/holdings     — current holdings + P&L
GET  /api/portfolio/analyze      — AI portfolio analysis
GET  /api/trades/status          — trading engine status
GET  /api/trades/pending         — pending proposals
POST /api/trades/approve/{id}    — approve proposal
POST /api/trades/reject/{id}     — reject proposal
POST /api/trades/kill-switch     — toggle kill switch
GET  /api/trades/scan-status     — scan loop status
POST /api/trades/scan-now        — trigger manual scan
GET  /api/trades/confirm/{token} — HMAC token approve/reject
```

## Trades Page (inline JS)

Key functions in `trades.html`:
- `loadTradingStatus()`, `loadPendingProposals()`, `approveTrade()`, `rejectTrade()`
- `toggleKillSwitch()`, `loadScanStatus()`, `triggerScan()`
- `loadPortfolio()`, `loadPerformance()`, `loadActivityLog()`

## Gotchas

- `trades.html` inline JS is ~700 lines — keep it there, don't break it into modules
- No build step: edit files directly, refresh browser
- `sessionStorage` for API key means prompting on each new tab/session

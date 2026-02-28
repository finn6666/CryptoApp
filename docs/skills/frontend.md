# Skill: Frontend

## Overview

Vanilla JavaScript + Jinja2 templates + single CSS file. No build step, no framework. Three pages: dashboard, trades, health.

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/web/templates/index.html` | ~148 | Main dashboard |
| `src/web/templates/trades.html` | ~1202 | Trade journal + live trading (most complex) |
| `src/web/templates/health.html` | ~167 | Server health dashboard |
| `src/web/static/js/dashboard.js` | ~248 | Overview cards, auto-refresh |
| `src/web/static/js/api-service.js` | ~308 | API calls, data refresh, background agent loading |
| `src/web/static/js/portfolio.js` | ~175 | Portfolio analysis (AI-powered) |
| `src/web/static/js/health.js` | ~170 | Health page rendering |
| `src/web/static/js/favorites.js` | — | Favorites management |
| `src/web/static/js/symbol-search.js` | — | Symbol search/add |
| `src/web/static/js/ui-components.js` | — | Shared UI helpers |
| `src/web/static/js/utils.js` | — | `formatPrice`, `formatPercent`, `timeAgo` etc. |
| `src/web/static/js/main.js` | — | Entry point, init |
| `src/web/static/css/main.css` | — | Single stylesheet, dark theme, CSS variables |

## Pages

### Dashboard (`index.html`)
- Overview cards: Portfolio, Trading Engine, Scanner, Market Monitor, Exchanges
- Favorites table with agent analysis
- Symbol search
- Portfolio analysis (AI toggle)
- Loads 9 JS modules via `<script>` tags

### Trades (`trades.html`)
The most complex page (~1200 lines). **All JS is inline** (~700 lines of `<script>`).

Sections:
- **Stats grid:** Total trades, win rate, budget remaining, trades today, winning/losing
- **Live Trading:** Status indicator, kill switch, pending proposals (approve/reject), trade log
- **Automated Scanning:** Status badge, next scan countdown, coins analysed, proposals made, "Scan Now" button
- **Portfolio Holdings:** Value, unrealised/realised P&L, fees, holdings list
- **Performance Summary:** Win rate, wins/losses, avg trade, coins traded
- **Closed Positions**
- **Activity Log** (audit trail)
- **Manual Trade Form:** Symbol, days held, entry/exit price → trains RL

Key inline functions: `loadTradingStatus()`, `loadPendingProposals()`, `approveTrade()`, `rejectTrade()`, `toggleKillSwitch()`, `loadScanStatus()`, `triggerScan()`, `loadPortfolio()`, `loadPerformance()`, `loadActivityLog()`

### Health (`health.html`)
- Auto-refreshes every **10 seconds**
- Status banner (online/error)
- Cards: Components, Trading Engine, Scan Loop, System Resources (CPU/Memory/Disk bars), Cache, Server Info

## Authentication

- `getApiKey()` — prompts user, stores in `sessionStorage` (cleared on tab close)
- `authHeaders()` — returns `{ 'Authorization': 'Bearer <key>', 'Content-Type': 'application/json' }`
- All trading POST endpoints require the Bearer token

## API Endpoints Used

```
GET  /api/favorites              — coin list with optional agent analysis
GET  /api/market/conditions      — market sentiment
GET  /api/ml/status              — ML pipeline status
POST /api/ml/train               — trigger model retrain
POST /api/refresh                — force data refresh
GET  /api/portfolio/holdings     — current holdings + P&L
GET  /api/portfolio/history      — trade history
GET  /api/portfolio/analyze      — AI portfolio analysis
GET  /api/trades/status          — trading engine status
GET  /api/trades/pending         — pending proposals
GET  /api/trades/history         — executed trades
POST /api/trades/approve/{id}    — approve proposal
POST /api/trades/reject/{id}     — reject proposal
POST /api/trades/kill-switch     — toggle kill switch
GET  /api/trades/scan-status     — scan loop status
POST /api/trades/scan-now        — trigger manual scan
POST /api/trades/auto-evaluate   — propose trade via API
GET  /api/trades/confirm/{token} — HMAC token approve/reject
GET  /api/monitor/status         — market monitor status
GET  /api/exchanges/status       — exchange connectivity
GET  /api/health                 — server health
```

## Styling

- **Dark theme** throughout using CSS variables: `--card-bg`, `--border`, `--accent-primary`, `--text-primary`, `--text-secondary`, `--success`, `--error`
- Inter font family
- CSS versioning: `?v=20260208b` on `<link>` tags
- Inline styles used extensively alongside `main.css`

## Key JS Patterns

- `dashboard.js` loads 5 overview cards in parallel via `Promise.allSettled()`
- `api-service.js` does background agent analyses: fetch favorites without agents first (fast), then refetch with agents (slow) and update cards in-place
- `forceRefresh()` calls `/api/refresh` POST which triggers server-side data reload
- Polling: health page every 10s, trades page scan status every 60s

## Gotchas

- `trades.html` has **all JS inline** — not in separate files like the dashboard
- Auth uses `sessionStorage` — user must re-enter API key on every new tab
- No build step, no minification, no bundling
- CSS cache versioning is manual (update `?v=` query string)
- Health polling is hardcoded 10s — no backoff on errors
- Static files served by nginx in production (7d cache) — clear cache after CSS/JS updates

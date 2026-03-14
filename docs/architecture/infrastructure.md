# Infrastructure

Raspberry Pi 4 stack — systemd, nginx, Gunicorn, Redis, Flask.

## Request Flow

```
Client → nginx (:80/:443)
           │
           ├─ /static/*  → served directly from src/web/static/ (7-day cache)
           │
           └─ /api/* and /  → Gunicorn @ 127.0.0.1:5001
                                  │
                                  └─ Flask app (wsgi:app)
                                       ├─ routes/coins.py
                                       ├─ routes/ml_routes.py
                                       ├─ routes/trading.py
                                       ├─ routes/health.py
                                       └─ routes/symbols.py
```

## Gunicorn

| Setting | Value | Reason |
|---------|-------|--------|
| Workers | 1 | Pi memory constraint (1G cap) |
| Worker class | `gthread` | Mixed I/O workload |
| Threads | 2 | Light concurrency within the single worker |
| Timeout | 120s | ADK orchestrator can take 2 min |
| `preload_app` | False | Preserves background daemon threads (scan scheduler, market monitor) |
| Max requests | 500 + jitter 50 | Guard against memory leaks |

## Systemd

Unit file: `deploy/cryptoapp.service`

```ini
[Service]
User=pi
WorkingDirectory=/home/pi/CryptoApp
EnvironmentFile=/home/pi/CryptoApp/.env
ExecStart=uv run gunicorn -c gunicorn.conf.py wsgi:app
Restart=always
MemoryMax=1G
MemoryHigh=768M
```

## Redis (Optional Cache)

`services/redis_cache.py` provides a Redis-backed fallback for the analysis cache. Falls back silently to in-memory if Redis is unavailable.

Cache hierarchy (for agent analysis results):
1. In-memory dict (`state.analysis_cache`) — fastest
2. Redis (`services/redis_cache.py`) — survives Gunicorn restarts
3. Disk (`data/agent_analysis_cache.json`) — survives Pi reboots
4. Miss → fresh ADK analysis

TTL: 12 hours (`CACHE_EXPIRY_SECONDS = 43200`).

## Flask App

Entry point: `wsgi.py` → `app.py:create_app()`.

Blueprints registered in `app.py`:
- `coins_bp` — `/api/coins`, `/api/favorites`
- `ml_bp` — `/api/ml/*`, `/api/agents/*`, `/api/gems/*`, `/api/portfolio/*`
- `trading_bp` — `/api/trades/*`
- `health_bp` — `/api/health`, `/api/metrics`
- `symbols_bp` — `/api/symbols`

## Remote Access

See [../DEPLOYMENT.md](../DEPLOYMENT.md) for Tailscale SSH setup.

## Resource Constraints

| Resource | Limit | Implication |
|----------|-------|-------------|
| RAM | 1G (systemd `MemoryMax`) | OOM-kills if exceeded |
| Workers | 1 | No true concurrent requests |
| Threads | 2 | Helps I/O-bound routes (API polling) |
| CPU | 4-core ARM | Network-bound, not CPU-bound |
| Storage | SD card | Keep JSON state files small |

## Startup Sequence

`init_all()` in `services/app_state.py` runs once on first import:

1. `initialize_exchange_manager()` — loads exchange pairs
2. `initialize_trading_engine()` — loads proposals/budgets from disk
3. `initialize_official_agents()` — imports ADK agents
4. `initialize_scan_loop()` — creates scan loop (doesn't start it)
5. `initialize_market_monitor()` — creates monitor (doesn't start it)
6. `initialize_sell_automation()` — loads sell automation state

The scan scheduler is started separately when the app is ready.

## Gotchas

- `preload_app=False` is critical — enabling it would fork the process before the scan scheduler thread starts, causing it to be silently lost
- `MemoryMax=1G` will OOM-kill with no warning — avoid large in-memory data structures
- nginx `proxy_read_timeout 180s` gives 60s headroom above Gunicorn's 120s timeout
- Static file paths in nginx are hardcoded to `/home/pi/CryptoApp` — edit for non-default installs

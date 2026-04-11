# Infrastructure

Raspberry Pi 4 stack -- systemd, nginx, Gunicorn, Flask.

For deployment commands, SSH setup, and systemd config, see [deployment.instructions.md](../../.github/instructions/deployment.instructions.md).

## Request Flow

```
Client --> nginx (:80/:443)
              |
              |-- /static/*  --> served directly (cached, skip Gunicorn)
              |
              +-- everything else --> Gunicorn @ localhost:5001
                                          |
                                          +-- Flask app (wsgi:app)
                                               |-- routes/coins.py
                                               |-- routes/ml_routes.py
                                               |-- routes/trading.py
                                               |-- routes/health.py
                                               +-- routes/symbols.py
```

## Why These Choices

**1 Gunicorn worker, gthread class**: The Pi has 4GB RAM with a 1G systemd cap. Multiple workers would each load the full app (ML models, agent state, exchange connections). A single worker with threads handles the mixed I/O workload (API polling, exchange calls) without duplicating memory. `preload_app=False` is critical -- the scan scheduler and market monitor run as daemon threads that would be lost if the app forked after preloading.

**nginx in front**: Serves static files directly (7d cache), handles SSL termination, adds security headers, and provides a longer read timeout (180s) than Gunicorn's worker timeout (120s) to give agent analysis headroom.

**No database**: JSON files in `data/` with atomic writes. The dataset is small enough that a database would add operational complexity (backups, migrations, connection pooling) without meaningful benefit on a single-user Pi.

**Optional Redis**: A Redis-backed analysis cache can survive Gunicorn restarts, but the system falls back silently to in-memory + disk caching when Redis is unavailable. Most deployments run without it.

## Startup Sequence

`init_all()` in `services/app_state.py` runs once on first import:

1. Exchange manager -- loads exchange pair cache
2. Trading engine -- restores proposals and budgets from disk
3. ADK agents -- imports Gemini agent definitions
4. Scan loop -- creates scheduler (starts when app is ready)
5. Market monitor -- creates monitor threads
6. Sell automation -- loads peak prices and recheck state

## Resource Constraints

The Pi's constraints shape most design decisions:

- **1G RAM cap** (systemd `MemoryMax`) -- OOM-kills with no warning if exceeded. This is why there's one worker, bounded caches, and periodic state pruning.
- **SD card storage** -- JSON state files are kept small. Trade history is capped at 500 entries in memory.
- **4-core ARM CPU** -- workload is network-bound (exchange APIs, Gemini calls), not CPU-bound.
- **Agent analysis latency** -- a full debate can take 60-120s, which is why both Gunicorn and nginx timeouts are set high.

## Security

- Bearer token auth on all trading POST endpoints
- HMAC-signed approval links (1h expiry) for email-based trade approval
- systemd hardening (NoNewPrivileges, ProtectSystem=strict, ReadWritePaths restricted)
- nginx security headers (HSTS, CSP, X-Frame-Options)
- Weekly automated security checks via systemd timer (CVE scan, secret scan, SSH config)
- Pre-commit hook blocks commits containing likely secrets

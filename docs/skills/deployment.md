# Skill: Deployment

## Overview

CryptoApp runs on a Raspberry Pi 4 (4GB RAM) behind nginx, managed by systemd, served by Gunicorn.

## Stack

```
Internet → nginx (:80/:443) → Gunicorn (:5001) → Flask (wsgi:app)
                                    ↑
                              systemd manages
```

## Files

| File | Purpose |
|------|---------|
| `deploy/cryptoapp.service` | systemd unit file |
| `deploy/nginx-cryptoapp.conf` | nginx reverse proxy config |
| `deploy/setup-ssl-rhel.sh` | Let's Encrypt SSL setup (RHEL/CentOS) |
| `gunicorn.conf.py` | Pi-optimised Gunicorn config |
| `wsgi.py` | WSGI entry point (`wsgi:app`) |

## systemd Service

```ini
[Service]
User=pi
WorkingDirectory=/home/pi/CryptoApp
EnvironmentFile=/home/pi/CryptoApp/.env
ExecStart=uv run gunicorn -c gunicorn.conf.py wsgi:app
Restart=always
RestartSec=10
MemoryMax=1G
MemoryHigh=768M
```

**Common commands:**
```bash
ssh pi "sudo systemctl restart cryptoapp"
ssh pi "sudo systemctl status cryptoapp"
ssh pi "sudo journalctl -u cryptoapp -f"       # live logs
ssh pi "sudo journalctl -u cryptoapp --since '1h ago'"
```

## Gunicorn Config

| Setting | Value | Reason |
|---------|-------|--------|
| Bind | `127.0.0.1:5001` | Localhost only — nginx fronts it |
| Workers | `1` | Pi memory constraint |
| Worker class | `gthread` | Mixed I/O workload |
| Threads | `2` | Light concurrency |
| Timeout | `120s` | Agent orchestrator can take 2 min |
| Graceful timeout | `30s` | Clean shutdown |
| Max requests | `500` + jitter `50` | Memory leak guard (auto-restart) |
| preload_app | `False` | Preserves scan scheduler thread |

## nginx Config

- Listens port 80, `server_name _`
- Static files: served directly from `/home/pi/CryptoApp/src/web/static/` with 7-day cache
- Proxy: passes to `127.0.0.1:5001` with HTTP/1.1 + WebSocket support
- `proxy_read_timeout 180s` — headroom for agent analysis
- `client_max_body_size 10MB`

## SSL Setup

Script: `deploy/setup-ssl-rhel.sh` (RHEL/CentOS only — uses `dnf`)

```bash
./setup-ssl-rhel.sh yourdomain.com your-email@example.com
```

- Installs certbot, obtains standalone certificate
- Generates nginx HTTPS config with TLS 1.2/1.3
- Sets HSTS (1 year), security headers
- Configures SELinux (`httpd_can_network_connect`)
- Opens firewall ports (http + https)
- Sets up auto-renewal timer

## Deployment Workflow

```bash
# On dev machine:
git push origin dev

# On Pi:
ssh pi
cd /home/pi/CryptoApp
git pull
sudo systemctl restart cryptoapp
sudo journalctl -u cryptoapp -f   # verify startup
```

## Resource Constraints (Pi 4, 4GB)

| Resource | Limit | Notes |
|----------|-------|-------|
| RAM | 1G (systemd cap) | MemoryHigh=768M triggers pressure warning |
| Workers | 1 | No concurrent request handling (2 threads only) |
| CPU | 4 cores ARM | Agent analysis is network-bound, not CPU-bound |
| Disk | SD card | JSON state files are small |

## Gotchas

- Service file paths assume `/home/pi/CryptoApp` — edit for other users/paths
- `MemoryMax=1G` will **OOM-kill** the process if exceeded
- Only 1 Gunicorn worker = no true concurrent requests (2 threads help for I/O)
- `preload_app` is **disabled** — scan scheduler thread relies on this
- SSL script is RHEL-specific — won't work on Debian/Ubuntu without modifications
- Agent analysis can take up to 120s — both Gunicorn and nginx timeouts account for this
- Static file cache: 7d (plain nginx) vs 30d (SSL config) — intentional difference

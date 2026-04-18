---
description: Systemd, nginx, Gunicorn config, Pi optimisations, remote access, and deployment workflow.
applyTo: "deploy/**,gunicorn.conf.py,wsgi.py"
---

# Deployment

Raspberry Pi 4 (4GB RAM), systemd-managed, nginx reverse proxy, Gunicorn WSGI server.

```
Internet → nginx (:80/:443) → Gunicorn (:5001) → Flask (wsgi:app)
                                    ↑
                              systemd manages
```

## Key Files

| File | Purpose |
|------|---------|
| `deploy/cryptoapp.service` | systemd unit file |
| `deploy/nginx-cryptoapp.conf` | nginx reverse proxy |
| `gunicorn.conf.py` | Pi-optimised Gunicorn config |
| `wsgi.py` | WSGI entry point (`wsgi:app`) |

## Gunicorn Settings

| Setting | Value | Reason |
|---------|-------|--------|
| Bind | `127.0.0.1:5001` | Localhost only — nginx fronts it |
| Workers | `1` | Pi memory constraint |
| Worker class | `gthread` | Mixed I/O workload |
| Threads | `2` | Light concurrency |
| Timeout | `120s` | ADK orchestrator can take 2 min |
| `preload_app` | `False` | Preserves scan scheduler thread |

## systemd Commands

```bash
sudo systemctl restart cryptoapp
sudo systemctl status cryptoapp
sudo journalctl -u cryptoapp -f          # live logs
sudo journalctl -u cryptoapp --since '1h ago'
```

## SSH Access

**On local network (no Tailscale needed):** SSH key auth works directly — no password required because the public key is in `~/.ssh/authorized_keys` on the Pi. Port 22 is firewalled to local network + Tailscale range only (not public internet).

```bash
ssh finnbryant@<pi-local-ip>
```

**From outside home network (Tailscale):** Tailscale provides a stable private IP that works from any network.

```bash
# One-time Pi setup:
curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up

# SSH from anywhere:
ssh finnbryant@<tailscale-ip>
```

Find Tailscale IP: `tailscale ip -4` on the Pi, or https://login.tailscale.com/admin/machines.

## Weekly Security Checks

Automated checks run via systemd timer (CVE scan, .env permissions, nginx headers, secret scan):

```bash
# Setup (one-time on Pi):
sudo cp deploy/cryptoapp-security.service /etc/systemd/system/
sudo cp deploy/cryptoapp-security.timer   /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now cryptoapp-security.timer

# Run manually:
bash deploy/security-check.sh
# Logs: data/security_audit.log
```

## Deployment Workflow

```bash
# On Pi:
cd ~/CryptoApp && git pull && uv sync
sudo systemctl restart cryptoapp
sudo journalctl -u cryptoapp -f   # verify startup
```

## Resource Constraints

| Resource | Limit |
|----------|-------|
| RAM | 1G systemd cap (`MemoryMax=1G`) |
| Workers | 1 (2 threads only) |
| CPU | 4-core ARM, network-bound workload |

## Gotchas

- `MemoryMax=1G` will OOM-kill the process if exceeded
- `preload_app` disabled — scan scheduler thread relies on this
- Agent analysis takes up to 120s — both Gunicorn and nginx timeouts account for this
- Service file paths default to `/home/pi/CryptoApp` — edit for other users
- SSL script (`setup-ssl-rhel.sh`) is RHEL-specific; use `certbot --nginx` on Pi OS instead

## Current work

- ~~Scan more per day without high cost~~ — Tiered scanning implemented: gem gate (≥6.0) → quick LLM screen (1 call) → full multi-agent (6 calls). Default bumped to 25 coins/scan, ~60-70% fewer Gemini calls.
- ~~Do all security fixes~~ — Done: auth on all sensitive GET + POST endpoints (14 trading routes, 3 coins/ML/symbols routes), rate limits on ML/refresh endpoints, atomic writes in portfolio tracker + trading engine + sell automation, CSP header added to nginx.
- ~~Fix enhanced gem detector~~ — Done: KeyError bug fixed (added 3 missing features), circular label bug fixed (cap-rank now requires activity signal), nano-cap boost reduced (35% → 10%), all 23 bare `except:` fixed.
- ~~Remote control ideas~~ — Leave for later
- Enable HTTPS on Pi — nginx config is templated and ready, just needs a domain + cert:
  ```bash
  # 1. Point a domain (or subdomain) at your Pi's public IP
  # 2. Install certbot
  sudo apt install -y certbot python3-certbot-nginx
  # 3. Obtain cert and auto-patch nginx config
  sudo certbot --nginx -d your-domain.com
  # 4. Test renewal
  sudo certbot renew --dry-run
  ```
  Then in `deploy/nginx-cryptoapp.conf`: uncomment the HTTP→HTTPS redirect block, the `listen 443 ssl` lines, and the `Strict-Transport-Security` header. Copy the updated config and reload nginx.

## Future work

### Crypto Twitter sentiment

Add direct Twitter/X API integration for real-time crypto trader sentiment. Needs API key + rate-limited endpoint.

### Trade sizing / allocation tuning

Track per-coin allocation performance. Tune the trading agent's budget allocation rules (currently 55-70% conviction = 40-60% budget). The Q-learning agent adjusts conviction but allocation % could be smarter.

### Phase 1 — More CEXes via ccxt

Add KuCoin + Gate.io to `EXCHANGE_PRIORITY`. The `ExchangeManager` already supports multi-exchange routing — just need API keys and a small tweak for KuCoin's passphrase field. Goes from ~700 Kraken pairs to ~5,000+ tradeable coins with zero architecture changes.

### Weekly Report (revisit in future)
## Security setup (one-time, run on Pi)

```bash
# Install pre-commit secret scanner
bash deploy/install-hooks.sh

# Install systemd weekly security check timer
sudo cp deploy/cryptoapp-security.service /etc/systemd/system/
sudo cp deploy/cryptoapp-security.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cryptoapp-security.timer

# Verify timer is scheduled
systemctl list-timers cryptoapp-security.timer

# Run manually any time
sudo systemctl start cryptoapp-security.service
# or: bash deploy/security-check.sh
```

## Cur work
- Just looked at activity log on dashboard, can you explain this concerning the Q learning "skip STG — Q-learning recommends SKIP for state low|low|neutral|mid (Q_buy=0.000, Q_skip=0.000, visits=0, ε=0.158)"

## Future Work

### Multi-agent teams

Run multiple agent teams with different strategies (e.g., conservative vs aggressive) analyzing the same coins. Teams vote or compete — highest-conviction consensus triggers trades. Needs: team-scoped orchestrator configs, per-team Q-learning state, ensemble voting logic in trading engine.

### Trade sizing / allocation tuning

Track per-coin allocation performance. Tune the trading agent's budget allocation rules (currently 55-70% conviction = 40-60% budget). The Q-learning agent adjusts conviction but allocation % could be smarter.

### Phase 1 — More CEXes via ccxt

Add KuCoin + Gate.io to `EXCHANGE_PRIORITY`. The `ExchangeManager` already supports multi-exchange routing — just need API keys and a small tweak for KuCoin's passphrase field. Goes from ~700 Kraken pairs to ~5,000+ tradeable coins with zero architecture changes.

**Steps:**

1. **KuCoin passphrase support** — in `ml/exchange_manager.py`, add an `elif exchange_id == "kucoin"` branch in `_get_exchange_config()` that reads `KUCOIN_API_KEY`, `KUCOIN_API_SECRET`, and `KUCOIN_PASSPHRASE` from env and returns `{"apiKey": ..., "secret": ..., "password": ...}`.

2. **Create API keys** — on KuCoin (kucoin.com) and Gate.io (gate.io), generate read + trade API keys. Gate.io works with the existing generic fallback, no code change needed.

3. **Add to `.env`:**
   ```
   KUCOIN_API_KEY=...
   KUCOIN_API_SECRET=...
   KUCOIN_PASSPHRASE=...
   GATEIO_API_KEY=...
   GATEIO_API_SECRET=...
   EXCHANGE_PRIORITY=kraken,kucoin,gateio
   ```

4. **Restart** — `sudo systemctl restart cryptoapp` — logs should show `✅ kucoin connected — N markets` and `✅ gateio connected — N markets`.

5. **Verify routing** — check `/api/exchanges/status` in the app, confirm pair counts look right (~700 Kraken, ~1,000+ KuCoin, ~3,000+ Gate.io).

### Weekly Report (revisit in future)

## Current work

- Remove favorites functionality as im not uisng it
- checked closed positions are picking up correct data
- I dont need to see so far back on the Activity log and trade log on the dashboard

## Future work

### Crypto Twitter sentiment

Add direct Twitter/X API integration for real-time crypto trader sentiment. Needs API key + rate-limited endpoint.

### Trade sizing / allocation tuning

Track per-coin allocation performance. Tune the trading agent's budget allocation rules (currently 55-70% conviction = 40-60% budget). The Q-learning agent adjusts conviction but allocation % could be smarter.

### Phase 1 — More CEXes via ccxt

Add KuCoin + Gate.io to `EXCHANGE_PRIORITY`. The `ExchangeManager` already supports multi-exchange routing — just need API keys and a small tweak for KuCoin's passphrase field. Goes from ~700 Kraken pairs to ~5,000+ tradeable coins with zero architecture changes.

### Phase 2 — Jupiter / Solana DEX for micro-cap & meme coins

Build a `DexManager` class using Jupiter's REST API + `solders` for signing. Gas is essentially free (~£0.001/swap). Gives access to 1,500+ liquid tokens (2M+ total on Solana). Integrate as CEX-first → DEX-fallback routing in `TradingEngine`.

### Phase 3 — Unified CEX + DEX routing

Seamless routing: check CEXes first for best price/availability, fall back to Jupiter DEX for tokens not listed on any CEX.

### Weekly Report (revisit in future)
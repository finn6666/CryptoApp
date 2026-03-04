## Current work


## Future work

### Phase 1 — More CEXes via ccxt (effort: ~2 hours)

Add KuCoin + Gate.io to `EXCHANGE_PRIORITY`. The `ExchangeManager` already supports multi-exchange routing — just need API keys and a small tweak for KuCoin's passphrase field. Goes from ~700 Kraken pairs to ~5,000+ tradeable coins with zero architecture changes.

### Phase 2 — Jupiter / Solana DEX for micro-cap & meme coins (effort: 1–2 days)

Build a `DexManager` class using Jupiter's REST API + `solders` for signing. Gas is essentially free (~£0.001/swap). Gives access to 1,500+ liquid tokens (2M+ total on Solana). Integrate as CEX-first → DEX-fallback routing in `TradingEngine`.

### Phase 3 — Unified CEX + DEX routing (effort: ~0.5 day)

Seamless routing: check CEXes first for best price/availability, fall back to Jupiter DEX for tokens not listed on any CEX.

### Phase 4 (optional) — 1inch on BSC (effort: ~1 day)

REST API + `web3.py` for BSC-specific tokens. Gas ~£0.03–0.05/swap. Only worth it if there are BSC-exclusive tokens not available on Solana.

### ❌ Ruled out — Uniswap on Ethereum mainnet

Gas fees (£3–15 per swap) exceed the entire £3 daily budget. Not viable unless moved to L2s (Arbitrum/Base) where micro-cap selection is limited anyway.

### Weekly Report


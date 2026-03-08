## Current work

### Security Hardening (priority)

- [ ] Replace `str(e)` error leaks with generic messages (~20 endpoints return raw exception strings)
- [ ] Fix `innerHTML` XSS in frontend JS (use `textContent` or DOMPurify)
- [ ] Add HTTPS redirect in nginx config
- [ ] Set `SECRET_KEY` in production env (random fallback doesn't persist across restarts)

### Going through proj findings | questions
- Do we need pycache/ directory and stuff in it?, think theres another gitignore etc
- Look at deploy dir as i dont think the rhel file is needed anymore? Also seems theres a bit of duplication with docs/setup.md and the deploy dir?
- Look through docs/skills as this was only to help claude in the chat section but not sure it's actually doing that? Same with docs/claude.md
- On the research agent, we have the 3 points to do research on, just want to make sure that it'll look at coins with no usability but massive current hype that can result in huge profits just on that alone - After note, think this may be more sentiment agent?
- On the risk agent, assesing point 2. gets the agent to think about allocating a £1000 portfolio, if you think that's optimal then leave it but it just caught my eye 
- On sentiment agent, any chance we can look at crypto twitter traders for help on sentiment?
- On the trading agent, quite a lot of mention on the importance of holding coins which I do like, but maybe just reduce the redundancy
- For both buying and selling coins, I want approval only for over £50 at the  moment
- Are we still using the ml/advanced gem detector anymore?
- Remove the ml/weekly report and any reference. Very old implementation, something I'll do in the future
- Are we actuall using /services/redis cache?
- Think we have a few readmes so just make sure were having redundant docs
- Are we still using main.py?
-
-
## Future work

### Phase 1 — More CEXes via ccxt (effort: ~2 hours)

Add KuCoin + Gate.io to `EXCHANGE_PRIORITY`. The `ExchangeManager` already supports multi-exchange routing — just need API keys and a small tweak for KuCoin's passphrase field. Goes from ~700 Kraken pairs to ~5,000+ tradeable coins with zero architecture changes.

### Phase 2 — Jupiter / Solana DEX for micro-cap & meme coins (effort: 1–2 days)

Build a `DexManager` class using Jupiter's REST API + `solders` for signing. Gas is essentially free (~£0.001/swap). Gives access to 1,500+ liquid tokens (2M+ total on Solana). Integrate as CEX-first → DEX-fallback routing in `TradingEngine`.

### Phase 3 — Unified CEX + DEX routing (effort: ~0.5 day)

Seamless routing: check CEXes first for best price/availability, fall back to Jupiter DEX for tokens not listed on any CEX.


### Weekly Report
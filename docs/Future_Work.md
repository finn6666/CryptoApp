## Future Work

### Backtesting → Q-table pre-seeding
Run `ml/backtesting.py` over historical data and feed outcomes into `ql.record_outcome()` to give the RL agent a prior before the first live trade. Also useful for validating exit threshold changes (stop-loss %, trailing stop, tier levels) before going live.

---

### Self-custody / wallet consolidation (longer term)
Auto-withdraw bought coins to a hardware wallet after purchase. Portfolio tracking already works exchange-agnostic. Needs per-exchange withdrawal API calls + minimum threshold to avoid fee bleed.

---

### Debate orchestrator — tuning
- Monitor referee verdict quality on real trades vs the old 5-agent chain
- Tune bear/bull prompt aggression
- Pass recent closed-trade outcomes into the referee prompt for regime-aware calibration

---

### Multi-exchange routing — gaps
- Silent fallback to priority order when best-price fetch fails — add alerting when degraded
- Pair cache (6h TTL) misses new listings until expiry — consider shorter TTL or event-driven invalidation
- No spread comparison — picks best mid-price, not accounting for bid/ask spread width

---

### Monetisation
**1. Telegram signal channel** — bot posts scan signals to a private paid channel on each scan. Minimal build: `ml/telegram_notifier.py` + patch `scan_loop.py`. Fastest route to revenue validation.

**2. Packaged software** — Docker image users run on their own Pi/VPS. First-run setup wizard, built-in Telegram bot, licence key validation, full trading dashboard. Sell via Gumroad (~£120–200 one-time).

**Exchange affiliate programs** — Kraken, KuCoin, Bitget, MEXC all pay 20–40% of referred trading fees. Add referral links to the Telegram welcome message and setup wizard — zero extra build work.

---

### Multi-agent strategy teams (longer term)
Multiple agent teams with different risk profiles vote on the same coins. Highest-conviction consensus triggers trades. Consider CrewAI — maps naturally to the debate orchestrator pattern and supports Gemini via LiteLLM.

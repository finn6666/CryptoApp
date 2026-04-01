## Activate on Pi

### Swing / dual-strategy trading

Implemented — just needs env vars set on the Pi. Add to `~/CryptoApp/.env`:

```
SWING_TRADE_ENABLED=true   # enable swing exits for swing-tagged positions
SWING_BULL_REGIME=true     # tag all bull-market (BTC +10% 7d) trades as swing

# Swing exit thresholds (defaults — adjust to taste):
SWING_MIN_HOLD_HOURS=8         # vs 72h for accumulate
SWING_TRAILING_STOP_PCT=15.0   # vs 45% for accumulate
SWING_TIER1_PCT=25.0           # first profit target vs 75%
SWING_TIER1_FRACTION=0.5       # sell 50% at tier 1 vs 33%
```

Long-term holds (`trade_mode=accumulate`) are unaffected — only new positions entered during a bull regime get swing exits. Regime is determined by BTC 7-day % change: >+10% = bull, <-10% = bear, otherwise neutral.

---

## Future Work

### Self-custody / wallet consolidation

Auto-withdraw bought coins to a hardware wallet (e.g. Ledger) after purchase to reduce exchange counterparty risk. Portfolio tracking via `data/portfolio.json` already works exchange-agnostic. Needs per-exchange withdrawal API calls + minimum threshold to avoid fee bleed.

---

### Future: Bitget exchange support

Bitget has a large altcoin selection and would complement Gate.io/KuCoin/MEXC for small-cap discovery. The ExchangeManager architecture already supports it — only needs:
- `_get_exchange_config()` case for `bitget` (requires passphrase like KuCoin)
- `.env.example` entry for `BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_PASSPHRASE`
- Add `bitget` to `EXCHANGE_PRIORITY` in `.env`

Blocked on: obtaining Bitget API keys.

---

### Future: Weekly report email

---

### Future: Multi-agent teams

Multiple teams with different strategies (conservative vs aggressive) vote on the same coins. Highest-conviction consensus triggers trades. Needs: team-scoped orchestrator configs, per-team Q-learning state, ensemble voting logic.

**Consider CrewAI** for implementation — natural `Crew` + `Agent` + `Task` model maps directly to the existing orchestrator/specialist pattern. Supports role delegation, sequential or parallel task execution, shared memory between agents, and works with Gemini via the LiteLLM backend. Much cleaner than wiring ADK multi-team logic manually.

---

### Future: OpenViking for agent memory

[OpenViking](https://github.com/volcengine/OpenViking) — open-source tiered context database for agents (L0 abstract / L1 overview / L2 full content). Better than flat prompt stuffing for long-running agents with large memory.

Not worth it now: `use_memory=False`, Pi RAM limit, needs Go + C++ build, extra embedding API. Revisit if agent memory is re-enabled and past trade context starts overflowing prompts.

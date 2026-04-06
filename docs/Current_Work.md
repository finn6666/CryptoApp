## To Do

### Differentiation strategy
Deepen learning and trade quality to stand out from competing services. Key moat areas to develop:
- Q-learning feedback loop — close the loop between trade outcomes and future buy/skip decisions
- Debate architecture tuning — referee verdict quality, bear/bull prompt calibration
- Regime-aware thresholds — smarter conviction floors in bear vs bull markets
- Tiered profit-taking — already live, but refine based on real trade data

### Short-term trade performance
Improve the system's ability to capitalise on shorter-term moves, not just medium-to-long accumulation:
- Swing trade mode (`SWING_TRADE_ENABLED`) already exists — evaluate and tune its thresholds against real trade data
- Tighter entry timing — debate orchestrator currently has no momentum/entry-timing signal, only fundamentals
- Consider a dedicated short-term agent or prompt variant that weights recent price action and volume more heavily
- Market monitor 30-min opportunity scan could feed swing proposals separately from the main scan loop

---

## In Progress



---

## Recently Completed

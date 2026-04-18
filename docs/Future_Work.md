## Future Work

### Crypto Venture Capital System
Build CryptoApp into an automated VC-style investment platform for crypto. The debate orchestrator already evaluates coins like a due-diligence committee — extend it to operate as a systematic fund.

**Core thesis:** AI agents evaluate early-stage tokens the way a VC fund evaluates startups — team, traction, market size, tokenomics, competitive moat — then allocate capital with portfolio-level risk management.

**Near-term steps:**
- Thesis-driven screening: add project fundamentals (team, GitHub activity, TVL, partnerships) alongside price data in the scan pipeline
- Portfolio construction: position sizing based on conviction tiers, sector diversification limits, max drawdown constraints
- Fund-style reporting: weekly NAV, attribution by sector/thesis, benchmark vs BTC/ETH
- LP dashboard: read-only view for external investors showing performance, allocations, and risk metrics

**Revenue model:**
- Management fee (2%) + performance fee (20%) on external capital — standard VC/hedge fund terms
- Telegram signal channel for retail subscribers (lower commitment entry point)
- Exchange affiliate revenue (Kraken, KuCoin, Bitget, MEXC — 20-40% of referred fees)

---

### Debate orchestrator — tuning
- Monitor referee verdict quality on real trades vs the old 5-agent chain
- Tune bear/bull prompt aggression

---

### Multi-exchange routing — remaining gaps
- Pair cache (6h TTL) misses new listings until expiry — consider shorter TTL or event-driven invalidation
- No spread comparison — picks best mid-price, not accounting for bid/ask spread width

---

### Self-custody / wallet consolidation
Auto-withdraw bought coins to a hardware wallet after purchase. Portfolio tracking already works exchange-agnostic. Needs per-exchange withdrawal API calls + minimum threshold to avoid fee bleed.

---

### Multi-agent strategy teams
Multiple agent teams with different risk profiles vote on the same coins. Highest-conviction consensus triggers trades. Consider CrewAI — maps naturally to the debate orchestrator pattern and supports Gemini via LiteLLM.

---

### Technical analysis enhancements (from nateemma/strategies research)
Ideas from the [nateemma/strategies](https://github.com/nateemma/strategies) freqtrade repo — adapted for CryptoApp's agent-based architecture.

**Anomaly detection for buy signals:**
Train on "normal" market data, flag anomalies as potential entry points. Uses ensemble of detectors (Isolation Forest, LOF, PCA, One-Class SVM, KMeans, Elliptic Envelope, Gaussian Mixture). Could supplement or replace the heuristic quick_screen. Filter anomaly signals with MFI (buy if MFI < 50, sell if MFI > 50).

**Wavelet-based price prediction (DWT):**
Discrete Wavelet Transform models expected price gain, buys when predicted gain exceeds a rolling threshold. Uses rolling-window training to avoid lookahead bias. Could provide a secondary quantitative signal alongside the debate orchestrator.

**Adaptive exit targets:**
Rolling profit/loss thresholds based on standard deviations — more dynamic than fixed-percentage exits. Formula: `target_profit = rolling_mean(profit) + n * rolling_std(profit)`. Currently sell_automation uses fixed tiers — could be enhanced with adaptive thresholds per holding.

**PCA dimensionality reduction:**
Compress indicator features via PCA before classification. The training_pipeline.py RandomForest could benefit — reduce overfitting and improve generalisation on the Pi's limited compute.

**Bollinger Band squeeze detection:**
When Bollinger Band width squeezes inside a Keltner Channel, it signals compressed volatility and potential breakout. Useful as a guard metric for entry timing.

**Guard metrics for entry/exit filtering:**
Use RMI (Relative Momentum Index), Fisher RSI, and Williams %R as guard conditions to filter false signals. Scale to [-1, +1] range where -ve = oversold, +ve = overbought.

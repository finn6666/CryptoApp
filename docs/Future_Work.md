## Future Work

### Crypto Venture Capital System
Automated VC-style investment platform. AI agents evaluate early-stage tokens like a due-diligence committee — team, traction, tokenomics, competitive moat — then allocate capital with portfolio-level risk management.

- **Screening:** thesis-driven fundamentals (team, GitHub, TVL, partnerships) alongside price data
- **Portfolio construction:** conviction-tier sizing, sector diversification limits, max drawdown constraints
- **Reporting:** weekly NAV, sector attribution, benchmark vs BTC/ETH; LP dashboard for external investors
- **Revenue:** 2/20 fee structure on external capital, Telegram signal channel, exchange affiliate revenue


---

### Advanced ML strategies
Ideas from [nateemma/strategies](https://github.com/nateemma/strategies) and [FinRL](https://github.com/AI4Finance-Foundation/FinRL):

- **DRL trade timing (FinRL):** PPO/SAC/A2C agents for buy/sell/hold decisions — upgrade Q-learning to proper DRL. FinRL's ensemble approach (multiple DRL agents vote) maps to the existing debate pattern
- **Turbulence index (FinRL):** market turbulence detector triggers defensive mode — complements the existing regime detection
- **Anomaly detection entries:** ensemble (IsoForest, LOF, PCA, SVM) trained on "normal" data; anomalies = buy signals filtered by MFI
- **Wavelet price prediction (DWT):** models expected gain, buys when prediction exceeds rolling threshold
- **Adaptive exit targets:** `rolling_mean + n * rolling_std` instead of fixed percentage tiers in sell_automation
- **PCA feature compression:** reduce overfitting in training_pipeline RandomForest on Pi's limited compute
- **Guard metrics:** RMI, Fisher RSI, BB squeeze as entry/exit filters

---

### Longer-term
- **Self-custody:** auto-withdraw to hardware wallet post-purchase; per-exchange withdrawal APIs + minimum threshold
- **Multi-agent strategy teams:** multiple risk-profile agent teams vote on same coins; CrewAI + Gemini via LiteLLM

## Current work

- On the RL insights, it says learnt from 122 trades but its definately not done that many

- Look at Enhanced gem detector as I dont think it's doing any of this eg advanced alpha features. Maybe state what it's doing so we can have a disucussion on it's future use and neccesitiy. Belive the agents are doing what it's set out to do anyway, seems a waste of around 1000 lines of code
Enhanced ML model specifically designed to identify hidden gems
    
    Key Innovation: Uses advanced alpha features + AI sentiment analysis to detect
    opportunities others miss by analyzing:
    - Market psychology patterns (fear/greed contrarian signals)
    - Timing anomalies (market inefficiency windows)  
    - Cross-asset relationships (network effects)
    - Smart money vs crowd behavior patterns
    - Asymmetric risk-reward opportunities
    - AI-powered sentiment analysis (Gemini agent integration)
    """
- What is the scheduler.py doing?
- Do i need the quick screen as trades can't actually be made as a result of it?
- How does the back testing and q-learning work? Do they work together in tandem?
- Think this feature is pointless if its the case 'Falls back to the local GradientBoosting gem detector if Gemini's down.' - This was in the architecture file, don't think gemeni would ever be down
- Don't think redis cache.py is being used, may as well remove?
- Have ._pytest cache.py - Is this needed, eg another git.ignore etc??
- Would like maybe a new dir for architecture, just so I can fully see and explain how everything works in isolation and together.
- Are we using core/crypto analyzer.py ??
- I see there is now skills and instructions & rules functionality, ensure my skills and instructions can be used in this new functionality 
- Sell logic is broken, trying to sell wrong balance amount of coin causing errors  
- SSH issues while away from pi?
- Look at Singleton at the bottom of sell-automation.py
- Only want the stop loss to kick in if the coin is actually dead
- Don't like the idea of the min hold period (72 hours?), only reasoning for this initially was to ensure we buy & hold when the market is red, but when this is not the case, I want the agent to have the freedom to make shorter term trades if they are profitable 
- Think the general exit triggers need to be relooked at eg profit targets and trailing stop. Maybe have a discussion on there usefulness, seems more suited to convential stock markets rather than crypto

## Future work

### Multi-agent teams

Run multiple agent teams with different strategies (e.g., conservative vs aggressive) analyzing the same coins. Teams vote or compete — highest-conviction consensus triggers trades. Needs: team-scoped orchestrator configs, per-team Q-learning state, ensemble voting logic in trading engine.

### Multi-user support

Allow others to access the dashboard (read-only viewers, shared portfolio managers, or independent traders with their own portfolios). Needs: user auth system (Flask-Login or similar), user database (SQLite/Postgres), per-user portfolio files, role-based route access. Current blockers: all state is global singletons, single JSON portfolio file, single exchange account, single API key.
Like the idea of sharing a portfolio manager, users can choose different customized agents that i have created/tested

### Crypto Twitter sentiment

Add direct Twitter/X API integration for real-time crypto trader sentiment. Needs API key + rate-limited endpoint.

### Trade sizing / allocation tuning

Track per-coin allocation performance. Tune the trading agent's budget allocation rules (currently 55-70% conviction = 40-60% budget). The Q-learning agent adjusts conviction but allocation % could be smarter.

### Phase 1 — More CEXes via ccxt

Add KuCoin + Gate.io to `EXCHANGE_PRIORITY`. The `ExchangeManager` already supports multi-exchange routing — just need API keys and a small tweak for KuCoin's passphrase field. Goes from ~700 Kraken pairs to ~5,000+ tradeable coins with zero architecture changes.

### Weekly Report (revisit in future)
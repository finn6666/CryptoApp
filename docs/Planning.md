
## Current To Do

### Action needed — resume live trading
1. SSH to Pi: `grep TRADING_API_KEY ~/CryptoApp/.env` — copy the key
2. Open dashboard in browser → F12 → Console → run:
   `localStorage.setItem('tradingApiKey', 'PASTE_KEY_HERE')`
3. Click **Resume** on the dashboard to re-enable trading

### Action needed — Pi security hardening (do on Pi)
1. Restrict SSH firewall: `sudo ufw delete allow 22 && sudo ufw allow from 192.168.0.0/16 to any port 22 && sudo ufw allow from 100.64.0.0/10 to any port 22 && sudo ufw reload`
2. Disable SSH password auth: `sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && sudo systemctl restart ssh`
3. Set up weekly security check timer: `sudo cp ~/CryptoApp/deploy/cryptoapp-security.service /etc/systemd/system/ && sudo cp ~/CryptoApp/deploy/cryptoapp-security.timer /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now cryptoapp-security.timer`

## Future Work

---

### Self-custody / wallet consolidation

Auto-withdraw bought coins to a hardware wallet (e.g. Ledger) after purchase to reduce exchange counterparty risk. Portfolio tracking via `data/portfolio.json` already works exchange-agnostic. Needs per-exchange withdrawal API calls + minimum threshold to avoid fee bleed.

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

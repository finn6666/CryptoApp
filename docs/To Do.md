## Questions


## Future Work

### Dashboard layout rework — Finviz-style

Agreed design (March 2026):

**Layout:**
```
┌─ Header + nav ──────────────────────────────────────────────────┐
│  Budget │ Portfolio P&L │ Scanner status │ Monitor status        │  ← compact strip
├──────────────────────────────────────┬──────────────────────────┤
│  COIN HEATMAP                        │  💼 Holdings              │
│                                      │  ⚡ Live Trading          │
│  Tile size  = gem score (weighted)   │  📊 Scanner              │
│  Tile colour = gem score green→red   │  🧠 RL Insights           │
│  Tile text  = symbol, price, Δ24h,   │                           │
│               gem score              │                           │
│  Click tile → inline AI analysis     │                           │
└──────────────────────────────────────┴──────────────────────────┘
```

**Details:**
- Heatmap replaces the coin card grid; tiles sized proportionally by gem score (higher score = bigger tile), equal minimum size floor
- Sidebar replaces the stacked full-width section cards for holdings, trading, scanner, RL Insights
- Compact status strip replaces the 5 overview cards (saves vertical space)
- RL Insights visible on dashboard (sidebar panel), not buried on Trades page
- Sections that don't need always-visible presence (Activity Log, Monthly Review, Closed Positions) stay on Trades page
- Sparkline SVG per holding tile still desirable once heatmap is in place

**Still needed from previous rework list:**
- Switch dashboard polling to SSE — reduces Pi idle CPU vs. 30s setInterval
- Debounce/batch JS API calls on page load
- Add `/api/dashboard-summary` endpoint (one call for all status data) — becomes more important with sidebar layout
- Enable gzip compression in nginx for JSON API responses
- Add pagination / virtual scroll to trades log
- Cache-bust CSS/JS via git short SHA instead of hardcoded date strings

---

### Self-custody / single wallet consolidation

Currently coins bought on KuCoin/MEXC sit on those exchanges. Consider auto-withdrawing to a single hardware wallet (e.g. Ledger) after buy. App already tracks holdings via `data/portfolio.json` so P&L and sell decisions don't depend on which exchange holds the coin — withdrawal would just reduce exchange counterparty risk. Needs: per-exchange withdrawal API calls, minimum withdrawal threshold to avoid fee bleed.


### Weekly Report (revisit in future)

### Multi-agent teams (revisit in future)

Run multiple agent teams with different strategies (e.g., conservative vs aggressive) analyzing the same coins. Teams vote or compete — highest-conviction consensus triggers trades. Needs: team-scoped orchestrator configs, per-team Q-learning state, ensemble voting logic in trading engine.

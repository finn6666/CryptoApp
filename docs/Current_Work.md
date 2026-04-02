## To Do



---

## In Progress



---

## Recently Completed

- **Aggressive trading improvements** (2026-04-02): tighter exits, conviction-tiered sizing, swing mode tagging
  - `sell_automation.py`: early stagnation fast-path at 7d uses `price_change_7d` only (no Gemini call)
  - `trading_engine.py`: conviction-tiered sizing (80%+ conviction → up to 80% daily budget); post-sell recycle scan (capped by 1h cooldown + `GEMINI_DAILY_BUDGET_GBP`)
  - `scan_loop.py`: regime-aware quick-screen threshold — bear market raises bar to 78% (reduces agent API calls)
  - `market_monitor.py`: momentum/quick-scan triggers tagged as `play_type=swing` for tighter exits
  - Mechanical stop-loss / profit-tier sells now auto-execute without email approval delay
- Swing trading enabled — added env vars to `.env` (`SWING_TRADE_ENABLED`, `SWING_BULL_REGIME`, thresholds)
- Fixed deprecated `gemini-2.0-flash-lite` → `gemini-2.0-flash` in all 7 agent files
- Fixed stale GBP/USDT FX rate — USD proxy fallback added to `exchange_manager._get_fx_rate()`
- Gmail SMTP fix pending — `SMTP_PASSWORD` needs updating to a Google App Password in `.env`

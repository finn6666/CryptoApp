## To Do

### Bitget integration — manual steps pending

- [ ] Wait for Bitget cooling-off period to end
- [ ] Generate Bitget API keys at https://www.bitget.com/account/newApiManagement
      (Permissions needed: Trade, Read)
- [ ] Add to `.env` on the Pi:
      ```
      BITGET_API_KEY=<your key>
      BITGET_API_SECRET=<your secret>
      BITGET_PASSPHRASE=<your passphrase>
      EXCHANGE_PRIORITY=kraken,bitget
      ```
- [ ] Deploy: `ssh pi "cd ~/CryptoApp && git pull && sudo systemctl restart cryptoapp"`
- [ ] Verify Bitget appears connected in `/api/trades/status`


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

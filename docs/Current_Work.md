# Current Work

Active tasks and in-progress changes. Clear entries when merged/deployed.

---

## In Progress

_Nothing active right now._

---

## Recently Completed

- Swing trading enabled — added env vars to `.env` (`SWING_TRADE_ENABLED`, `SWING_BULL_REGIME`, thresholds)
- Fixed deprecated `gemini-2.0-flash-lite` → `gemini-2.0-flash` in all 7 agent files
- Fixed stale GBP/USDT FX rate — USD proxy fallback added to `exchange_manager._get_fx_rate()`
- Gmail SMTP fix pending — `SMTP_PASSWORD` needs updating to a Google App Password in `.env`

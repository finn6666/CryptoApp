## To Do

### Bitget integration — manual steps pending

- [ ] Remove `SELL_PROFIT_TARGET_PCT` from `.env` on the Pi (nuclear exit trigger removed — no longer read)
- [ ] Add `SCAN_QUICK_SCREEN_BEAR=72` to `.env` on the Pi (lower bear market quick-screen from 78% → 72% to let more coins reach full analysis)
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


### Api costs now only ~10p per day, ensure they come under £1 but look to increase them

---

## In Progress



---

## Recently Completed

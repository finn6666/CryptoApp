# Todo

## Manual — Bitget integration

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
- [ ] Deploy and verify: `ssh pi "cd ~/CryptoApp && git pull && sudo systemctl restart cryptoapp"`
- [ ] Check health endpoint confirms Bitget is connected: `curl -s https://<your-domain>/api/trades/status`

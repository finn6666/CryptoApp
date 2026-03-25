---
name: deploy
description: Deploy latest code to the Raspberry Pi and restart the service
disable-model-invocation: false
---

Deploy the current `dev` or `main` branch to the Raspberry Pi production server.

Steps:
1. Run `git status` to confirm there are no uncommitted changes that should be deployed first
2. Run `git log --oneline -5` to show what will be deployed
3. SSH to the Pi and pull the latest code: `ssh pi "cd ~/CryptoApp && git pull origin $ARGUMENTS"`
   - If no branch argument given, default to `main`
4. Restart the service: `ssh pi "sudo systemctl restart cryptoapp"`
5. Wait 3 seconds then check service health: `ssh pi "sudo systemctl status cryptoapp --no-pager -l"` and `curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/`
6. Report the result — confirm the service is active and the health check returns 200

If the service fails to start, show the last 30 lines of logs: `ssh pi "sudo journalctl -u cryptoapp -n 30 --no-pager"`

# SSH into VM

## 🔄 Update & Restart App
```bash
# Navigate and update in one command
cd ~/crypto-app && git pull && sudo pkill gunicorn && nohup gunicorn --bind 0.0.0.0:8080 app:app &
```

## ✅ Verify Deployment
```bash
# Check if app is running
ps aux | grep gunicorn
```

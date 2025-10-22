# 🚀 Quick Azure VM Deploy

Deploy your Crypto App to Azure VM in 5 minutes.

---

## 1. Setup VM

SSH into your Azure VM:
```bash
# Install stuff
sudo apt update && sudo apt install python3 python3-pip python3-venv git -y

# Create folder
mkdir ~/crypto-app && cd ~/crypto-app
```

## 2. Deploy App

```bash
# Get your code
git clone https://github.com/your-username/CryptoApp.git .

# Setup Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt gunicorn
```

## 3. Run It

```bash
# Test first
python app.py

# Run in background
nohup gunicorn --bind 0.0.0.0:8080 app:app &
```

## 4. Access

Open: `http://your-vm-ip:8080`

---

## Quick Commands

```bash
# Update app
cd ~/crypto-app && git pull && sudo pkill gunicorn && nohup gunicorn --bind 0.0.0.0:8080 app:app &

# Check if running
ps aux | grep gunicorn

# Stop app
sudo pkill gunicorn
```

## Fix Common Issues

**Can't access?** 
- Azure Portal → VM → Networking → Add port 8080

**App crashes?**
```bash
# See what's wrong
python app.py
```

**Permission error?**
```bash
chmod +x ~/crypto-app/*
```

---

**Done!** Your crypto app is live at `http://your-vm-ip:8080`
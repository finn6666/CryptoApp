# 🔵 Azure VM Deployment Guide

Simple deployment guide for your Crypto Investment Analyzer on Azure Virtual Machine.

## Prerequisites

- Azure VM running Ubuntu/Linux
- SSH access to your VM
- Git repository with your code
- Python 3.9+ on the VM

---

## Initial VM Setup

SSH into your Azure VM and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install python3 python3-pip python3-venv git -y

# Create app directory
sudo mkdir -p /var/www/crypto-analyzer
sudo chown $USER:$USER /var/www/crypto-analyzer
```

## Deploy Application

```bash
# Clone your repository
cd /var/www/crypto-analyzer
git clone https://github.com/your-username/your-repo.git .

# Setup Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Test the app
python3 web_app.py
```

## Production Setup

### 1. Install Gunicorn
```bash
pip install gunicorn
```

### 2. Create systemd service
```bash
sudo nano /etc/systemd/system/crypto-analyzer.service
```

Add this content:
```ini
[Unit]
Description=Crypto Analyzer Flask App
After=network.target

[Service]
User=azureuser
Group=www-data
WorkingDirectory=/var/www/crypto-analyzer
Environment="PATH=/var/www/crypto-analyzer/.venv/bin"
ExecStart=/var/www/crypto-analyzer/.venv/bin/gunicorn --bind 0.0.0.0:8080 web_app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### 3. Start the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable crypto-analyzer
sudo systemctl start crypto-analyzer
```

## Easy Updates

Create an update script:
```bash
nano /var/www/crypto-analyzer/update.sh
```

Script content:
```bash
#!/bin/bash
cd /var/www/crypto-analyzer
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crypto-analyzer
echo "✅ App updated!"
```

Make it executable:
```bash
chmod +x update.sh
```

## Access Your App

- **URL**: `http://your-vm-ip:8080`
- **Status**: `sudo systemctl status crypto-analyzer`
- **Logs**: `sudo journalctl -u crypto-analyzer -f`
- **Update**: `./update.sh`

## Troubleshooting

**App won't start:**
```bash
sudo journalctl -u crypto-analyzer -f
```

**Permission issues:**
```bash
sudo chown -R azureuser:www-data /var/www/crypto-analyzer
```

**Port blocked:**
- Azure Portal → VM → Networking → Add inbound rule (port 8080)

---

That's it! Simple VM deployment with no container overhead.
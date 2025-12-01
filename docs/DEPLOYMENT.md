# 🚀 CryptoApp Deployment Guide

Complete guide for deploying and updating CryptoApp on Azure VM (Ubuntu/Debian or RHEL).

## 📋 Quick Navigation

| What do you need? | Go to |
|-------------------|-------|
| **Update code on existing VM** | [→ Quick Update](#-quick-update-most-common) |
| **Setup SSL/HTTPS (RHEL)** | [→ SSL Setup](../deploy/SSL-DEPLOYMENT-RHEL.md) 🔒 |
| **First time setup - Ubuntu/Debian** | [→ Ubuntu Setup](#-ubuntu--debian-setup) |
| **First time setup - RHEL** | [→ RHEL Setup](#-rhel-setup) |
| **Service commands** | [→ Service Management](#-service-management) |
| **Something broken?** | [→ Troubleshooting](#-troubleshooting) |

---

## ⚡ Quick Update (Most Common)

**Already have VM setup? Just need to update code?**

```bash
# 1. SSH into your VM
ssh your-username@your-vm-ip

# 2. Navigate to project and pull changes
cd ~/CryptoApp
git pull origin main

# 3. Update dependencies (if pyproject.toml changed)
# Ubuntu/Debian:
source .venv/bin/activate && pip install -e .
# RHEL:
uv sync

# 4. Restart service
sudo systemctl restart cryptoapp

# 5. Check it worked
sudo systemctl status cryptoapp
sudo journalctl -u cryptoapp -n 20
```

**Done!** Your app is now running the latest code.

---

## 🐧 Ubuntu / Debian Setup

### 1. Azure VM Setup
```bash
# SSH into your Azure VM
ssh your-username@your-vm-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip git nginx -y
```

### 2. Clone Repository
```bash
cd ~
git clone https://github.com/finn6666/CryptoApp.git
cd CryptoApp
```

### 3. Setup Python Environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### 4. Configure Environment
```bash
nano .env
```

Add these variables:
```bash
# Required
FLASK_SECRET_KEY=your-random-secret-key-here

# Optional - DeepSeek AI
DEEPSEEK_API_KEY=your-deepseek-api-key

# Optional - Email Reports
REPORT_EMAIL_FROM=your-email@gmail.com
REPORT_EMAIL_TO=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password

# Optional - CoinMarketCap
COINMARKETCAP_API_KEY=your-api-key
```

Save with `Ctrl+O`, `Enter`, `Ctrl+X`

### 5. Setup Systemd Service
```bash
# Copy service file
sudo cp deploy/cryptoapp.service /etc/systemd/system/

# Edit with your username
sudo nano /etc/systemd/system/cryptoapp.service
```

Update these lines:
```ini
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/CryptoApp
ExecStart=/home/YOUR_USERNAME/CryptoApp/.venv/bin/gunicorn
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cryptoapp
sudo systemctl start cryptoapp
sudo systemctl status cryptoapp
```

### 6. Setup Nginx (Optional)
```bash
# Copy nginx config
sudo cp deploy/nginx-cryptoapp.conf /etc/nginx/sites-available/cryptoapp

# Edit to set your VM IP
sudo nano /etc/nginx/sites-available/cryptoapp

# Enable site
sudo ln -s /etc/nginx/sites-available/cryptoapp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Configure Firewall
```bash
# Allow HTTP/HTTPS
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### 8. Azure Network Security Group (CRITICAL!)
In Azure Portal:
1. Go to your VM → Networking
2. Add inbound port rules for:
   - Port 80 (HTTP)
   - Port 443 (HTTPS)

**Without this, browser access will hang!**

---

## 🎩 RHEL Setup

### 1. Install Dependencies
```bash
# Update system
sudo dnf update -y

# Install packages
sudo dnf install -y python3 nginx git

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

### 2. Clone and Setup
```bash
cd ~
git clone https://github.com/finn6666/CryptoApp.git
cd CryptoApp
uv sync
```

### 3. Configure Environment
```bash
cat > .env << EOF
FLASK_SECRET_KEY=your-random-secret-key-here
COINMARKETCAP_API_KEY=your-api-key-here
DEEPSEEK_API_KEY=your-deepseek-api-key
REPORT_EMAIL_FROM=your-email@gmail.com
REPORT_EMAIL_TO=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
EOF
```

### 4. Setup Systemd Service
```bash
sudo tee /etc/systemd/system/cryptoapp.service > /dev/null << 'EOF'
[Unit]
Description=CryptoApp Flask (Gunicorn)
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/CryptoApp
Environment=PATH=/home/YOUR_USERNAME/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/bin/bash -c 'cd /home/YOUR_USERNAME/CryptoApp && /home/YOUR_USERNAME/.local/bin/uv run gunicorn -c gunicorn.conf.py wsgi:app'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Replace YOUR_USERNAME with actual username
sudo nano /etc/systemd/system/cryptoapp.service
```

### 5. Setup Nginx
```bash
# Copy config
sudo cp deploy/nginx-cryptoapp.conf /etc/nginx/conf.d/cryptoapp.conf

# Edit to set your VM IP
sudo nano /etc/nginx/conf.d/cryptoapp.conf
```

### 6. Configure Firewall & SELinux
```bash
# Firewall
sudo firewall-cmd --permanent --add-service={http,https}
sudo firewall-cmd --reload

# SELinux (allow nginx to connect to backend)
sudo setsebool -P httpd_can_network_connect 1
```

### 7. Start Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cryptoapp nginx
sudo systemctl status cryptoapp
```

### 8. Verify
```bash
curl http://localhost/health
```

---

## 🎛️ Service Management

### Check Status
```bash
sudo systemctl status cryptoapp
```

### View Logs
```bash
# Live logs (Ctrl+C to exit)
sudo journalctl -u cryptoapp -f

# Last 50 lines
sudo journalctl -u cryptoapp -n 50

# Logs from today
sudo journalctl -u cryptoapp --since today

# With timestamps
sudo journalctl -u cryptoapp -n 100 --no-pager
```

### Restart/Stop/Start
```bash
sudo systemctl restart cryptoapp   # Restart service
sudo systemctl stop cryptoapp      # Stop service
sudo systemctl start cryptoapp     # Start service
sudo systemctl reload cryptoapp    # Reload config
```

### Multiple Services
```bash
# Restart both app and nginx
sudo systemctl restart cryptoapp nginx

# Check both statuses
sudo systemctl status cryptoapp nginx
```

---

## 🔧 Troubleshooting

### Service Won't Start

**Check logs first:**
```bash
sudo journalctl -u cryptoapp -n 50 --no-pager
```

**Common Issue #1: Port in use**
```bash
# Find what's using port 5001
sudo lsof -i :5001

# Kill the process
sudo kill -9 <PID>

# Restart
sudo systemctl restart cryptoapp
```

**Common Issue #2: Permission errors**
```bash
# Fix ownership
sudo chown -R $USER:$USER ~/CryptoApp

# Make gunicorn executable
chmod +x ~/CryptoApp/.venv/bin/gunicorn
```

**Common Issue #3: Missing .env file**
```bash
# Check if .env exists
ls -la ~/CryptoApp/.env

# If missing, create it
nano ~/CryptoApp/.env
```

### Browser Access Hangs (but curl works)

**This is Azure NSG issue!**

1. Go to Azure Portal
2. Your VM → Networking
3. Add inbound security rules:
   - Port 80 (HTTP)
   - Port 443 (HTTPS)
4. Wait 1-2 minutes for rules to apply

Verify nginx logs show your IP:
```bash
sudo tail -f /var/log/nginx/access.log
```

### 502 Bad Gateway

**RHEL SELinux blocking nginx:**
```bash
sudo setsebool -P httpd_can_network_connect 1
sudo systemctl restart nginx
```

**Backend not running:**
```bash
sudo systemctl status cryptoapp
sudo systemctl start cryptoapp
```

### Git Pull Conflicts

**If you have local changes:**
```bash
# Save local changes
git stash

# Pull updates
git pull origin main

# Reapply local changes
git stash pop
```

**Discard local changes:**
```bash
git reset --hard origin/main
git pull origin main
```

### Python/Dependencies Issues

**Recreate virtual environment (Ubuntu/Debian):**
```bash
cd ~/CryptoApp
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
sudo systemctl restart cryptoapp
```

**Reinstall dependencies (RHEL):**
```bash
cd ~/CryptoApp
uv sync --reinstall
sudo systemctl restart cryptoapp
```

### Check Disk Space
```bash
df -h

# Clean old logs if low
sudo journalctl --vacuum-time=7d

# Clean pip cache
pip cache purge
```

### Memory Issues (Small VM)

**If using B1ms (2GB RAM):**
```bash
# Reduce workers in gunicorn.conf.py
nano ~/CryptoApp/gunicorn.conf.py
# Change: workers = 2

# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📊 Testing & Verification

### Test Endpoints
```bash
# Health check
curl http://localhost:5001/health

# API test
curl http://localhost:5001/api/stats
curl http://localhost:5001/api/coins

# Through nginx (if configured)
curl http://localhost/health
```

### Monitor Resources
```bash
# CPU and Memory
htop

# Or basic version
top

# Disk usage
df -h
du -sh ~/CryptoApp/*
```

### Check Service is Running
```bash
# Service status
sudo systemctl status cryptoapp

# Is port open?
sudo netstat -tlnp | grep 5001

# Recent logs
sudo journalctl -u cryptoapp -n 20
```

---

## 🔐 Security Best Practices

### Keep System Updated
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# RHEL
sudo dnf update -y
```

### Secure .env File
```bash
chmod 600 ~/CryptoApp/.env
```

### Use SSH Keys (not passwords)
```bash
# On your local machine
ssh-keygen -t ed25519
ssh-copy-id your-username@your-vm-ip
```

### Configure Firewall
```bash
# Ubuntu/Debian
sudo ufw status
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# RHEL
sudo firewall-cmd --list-all
```

---

## 🎯 Daily Workflow

```bash
# SSH to VM
ssh your-username@your-vm-ip

# Pull latest code
cd ~/CryptoApp
git pull origin main

# Update deps (if needed)
source .venv/bin/activate && pip install -e .  # Ubuntu
# OR
uv sync  # RHEL

# Restart
sudo systemctl restart cryptoapp

# Check logs
sudo journalctl -u cryptoapp -f
```

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| **Update code** | `cd ~/CryptoApp && git pull && sudo systemctl restart cryptoapp` |
| **Check status** | `sudo systemctl status cryptoapp` |
| **View logs** | `sudo journalctl -u cryptoapp -f` |
| **Restart** | `sudo systemctl restart cryptoapp` |
| **Test endpoint** | `curl http://localhost:5001/health` |
| **Check disk** | `df -h` |
| **Check memory** | `free -h` |

---

## 💡 Pro Tips

1. **Alias for quick updates** - Add to `~/.bashrc`:
   ```bash
   alias update-crypto='cd ~/CryptoApp && git pull && sudo systemctl restart cryptoapp && sudo systemctl status cryptoapp'
   ```

2. **Auto-load venv** - Add to `~/.bashrc`:
   ```bash
   cd ~/CryptoApp && source .venv/bin/activate
   ```

3. **Quick log check** - Create script `~/check-crypto.sh`:
   ```bash
   #!/bin/bash
   sudo systemctl status cryptoapp
   echo "---"
   sudo journalctl -u cryptoapp -n 10 --no-pager
   ```

---

**Need more help?** Check the logs: `sudo journalctl -u cryptoapp -n 100`

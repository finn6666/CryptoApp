# Raspberry Pi Deployment

Deploy CryptoApp on a Raspberry Pi 4/5 for 24/7 operation at ~$0.50/month power cost.

---

## Requirements

- Raspberry Pi 4/5 (4GB+ RAM, 8GB recommended)
- 32GB+ microSD (Class 10)
- Raspberry Pi OS 64-bit
- Ethernet recommended

---

## Install

```bash
# System packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-pip python3-venv nginx

# uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Clone and setup
cd ~ && git clone <repo-url> CryptoApp && cd CryptoApp
uv sync

# Configure
cp .env.example .env
nano .env  # Add API keys

# Test
python app.py  # http://<PI_IP>:5001
```

---

## Systemd Service

Create `/etc/systemd/system/cryptoapp.service`:

```ini
[Unit]
Description=CryptoApp - AI Crypto Analysis
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/CryptoApp
Environment="PATH=/home/pi/.cargo/bin:/home/pi/CryptoApp/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/pi/CryptoApp/.venv/bin/python /home/pi/CryptoApp/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cryptoapp

[Install]
WantedBy=multi-user.target
```

Adjust `/home/pi` and `User=pi` to match your setup.

```bash
sudo systemctl daemon-reload
sudo systemctl enable cryptoapp
sudo systemctl start cryptoapp
sudo systemctl status cryptoapp
```

---

## Nginx (Optional)

Proxies port 5001 to port 80.

Create `/etc/nginx/sites-available/cryptoapp`:

```nginx
server {
    listen 80;
    server_name cryptoapp.local _;
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/cryptoapp /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

---

## Updates

```bash
cd ~/CryptoApp && git pull origin main
uv sync
sudo systemctl restart cryptoapp
```

---

## Monitoring

```bash
sudo systemctl status cryptoapp        # Service status
sudo journalctl -u cryptoapp -f        # Live logs
sudo journalctl -u cryptoapp -n 50     # Last 50 lines
vcgencmd measure_temp                  # Temperature
free -h                                # Memory
df -h                                  # Disk
```

---

## Performance Tips

- **Enable swap** (4GB models): set `CONF_SWAPSIZE=2048` in `/etc/dphys-swapfile`
- **Reduce cache**: lower `MAX_CACHE_SIZE` in `ml/agent_config.py`
- **Disable unused services**: `sudo systemctl disable bluetooth`

## Security

```bash
sudo apt install ufw
sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 5001
sudo ufw enable
chmod 600 ~/CryptoApp/.env
```

## Backups

```bash
cp ~/CryptoApp/models/rl_simple_learner.json ~/backups/
cp ~/CryptoApp/data/favorites.json ~/backups/
cp ~/CryptoApp/.env ~/backups/
```

Always `sudo shutdown -h now` before unplugging -- never hard-power-off to avoid SD card corruption.

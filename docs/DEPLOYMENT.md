# Raspberry Pi Deployment

Deploy CryptoApp on a Raspberry Pi 4/5 for 24/7 operation (~£0.50/month power).

## Requirements

- Raspberry Pi 4/5 (4GB+ RAM)
- 32GB+ microSD (Class 10)
- Raspberry Pi OS 64-bit
- Ethernet recommended

## 1. Install

```bash
# System packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y git nginx

# uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Clone and setup
cd ~ && git clone <repo-url> CryptoApp && cd CryptoApp
uv sync

# Configure
cp .env.example .env
nano .env  # Add all API keys (see docs/SETUP.md)

# Quick test
uv run gunicorn -c gunicorn.conf.py wsgi:app
# Visit http://<PI_IP>:5001
```

## 2. Systemd Service

The service file defaults to `User=pi` and `/home/pi/CryptoApp`. If your username or path differs, edit the file after copying:

```bash
sudo cp ~/CryptoApp/deploy/cryptoapp.service /etc/systemd/system/
# Only needed if not using default pi user:
# sudo nano /etc/systemd/system/cryptoapp.service
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cryptoapp
sudo systemctl start cryptoapp
sudo systemctl status cryptoapp
```

## 3. Nginx Reverse Proxy

The nginx config accepts any hostname by default (`server_name _`):

```bash
sudo cp ~/CryptoApp/deploy/nginx-cryptoapp.conf /etc/nginx/sites-available/cryptoapp
sudo ln -s /etc/nginx/sites-available/cryptoapp /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

Now access via `http://<PI_IP>` (port 80).

## 4. Set TRADE_SERVER_URL

Update `.env` so email approval links point to the Pi (use port 80 since nginx fronts gunicorn):

```bash
TRADE_SERVER_URL=http://<PI_IP>
```

Then restart: `sudo systemctl restart cryptoapp`

## 5. Firewall

```bash
sudo apt install -y ufw
sudo ufw allow 22
sudo ufw allow 80
sudo ufw enable
```

Lock down the env file:

```bash
chmod 600 ~/CryptoApp/.env
```

## Updates

```bash
cd ~/CryptoApp && git pull
uv sync
sudo systemctl restart cryptoapp
```

## Monitoring

```bash
sudo systemctl status cryptoapp        # Service status
sudo journalctl -u cryptoapp -f        # Live logs
sudo journalctl -u cryptoapp -n 50     # Last 50 lines
vcgencmd measure_temp                  # CPU temp
free -h                                # Memory
df -h                                  # Disk
```

## Performance Tips

- **Swap**: Set `CONF_SWAPSIZE=2048` in `/etc/dphys-swapfile`, then `sudo systemctl restart dphys-swapfile`
- **Disable bluetooth**: `sudo systemctl disable bluetooth`
- **Never hard-power-off** - always `sudo shutdown -h now` to avoid SD corruption

## Backups

```bash
mkdir -p ~/backups
cp ~/CryptoApp/.env ~/backups/
cp ~/CryptoApp/data/portfolio.json ~/backups/ 2>/dev/null
```

## SSL (Optional)

The included `deploy/setup-ssl-rhel.sh` is for RHEL/Fedora servers. On Raspberry Pi OS (Debian), install certbot manually:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -m your@email.com --agree-tos
# Auto-renewal is configured automatically
```

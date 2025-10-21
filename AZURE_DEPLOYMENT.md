# 🔵 Azure VM Deployment Guide

## 📋 **Prerequisites**

- Azure VM running Ubuntu 20.04+ or similar
- SSH access to your VM
- Domain name or public IP (optional)

## 🚀 **Step-by-Step Azure VM Deployment**

### **1. Connect to Your Azure VM**
```bash
ssh username@your-vm-ip
# Replace with your actual VM username and IP
```

### **2. Update System**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3.9 python3.9-venv python3-pip git nginx curl -y
```

### **3. Clone Your Repository**
```bash
# Option A: If you have a GitHub repo
git clone https://github.com/yourusername/CryptoApp.git
cd CryptoApp

# Option B: Upload files manually
mkdir CryptoApp
cd CryptoApp
# Then upload your files via SCP or SFTP
```

### **4. Set Up Python Environment**
```bash
# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### **5. Test the Application**
```bash
# Run the app to test
python web_app.py

# You should see:
# 🔧 Initializing crypto analyzer...
# 📊 Fetching initial cryptocurrency data...
# ✅ Loaded X coins successfully
# 🚀 Starting web server on http://0.0.0.0:8080
```

### **6. Configure Firewall (Important!)**
```bash
# Allow HTTP traffic
sudo ufw allow 8080
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow ssh
sudo ufw --force enable
```

### **7. Set Up Production Server with Systemd**

Create a systemd service file:
```bash
sudo nano /etc/systemd/system/crypto-analyzer.service
```

Add this content:
```ini
[Unit]
Description=Crypto Investment Analyzer
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/CryptoApp
Environment=PATH=/home/ubuntu/CryptoApp/venv/bin
ExecStart=/home/ubuntu/CryptoApp/venv/bin/gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 web_app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### **8. Start the Service**
```bash
# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl start crypto-analyzer
sudo systemctl enable crypto-analyzer

# Check status
sudo systemctl status crypto-analyzer
```

### **9. Set Up Nginx Reverse Proxy (Optional)**

Create Nginx config:
```bash
sudo nano /etc/nginx/sites-available/crypto-analyzer
```

Add this content:
```nginx
server {
    listen 80;
    server_name your-domain.com your-vm-ip;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/crypto-analyzer /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## 🌐 **Access Your Application**

### **Direct Access (Port 8080):**
```
http://YOUR_VM_PUBLIC_IP:8080
```

### **Through Nginx (Port 80):**
```
http://YOUR_VM_PUBLIC_IP
http://your-domain.com
```

## 📊 **Azure-Specific Configuration**

### **Network Security Group Rules:**
In Azure Portal, add these inbound rules:
- **HTTP**: Port 80, Source: Any
- **HTTPS**: Port 443, Source: Any  
- **Custom**: Port 8080, Source: Any
- **SSH**: Port 22, Source: Your IP

### **Get Your VM's Public IP:**
```bash
curl ifconfig.me
# Or check Azure Portal
```

## 🔧 **Management Commands**

### **View Logs:**
```bash
# Service logs
sudo journalctl -u crypto-analyzer -f

# Application logs
sudo journalctl -u crypto-analyzer --since "1 hour ago"
```

### **Restart Service:**
```bash
sudo systemctl restart crypto-analyzer
```

### **Update Application:**
```bash
cd /home/ubuntu/CryptoApp
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crypto-analyzer
```

### **Monitor Performance:**
```bash
# CPU and memory usage
top
htop

# Service status
sudo systemctl status crypto-analyzer
```

## 🔒 **Security Best Practices**

### **Firewall Configuration:**
```bash
sudo ufw status
sudo ufw deny 22/tcp  # Disable SSH from everywhere
sudo ufw allow from YOUR_IP to any port 22  # Allow SSH only from your IP
```

### **Auto-Updates:**
```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### **SSL Certificate (Optional):**
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 🐛 **Troubleshooting**

### **Common Issues:**

1. **Port 8080 blocked:**
   ```bash
   sudo ufw allow 8080
   sudo systemctl restart crypto-analyzer
   ```

2. **Service won't start:**
   ```bash
   sudo journalctl -u crypto-analyzer --no-pager
   ```

3. **Can't access from internet:**
   - Check Azure NSG rules
   - Verify VM public IP
   - Test: `curl http://YOUR_VM_IP:8080/health`

4. **API rate limits:**
   - CoinGecko limits requests
   - App handles this automatically

### **Debug Commands:**
```bash
# Test if app works locally
cd /home/ubuntu/CryptoApp
source venv/bin/activate
python web_app.py

# Test API endpoints
curl http://localhost:8080/health
curl http://localhost:8080/api/stats
```

## 📱 **Mobile Access**

Your app will be accessible from:
- 💻 **Desktop browsers**
- 📱 **Mobile phones**
- 📟 **Tablets**

Example URLs:
- `http://YOUR_VM_IP:8080`
- `http://your-domain.com`

## 🎉 **Success Checklist**

- ✅ VM updated and secured
- ✅ Python environment set up
- ✅ Application running as service
- ✅ Firewall configured
- ✅ Accessible from internet
- ✅ Auto-restart on reboot
- ✅ Logs available for monitoring

Your crypto analyzer is now running professionally on Azure! 🚀

## 💡 **Next Steps**

1. **Domain Setup:** Point a domain to your VM IP
2. **SSL Certificate:** Add HTTPS with Let's Encrypt
3. **Monitoring:** Set up Azure Monitor alerts
4. **Backup:** Create VM snapshots
5. **Scaling:** Consider Azure Container Instances for auto-scaling

**Support:** Check logs with `sudo journalctl -u crypto-analyzer -f`
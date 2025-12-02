#!/bin/bash

# Raspberry Pi SIEM Setup Script for CryptoApp
# Run this on your Raspberry Pi 4 (4GB)

set -e

echo "🚀 CryptoApp SIEM Setup for Raspberry Pi"
echo "=========================================="

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install Python 3 and pip if not present
echo "🐍 Installing Python 3 and dependencies..."
sudo apt install -y python3 python3-pip python3-venv git

# Install system monitoring tools
echo "📊 Installing system monitoring tools..."
sudo apt install -y htop iotop

# Create project directory
PROJECT_DIR="$HOME/cryptoapp-siem"
echo "📁 Creating project directory at $PROJECT_DIR"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create virtual environment
echo "🔧 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install required Python packages
echo "📚 Installing Python packages..."
pip install --upgrade pip
pip install flask requests psutil

# Copy SIEM files (you'll need to transfer these)
echo "📋 Creating SIEM configuration..."
cat > siem_config.json << 'EOF'
{
  "azure_vm": {
    "url": "http://YOUR-VM-IP:5001",
    "check_interval": 60,
    "timeout": 10
  },
  "thresholds": {
    "cpu_percent": 80,
    "memory_percent": 85,
    "disk_percent": 90,
    "api_latency_ms": 5000,
    "gem_score_spike": 15.0,
    "volume_spike_multiplier": 5.0
  },
  "alerts": {
    "email_enabled": false,
    "email_to": "",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": ""
  },
  "market_monitoring": {
    "coingecko_api": "https://api.coingecko.com/api/v3",
    "check_interval": 300,
    "top_n_coins": 50
  }
}
EOF

echo "⚠️  IMPORTANT: Edit siem_config.json and set your Azure VM IP address!"

# Create systemd service for auto-start
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/cryptoapp-siem.service > /dev/null << EOF
[Unit]
Description=CryptoApp SIEM Dashboard
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python3 dashboard_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Set up log rotation
echo "📝 Configuring log rotation..."
sudo tee /etc/logrotate.d/cryptoapp-siem > /dev/null << 'EOF'
/home/*/cryptoapp-siem/siem_monitor.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0644
}
EOF

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Transfer the SIEM Python files to: $PROJECT_DIR"
echo "   - siem_monitor.py"
echo "   - dashboard_server.py"
echo "   - templates/siem_dashboard.html"
echo ""
echo "2. Edit configuration:"
echo "   nano $PROJECT_DIR/siem_config.json"
echo "   (Set your Azure VM IP address)"
echo ""
echo "3. Enable and start the service:"
echo "   sudo systemctl enable cryptoapp-siem"
echo "   sudo systemctl start cryptoapp-siem"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status cryptoapp-siem"
echo ""
echo "5. View logs:"
echo "   tail -f $PROJECT_DIR/siem_monitor.log"
echo ""
echo "6. Access dashboard:"
echo "   http://$(hostname -I | awk '{print $1}'):5002"
echo ""
echo "🎯 Tip: Use 'scp' or 'git clone' to transfer files to your Pi"

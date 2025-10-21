#!/bin/bash

# Azure VM Deployment Script for RHEL/CentOS/Fedora
# Crypto Investment Analyzer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔵 Starting Azure VM deployment for Crypto Investment Analyzer (RHEL)...${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}[ERROR] Please don't run this script as root. Use a regular user with sudo privileges.${NC}"
    exit 1
fi

# Get current user and directory
CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)
APP_DIR="/home/$CURRENT_USER/crypto-analyzer"

echo -e "${BLUE}[INFO] Deploying as user: $CURRENT_USER${NC}"
echo -e "${BLUE}[INFO] Current directory: $CURRENT_DIR${NC}"

# Update system packages
echo -e "${BLUE}[INFO] Updating system packages...${NC}"
sudo dnf update -y

# Install required packages
echo -e "${BLUE}[INFO] Installing required packages...${NC}"
sudo dnf install -y python3 python3-pip python3-venv git curl wget firewalld nginx

# Enable and start firewalld
echo -e "${BLUE}[INFO] Configuring firewall...${NC}"
sudo systemctl enable firewalld
sudo systemctl start firewalld

# Open port 8080 for the application
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

echo -e "${GREEN}✅ Firewall configured - Port 8080 opened${NC}"

# Create application directory
echo -e "${BLUE}[INFO] Setting up application directory...${NC}"
mkdir -p "$APP_DIR"

# Copy application files
echo -e "${BLUE}[INFO] Copying application files...${NC}"
cp -r "$CURRENT_DIR"/* "$APP_DIR/" 2>/dev/null || true
cd "$APP_DIR"

# Create virtual environment
echo -e "${BLUE}[INFO] Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo -e "${BLUE}[INFO] Installing Python dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    # Install basic dependencies if requirements.txt is missing
    pip install flask requests rich
fi

# Create systemd service
echo -e "${BLUE}[INFO] Creating systemd service...${NC}"
sudo tee /etc/systemd/system/crypto-analyzer.service > /dev/null <<EOF
[Unit]
Description=Crypto Investment Analyzer
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python web_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable crypto-analyzer.service

# Start the service
echo -e "${BLUE}[INFO] Starting Crypto Analyzer service...${NC}"
sudo systemctl start crypto-analyzer.service

# Check service status
sleep 3
if sudo systemctl is-active --quiet crypto-analyzer.service; then
    echo -e "${GREEN}✅ Crypto Analyzer service is running${NC}"
else
    echo -e "${YELLOW}⚠️ Service may be starting up. Check status with: sudo systemctl status crypto-analyzer.service${NC}"
fi

# Get VM IP address
VM_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || echo "YOUR_VM_IP")

# Configure Nginx (optional reverse proxy)
read -p "Would you like to set up Nginx reverse proxy? (y/N): " setup_nginx

if [[ $setup_nginx =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}[INFO] Configuring Nginx...${NC}"
    
    sudo tee /etc/nginx/conf.d/crypto-analyzer.conf > /dev/null <<EOF
server {
    listen 80;
    server_name $VM_IP;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Test Nginx configuration
    sudo nginx -t
    
    # Enable and start Nginx
    sudo systemctl enable nginx
    sudo systemctl restart nginx
    
    echo -e "${GREEN}✅ Nginx configured as reverse proxy${NC}"
    echo -e "${GREEN}🌐 Your app is available at: http://$VM_IP${NC}"
else
    echo -e "${GREEN}🌐 Your app is available at: http://$VM_IP:8080${NC}"
fi

# Create log viewing script
tee "$APP_DIR/view_logs.sh" > /dev/null <<'EOF'
#!/bin/bash
echo "=== Crypto Analyzer Service Status ==="
sudo systemctl status crypto-analyzer.service

echo -e "\n=== Recent Logs ==="
sudo journalctl -u crypto-analyzer.service -f --lines=50
EOF

chmod +x "$APP_DIR/view_logs.sh"

# Create management scripts
tee "$APP_DIR/manage.sh" > /dev/null <<'EOF'
#!/bin/bash

case "$1" in
    start)
        sudo systemctl start crypto-analyzer.service
        echo "✅ Service started"
        ;;
    stop)
        sudo systemctl stop crypto-analyzer.service
        echo "🛑 Service stopped"
        ;;
    restart)
        sudo systemctl restart crypto-analyzer.service
        echo "🔄 Service restarted"
        ;;
    status)
        sudo systemctl status crypto-analyzer.service
        ;;
    logs)
        sudo journalctl -u crypto-analyzer.service -f --lines=50
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
EOF

chmod +x "$APP_DIR/manage.sh"

echo
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo -e "   • Application directory: $APP_DIR"
echo -e "   • Service name: crypto-analyzer.service"
echo -e "   • Port: 8080"
if [[ $setup_nginx =~ ^[Yy]$ ]]; then
    echo -e "   • Access URL: http://$VM_IP (Nginx proxy)"
    echo -e "   • Direct URL: http://$VM_IP:8080"
else
    echo -e "   • Access URL: http://$VM_IP:8080"
fi
echo
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo -e "   • Start service: ./manage.sh start"
echo -e "   • Stop service: ./manage.sh stop"
echo -e "   • Restart service: ./manage.sh restart"
echo -e "   • Check status: ./manage.sh status"
echo -e "   • View logs: ./manage.sh logs"
echo -e "   • Quick logs: ./view_logs.sh"
echo
echo -e "${BLUE}🔍 Troubleshooting:${NC}"
echo -e "   • Check service: sudo systemctl status crypto-analyzer.service"
echo -e "   • View logs: sudo journalctl -u crypto-analyzer.service -f"
echo -e "   • Test connection: curl http://localhost:8080"
echo
echo -e "${GREEN}🚀 Your Crypto Investment Analyzer is now running!${NC}"

# Final service status check
echo -e "${BLUE}[INFO] Final service status check...${NC}"
sudo systemctl status crypto-analyzer.service --no-pager -l
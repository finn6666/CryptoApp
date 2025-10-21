#!/bin/bash

# 🔵 Azure VM Deployment Script
# Run this script on your Azure VM to deploy the Crypto Analyzer

set -e  # Exit on any error

echo "🔵 Starting Azure VM deployment for Crypto Investment Analyzer..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please don't run this script as root. Use a regular user with sudo privileges."
    exit 1
fi

# Variables
APP_DIR="$HOME/CryptoApp"
SERVICE_NAME="crypto-analyzer"
PYTHON_VERSION="python3.9"

print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

print_status "Installing required packages..."
sudo apt install -y python3.9 python3.9-venv python3-pip git nginx curl ufw

print_status "Setting up firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8080

print_status "Creating application directory..."
if [ -d "$APP_DIR" ]; then
    print_warning "Directory $APP_DIR already exists. Backing up..."
    sudo mv "$APP_DIR" "${APP_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
fi

mkdir -p "$APP_DIR"
cd "$APP_DIR"

print_status "Setting up Python virtual environment..."
$PYTHON_VERSION -m venv venv
source venv/bin/activate

print_status "Installing Python dependencies..."
cat > requirements.txt << 'EOF'
rich>=13.0.0
tabulate>=0.9.0
colorama>=0.4.6
requests>=2.31.0
flask>=2.3.0
gunicorn>=21.0.0
EOF

pip install --upgrade pip
pip install -r requirements.txt

print_status "If you have your code in a Git repository, clone it now:"
print_warning "Otherwise, you'll need to upload your Python files manually."
echo ""
echo "To clone from Git (replace with your repo URL):"
echo "git clone https://github.com/yourusername/CryptoApp.git temp_repo"
echo "cp -r temp_repo/* ."
echo "rm -rf temp_repo"
echo ""
echo "Or upload these files manually:"
echo "- web_app.py"
echo "- crypto_analyzer.py"
echo "- crypto_display.py"
echo "- crypto_visualizer.py"
echo "- live_data_fetcher.py"
echo "- templates/index.html"
echo ""
read -p "Press Enter when you have uploaded your code files..."

# Check if required files exist
REQUIRED_FILES=("web_app.py" "crypto_analyzer.py" "live_data_fetcher.py")
MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -ne 0 ]; then
    print_error "Missing required files: ${MISSING_FILES[*]}"
    print_error "Please upload all required Python files and run this script again."
    exit 1
fi

# Create templates directory if it doesn't exist
mkdir -p templates

print_status "Testing the application..."
timeout 10s python web_app.py &
sleep 5
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    print_success "Application is working correctly!"
    pkill -f web_app.py
else
    print_warning "Application test failed, but continuing with deployment..."
fi

print_status "Creating systemd service..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=Crypto Investment Analyzer
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 web_app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

print_status "Starting and enabling service..."
sudo systemctl daemon-reload
sudo systemctl start $SERVICE_NAME
sudo systemctl enable $SERVICE_NAME

# Wait a moment for service to start
sleep 3

if sudo systemctl is-active --quiet $SERVICE_NAME; then
    print_success "Service is running successfully!"
else
    print_error "Service failed to start. Check logs with: sudo journalctl -u $SERVICE_NAME"
    exit 1
fi

print_status "Setting up Nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/$SERVICE_NAME > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# Get public IP
PUBLIC_IP=$(curl -s ifconfig.me)

print_success "🎉 Deployment completed successfully!"
echo ""
echo "📊 Your Crypto Investment Analyzer is now running!"
echo ""
echo "🌐 Access URLs:"
echo "   • Direct access: http://$PUBLIC_IP:8080"
echo "   • Through Nginx: http://$PUBLIC_IP"
echo ""
echo "🔧 Management commands:"
echo "   • Check status: sudo systemctl status $SERVICE_NAME"
echo "   • View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "   • Restart: sudo systemctl restart $SERVICE_NAME"
echo ""
echo "🔒 Security notes:"
echo "   • Firewall is configured to allow HTTP traffic"
echo "   • Consider setting up SSL with Let's Encrypt"
echo "   • Monitor the application logs regularly"
echo ""
echo "📋 Next steps:"
echo "   1. Test your application: curl http://$PUBLIC_IP:8080/health"
echo "   2. Configure your domain (optional)"
echo "   3. Set up SSL certificate (recommended)"
echo "   4. Configure Azure NSG rules if needed"
echo ""
print_success "Happy crypto analyzing! 🚀"
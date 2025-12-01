#!/bin/bash
# RHEL SSL Setup Script for CryptoApp
# Usage: ./setup-ssl-rhel.sh yourdomain.com your-email@example.com

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Check arguments
if [ $# -lt 2 ]; then
    echo -e "${RED}Usage: $0 <domain> <email>${NC}"
    echo "Example: $0 crypto.example.com your-email@example.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2
APP_USER=${3:-$SUDO_USER}  # Use current user if not specified
APP_DIR="/home/$APP_USER/CryptoApp"

echo -e "${GREEN}=== CryptoApp RHEL SSL Setup ===${NC}"
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo "App User: $APP_USER"
echo "App Directory: $APP_DIR"
echo ""

# Confirm
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo -e "${YELLOW}Step 1: Installing Certbot...${NC}"
dnf install -y certbot python3-certbot-nginx

echo -e "${YELLOW}Step 2: Stopping nginx temporarily...${NC}"
systemctl stop nginx

echo -e "${YELLOW}Step 3: Getting SSL certificate...${NC}"
certbot certonly --standalone \
    -d $DOMAIN \
    --non-interactive \
    --agree-tos \
    --email $EMAIL \
    --preferred-challenges http

if [ $? -ne 0 ]; then
    echo -e "${RED}Certificate request failed!${NC}"
    echo "Make sure:"
    echo "  - Port 80 is open in Azure NSG"
    echo "  - DNS points to this server"
    echo "  - Domain is correct"
    exit 1
fi

echo -e "${YELLOW}Step 4: Creating nginx SSL configuration...${NC}"

cat > /etc/nginx/conf.d/cryptoapp.conf << EOF
# HTTP - Redirect to HTTPS
server {
    listen 80;
    server_name $DOMAIN;

    # Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect everything else to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL Certificate
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    
    # SSL Session Cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS (Force HTTPS for 1 year)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files (optional optimization)
    location /static/ {
        alias $APP_DIR/src/web/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Access and error logs
    access_log /var/log/nginx/cryptoapp_access.log;
    error_log /var/log/nginx/cryptoapp_error.log;
}
EOF

echo -e "${YELLOW}Step 5: Configuring SELinux for nginx...${NC}"
# Allow nginx to connect to backend
setsebool -P httpd_can_network_connect 1

# Allow nginx to read app files
chcon -R -t httpd_sys_content_t $APP_DIR/src/web/static/ 2>/dev/null || true

echo -e "${YELLOW}Step 6: Configuring firewall...${NC}"
# Open ports
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload

echo -e "${YELLOW}Step 7: Testing nginx configuration...${NC}"
nginx -t

if [ $? -ne 0 ]; then
    echo -e "${RED}Nginx configuration test failed!${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 8: Starting services...${NC}"
systemctl enable nginx
systemctl start nginx
systemctl restart cryptoapp

echo -e "${YELLOW}Step 9: Setting up auto-renewal...${NC}"
# Test renewal
certbot renew --dry-run

# Create renewal hook to reload nginx
cat > /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh << 'EOF'
#!/bin/bash
systemctl reload nginx
EOF
chmod +x /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh

# Ensure certbot timer is enabled
systemctl enable certbot-renew.timer
systemctl start certbot-renew.timer

echo ""
echo -e "${GREEN}=== SSL Setup Complete! ===${NC}"
echo ""
echo "✅ SSL Certificate installed"
echo "✅ Nginx configured with HTTPS"
echo "✅ HTTP → HTTPS redirect enabled"
echo "✅ Security headers configured"
echo "✅ Auto-renewal enabled"
echo ""
echo "🌐 Visit: https://$DOMAIN"
echo ""
echo "Verify SSL grade: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo ""
echo -e "${YELLOW}Status Check:${NC}"
systemctl status nginx --no-pager -l
echo ""
systemctl status cryptoapp --no-pager -l

echo ""
echo -e "${GREEN}Certificate will auto-renew before expiration.${NC}"
echo "Check renewal timer: systemctl status certbot-renew.timer"

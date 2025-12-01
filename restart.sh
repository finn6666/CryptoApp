#!/bin/bash
# Simple script to restart the CryptoApp service

echo "🔄 Restarting CryptoApp service..."
sudo systemctl restart cryptoapp

# Wait a moment for service to start
sleep 3

# Check status
if sudo systemctl is-active --quiet cryptoapp; then
    echo "✅ CryptoApp service restarted successfully"
    echo "📊 Service status:"
    sudo systemctl status cryptoapp --no-pager -l | head -10
else
    echo "❌ Failed to restart CryptoApp service"
    echo "🔍 Recent logs:"
    sudo journalctl -u cryptoapp -n 20 --no-pager
    exit 1
fi

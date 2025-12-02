# 🛡️ Raspberry Pi SIEM Dashboard for CryptoApp

Transform your Raspberry Pi 4 (4GB) into a dedicated Security Information and Event Management (SIEM) dashboard for monitoring your CryptoApp Azure VM and detecting market anomalies.

## 🎯 What It Does

- **VM Health Monitoring** - Tracks Azure VM uptime, latency, and availability
- **System Metrics** - Real-time Pi CPU, memory, disk, and temperature monitoring
- **Market Anomalies** - Detects unusual gem scores, volume spikes, and price movements
- **Alert Management** - Categorizes and displays alerts by severity (Critical/High/Medium/Low)
- **Web Dashboard** - Beautiful real-time SIEM interface accessible from any device
- **Email Alerts** - Optional email notifications for critical events

## 📊 Dashboard Features

### Real-Time Monitoring
- Live system metrics with color-coded warnings
- VM health status and API latency tracking
- Alert counters by severity level
- Recent alerts timeline with filtering

### Intelligent Alerts
- **CRITICAL**: VM offline, system failures
- **HIGH**: High latency, unusual volume spikes, resource exhaustion
- **MEDIUM**: Gem score spikes, elevated resource usage, high temperature
- **LOW**: Informational events

### Anomaly Detection
- Volume/Market Cap ratio analysis
- Gem score spike detection
- Cross-correlation with ML predictions
- Smart money movement tracking

## 🚀 Quick Start

### 1. Transfer Files to Your Pi

```bash
# From your Mac, transfer the SIEM system to your Pi
cd /Users/finnbryant/Dev/CryptoApp
scp -r raspberry_pi pi@your-pi-ip:~/cryptoapp-siem

# Or use git
ssh pi@your-pi-ip
git clone https://github.com/finn6666/CryptoApp.git
cd CryptoApp/raspberry_pi
```

### 2. Run Setup Script

```bash
ssh pi@your-pi-ip
cd ~/cryptoapp-siem
chmod +x setup_pi.sh
./setup_pi.sh
```

### 3. Configure Your Azure VM IP

```bash
nano siem_config.json
# Change "url": "http://YOUR-VM-IP:5001" to your actual VM IP
```

### 4. Start the SIEM Dashboard

```bash
# Manual start (for testing)
source venv/bin/activate
python3 dashboard_server.py

# Or enable as a service (auto-start on boot)
sudo systemctl enable cryptoapp-siem
sudo systemctl start cryptoapp-siem
sudo systemctl status cryptoapp-siem
```

### 5. Access Dashboard

Open your browser to: `http://your-pi-ip:5002`

## 📱 Configuration

### Basic Configuration (`siem_config.json`)

```json
{
  "azure_vm": {
    "url": "http://your-vm-ip:5001",
    "check_interval": 60,  // Check every 60 seconds
    "timeout": 10
  },
  "thresholds": {
    "cpu_percent": 80,
    "memory_percent": 85,
    "disk_percent": 90,
    "api_latency_ms": 5000,
    "gem_score_spike": 15.0,
    "volume_spike_multiplier": 5.0
  }
}
```

### Email Alerts (Optional)

Enable email notifications for critical alerts:

```json
{
  "alerts": {
    "email_enabled": true,
    "email_to": "your-email@example.com",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "your-email@gmail.com",
    "smtp_password": "your-app-password"
  }
}
```

**Gmail Setup**: Use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

## 🔧 System Requirements

- **Hardware**: Raspberry Pi 4 (4GB RAM minimum)
- **OS**: Raspberry Pi OS (Debian-based)
- **Storage**: 32GB+ SD card or USB SSD recommended
- **Network**: Ethernet connection preferred for reliability
- **Python**: 3.7+

## 📊 Architecture

```
┌─────────────────┐
│  Raspberry Pi   │
│  SIEM Monitor   │
│                 │
│  ┌───────────┐  │
│  │ Dashboard │  │◄─── Browser Access (Port 5002)
│  │  Server   │  │
│  └───────────┘  │
│        │        │
│  ┌───────────┐  │
│  │ Monitoring│  │
│  │  Engine   │  │
│  └───────────┘  │
└────────┬────────┘
         │
    Health Checks
    Every 60s
         │
         ▼
┌─────────────────┐
│   Azure VM      │
│   CryptoApp     │
│   (Port 5001)   │
└─────────────────┘
```

## 🎯 Use Cases

### 1. Infrastructure Monitoring
- Detect when Azure VM goes down
- Track API response times
- Monitor resource usage on both systems

### 2. Market Surveillance
- Alert on hidden gems breaking out
- Track unusual trading volumes
- Monitor whale activity patterns

### 3. ML System Monitoring
- Track ML prediction accuracy
- Alert on model drift
- Monitor RL agent decisions

### 4. Security Events
- Unusual API access patterns
- System resource anomalies
- Failed authentication attempts (future feature)

## 📝 API Endpoints

The dashboard server exposes these endpoints:

- `GET /` - Main dashboard page
- `GET /api/dashboard` - Complete dashboard data
- `GET /api/alerts` - All recent alerts
- `GET /api/alerts/<severity>` - Alerts by severity
- `GET /api/metrics/vm` - Azure VM metrics
- `GET /api/metrics/pi` - Raspberry Pi metrics
- `GET /api/status` - System status

## 🔍 Monitoring What Matters

### System Health
- CPU, Memory, Disk usage with thresholds
- Temperature monitoring (Pi-specific)
- Network connectivity
- Process status

### Application Health
- Azure VM uptime and availability
- API latency and response times
- Database connectivity (if exposed)
- Service health endpoints

### Market Intelligence
- High gem scores (>15.0 = unusual opportunity)
- Volume spikes (>5x normal = whale activity)
- Price movements (>50% in 24h)
- ML prediction anomalies

## 🛠️ Maintenance

### View Logs
```bash
# SIEM logs
tail -f ~/cryptoapp-siem/siem_monitor.log

# Service logs
sudo journalctl -u cryptoapp-siem -f
```

### Restart Service
```bash
sudo systemctl restart cryptoapp-siem
```

### Update Configuration
```bash
nano ~/cryptoapp-siem/siem_config.json
sudo systemctl restart cryptoapp-siem
```

### Check Pi Temperature
```bash
vcgencmd measure_temp
```

## 🔐 Security Considerations

1. **Firewall**: Only expose port 5002 to your local network
2. **Passwords**: Use strong passwords in config files
3. **File Permissions**: Keep config files readable only by your user
   ```bash
   chmod 600 ~/cryptoapp-siem/siem_config.json
   ```
4. **Network**: Use VPN when accessing remotely
5. **Updates**: Keep Pi OS and packages updated regularly

## 💡 Tips & Tricks

### Performance Optimization (4GB RAM)
- Monitor runs efficiently using ~200-300MB RAM
- Dashboard auto-refreshes every 10s (configurable)
- Keeps last 1000 alerts in memory (adjust if needed)
- Log rotation prevents disk fill-up

### Cooling Your Pi
- Use a case with fan for 24/7 operation
- Monitor temperature in dashboard
- Alert triggers at 70°C (configurable)

### Network Reliability
- Use Ethernet instead of WiFi
- Consider UPS for power stability
- Set static IP for easier access

### Extending Functionality
- Add Telegram bot notifications
- Integrate with Grafana for advanced visualization
- Export metrics to InfluxDB for long-term storage
- Add webhook support for automation

## 📈 Future Enhancements

- [ ] Machine learning on alert patterns
- [ ] Predictive failure detection
- [ ] SMS/Telegram notifications
- [ ] Multi-VM monitoring
- [ ] Historical trend analysis
- [ ] Blockchain transaction monitoring
- [ ] Integration with external SIEM tools

## 🐛 Troubleshooting

### Dashboard won't load
```bash
# Check if service is running
sudo systemctl status cryptoapp-siem

# Check logs
tail -50 ~/cryptoapp-siem/siem_monitor.log

# Test manually
cd ~/cryptoapp-siem
source venv/bin/activate
python3 dashboard_server.py
```

### Can't connect to Azure VM
- Verify VM IP in `siem_config.json`
- Check VM is running: `curl http://your-vm-ip:5001/api/health`
- Verify firewall allows port 5001
- Check VM service: `sudo systemctl status cryptoapp`

### High CPU/Memory on Pi
- Increase `check_interval` in config (reduce frequency)
- Reduce `maxlen` in deque buffers (less history)
- Disable market monitoring if not needed
- Check for other running processes

## 📞 Support

For issues or questions:
1. Check the logs first
2. Review configuration settings
3. Test connectivity manually
4. Open an issue on GitHub

## 🎉 Credits

Built for CryptoApp - AI-powered cryptocurrency analysis platform
Optimized for Raspberry Pi 4 (4GB RAM)

---

**Happy Monitoring! 🛡️📊**

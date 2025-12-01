# Auto-Shutdown Feature

The CryptoApp includes an automatic shutdown feature to save resources when idle.

## How It Works

- **Idle Timeout**: 5 minutes (300 seconds)
- **Monitoring**: Checks every 30 seconds for activity
- **Trigger**: Any HTTP request to the app (page loads, API calls)
- **Action**: Gracefully shuts down the service after 5 minutes of no activity

## Activity Tracking

The idle timer resets on ANY request:
- Page loads (`/`)
- API calls (`/api/*`)
- Health checks (`/health`)
- Static files (CSS, JS)

## Checking Idle Status

```bash
# Check current idle time and time until shutdown
curl http://localhost:5001/api/status/idle
```

Response includes:
- `auto_shutdown_enabled`: Whether feature is active
- `current_idle_seconds`: How long since last activity
- `time_until_shutdown_seconds`: Countdown to shutdown
- `last_activity`: Timestamp of last request

## Restarting After Auto-Shutdown

Use the provided restart script:

```bash
# On the VM
cd /path/to/CryptoApp
./restart.sh
```

Or manually:
```bash
sudo systemctl start cryptoapp
```

## Disabling Auto-Shutdown

To disable the auto-shutdown feature:

1. Edit the systemd service file:
```bash
sudo nano /etc/systemd/system/cryptoapp.service
```

2. Add this line under `[Service]`:
```
Environment=AUTO_SHUTDOWN=false
```

3. Reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart cryptoapp
```

## Why Auto-Shutdown?

- **Save Resources**: No CPU/memory usage when idle
- **Cost Efficiency**: Reduce Azure VM costs for low-traffic apps
- **Energy Efficient**: Environmentally friendly
- **Quick Restart**: Service starts in ~5 seconds when needed

## Monitoring

Check logs for shutdown events:
```bash
sudo journalctl -u cryptoapp -f | grep "Shutting down"
```

You'll see:
```
🛑 No activity for 301s. Shutting down to save resources...
```

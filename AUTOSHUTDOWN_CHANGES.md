# Auto-Shutdown Implementation Summary

## What Was Added

### 1. Idle Monitoring System
- **Location**: `app.py` (lines ~280-305)
- **Timeout**: 5 minutes (300 seconds)
- **Check Interval**: Every 30 seconds
- **Action**: Graceful shutdown via SIGTERM

### 2. Activity Tracking
- **Middleware**: `@app.before_request` decorator
- **Tracks**: ALL HTTP requests (pages, APIs, static files)
- **Resets**: Idle timer on every request

### 3. Status Endpoint
- **URL**: `/api/status/idle`
- **Shows**: Current idle time, time until shutdown, last activity

### 4. Configuration
- **Environment Variable**: `AUTO_SHUTDOWN=true/false`
- **Default**: Enabled
- **Override**: Set to `false` in systemd service to disable

### 5. Restart Script
- **File**: `restart.sh`
- **Purpose**: Quick restart after auto-shutdown
- **Usage**: `./restart.sh`

## How to Deploy

1. **On VM, pull changes**:
```bash
cd ~/CryptoApp
git pull
```

2. **Restart service to activate**:
```bash
sudo systemctl restart cryptoapp
```

3. **Verify it's working**:
```bash
curl http://localhost:5001/api/status/idle
```

## Testing Auto-Shutdown

1. **Start service and check status**:
```bash
curl http://localhost:5001/api/status/idle | jq '.time_until_shutdown_minutes'
```

2. **Wait 5 minutes without making requests**
   - Don't load the page
   - Don't call APIs
   - Service will automatically shut down

3. **Check service stopped**:
```bash
sudo systemctl status cryptoapp
# Should show "inactive (dead)"
```

4. **Restart when needed**:
```bash
./restart.sh
# or
sudo systemctl start cryptoapp
```

## Files Changed

- `app.py`: Added idle monitoring, activity tracking, status endpoint
- `restart.sh`: NEW - Quick restart script
- `AUTO_SHUTDOWN.md`: NEW - Documentation

## Benefits

✅ Saves CPU/memory when idle  
✅ Reduces Azure costs for low-traffic apps  
✅ Automatic - no manual intervention  
✅ Quick restart (~5 seconds)  
✅ Configurable via environment variable  
✅ Monitoring via status endpoint  

## Notes

- The idle timer counts from the LAST request (including health checks, static files, etc.)
- Any page load or API call resets the timer back to 5 minutes
- The service gracefully shuts down (finishes current requests)
- Systemd won't auto-restart after shutdown (would defeat the purpose)
- Use `./restart.sh` or manually start the service when needed

# Cost Optimization Settings for Crypto Analyzer

# API Call Optimization
FETCH_INTERVAL_MINUTES = 15  # Reduced from 5 to 15 minutes (saves 66% API calls)
MAX_COINS_PER_REQUEST = 25   # Reduced from 50 to 25 (saves bandwidth)
CACHE_DURATION_MINUTES = 10  # Cache data for 10 minutes

# Cost-Optimized VM Recommendations
RECOMMENDED_VM_SIZES = {
    'development': 'Standard_B1s',   # $3.80/month - 1 vCPU, 1GB RAM
    'production': 'Standard_B1ms',   # $7.60/month - 1 vCPU, 2GB RAM
    'high_traffic': 'Standard_B2s'   # $15.20/month - 2 vCPU, 4GB RAM
}

# Auto-shutdown schedule (saves ~70% when VM runs 8h/day)
AUTO_SHUTDOWN_TIME = "23:00"  # 11 PM daily shutdown
AUTO_START_TIME = "07:00"     # 7 AM daily start

# Storage optimization
DISK_SIZE_GB = 30            # Minimum required size
STORAGE_TYPE = "Standard_LRS" # Cheapest storage option

# Monitoring thresholds
COST_ALERT_THRESHOLDS = [5, 10, 15]  # Alert at $5, $10, $15
MONTHLY_BUDGET_LIMIT = 20             # Maximum $20/month

# Application optimization
ENABLE_COMPRESSION = True    # Reduce bandwidth usage
LOG_RETENTION_DAYS = 7       # Keep logs for 7 days only
CLEANUP_OLD_DATA = True      # Remove data older than 24 hours
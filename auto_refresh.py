#!/usr/bin/env python3
"""
Auto-refresh script that updates data every 30 minutes
Usage: python3 auto_refresh.py
"""

import time
import schedule
from src.core.live_data_fetcher import fetch_and_update_data

def refresh_job():
    """Job function to refresh data"""
    print(f"🔄 Auto-refreshing data at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    result = fetch_and_update_data()
    if result:
        print("✅ Auto-refresh completed!")
    else:
        print("❌ Auto-refresh failed!")

if __name__ == "__main__":
    # Run immediately on start
    refresh_job()
    
    # Schedule to run every 30 minutes
    schedule.every(30).minutes.do(refresh_job)
    
    print("🤖 Auto-refresh started! Data will update every 30 minutes.")
    print("Press Ctrl+C to stop...")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Auto-refresh stopped!")

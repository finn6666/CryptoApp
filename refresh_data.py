#!/usr/bin/env python3
"""
Simple script to refresh cryptocurrency data
Usage: python3 refresh_data.py
"""

from src.core.live_data_fetcher import fetch_and_update_data

if __name__ == "__main__":
    print("🔄 Refreshing cryptocurrency data...")
    result = fetch_and_update_data()
    if result:
        print("✅ Data refresh completed successfully!")
    else:
        print("❌ Data refresh failed!")

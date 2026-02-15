#!/usr/bin/env python3

"""
Simplified main entry point for the Crypto Investment Analyzer
Focuses on low cap cryptocurrency opportunities
"""

import os
import sys
from src.core.live_data_fetcher import fetch_and_update_data

def main():
    """Main entry point - fetch live data and start web app"""
    try:
        print("[INFO] Crypto Investment Analyzer - Low Cap Focus")
        print("=" * 50)
        
        # Always fetch fresh data focusing on low cap opportunities
        print("[INFO] Fetching live low cap cryptocurrency data...")
        live_data = fetch_and_update_data()
        
        if not live_data:
            print("[WARNING] Failed to fetch live data, using existing data.")
        else:
            print("[SUCCESS] Live data updated successfully!")
            # Check if live_data is a dict with coin data
            if isinstance(live_data, dict) and 'all_coins' in live_data:
                print(f"[INFO] Found {len(live_data['all_coins'])} low cap opportunities")
            else:
                print("[INFO] Low cap data fetched and saved to file")
        
        print("\n[INFO] Starting web application...")
        print("Visit: http://127.0.0.1:5001")
        print("Press Ctrl+C to stop\n")
        
        # Import and run the web app
        from app import app
        debug = os.environ.get('DEBUG', 'false').lower() in ('1', 'true', 'yes')
        app.run(debug=debug, host='127.0.0.1', port=5001)
            
    except FileNotFoundError:
        print("[ERROR] Error: Required data files not found!")
        print("Make sure the data directory exists.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

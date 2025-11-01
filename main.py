#!/usr/bin/env python3

"""
Simplified main entry point for the Crypto Investment Analyzer
Focuses on low cap cryptocurrency opportunities
"""

import sys
from src.core.live_data_fetcher import fetch_and_update_data

def main():
    """Main entry point - fetch live data and start web app"""
    try:
        print("🔍 Crypto Investment Analyzer - Low Cap Focus")
        print("=" * 50)
        
        # Always fetch fresh data focusing on low cap opportunities
        print("🌐 Fetching live low cap cryptocurrency data...")
        live_data = fetch_and_update_data()
        
        if not live_data:
            print("⚠️  Failed to fetch live data, using existing data.")
        else:
            print("✅ Live data updated successfully!")
            # Check if live_data is a dict with coin data
            if isinstance(live_data, dict) and 'all_coins' in live_data:
                print(f"📊 Found {len(live_data['all_coins'])} low cap opportunities")
            else:
                print("📊 Low cap data fetched and saved to file")
        
        print("\n🚀 Starting web application...")
        print("Visit: http://127.0.0.1:5001")
        print("Press Ctrl+C to stop\n")
        
        # Import and run the web app
        from app import app
        app.run(debug=True, host='127.0.0.1', port=5001)
            
    except FileNotFoundError:
        print("❌ Error: Required data files not found!")
        print("Make sure the data directory exists.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

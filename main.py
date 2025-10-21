#!/usr/bin/env python3
"""
Crypto Investment Analyzer
A tool to analyze and recommend attractive cryptocurrency investments
"""

import sys
import argparse
from crypto_display import CryptoDisplay
from live_data_fetcher import fetch_and_update_data

def main():
    parser = argparse.ArgumentParser(
        description="Crypto Investment Analyzer - Find attractive crypto opportunities"
    )
    parser.add_argument(
        "--mode", 
        choices=["analysis", "interactive"], 
        default="analysis",
        help="Run mode: 'analysis' for full report, 'interactive' for menu-driven interface"
    )
    parser.add_argument(
        "--top", 
        type=int, 
        default=5,
        help="Number of top coins to show (default: 5)"
    )
    parser.add_argument(
        "--live", 
        action="store_true",
        help="Fetch live data from CoinGecko API before analysis"
    )
    
    args = parser.parse_args()
    
    try:
        # Fetch live data if requested
        if args.live:
            print("🌐 Fetching live cryptocurrency data...")
            live_data = fetch_and_update_data()
            if not live_data:
                print("⚠️  Failed to fetch live data, using existing data.")
            else:
                print("✅ Live data updated successfully!\n")
        
        display = CryptoDisplay()
        
        if args.mode == "interactive":
            display.run_interactive()
        else:
            display.run_full_analysis()
            
    except FileNotFoundError:
        print("❌ Error: api.json file not found!")
        print("Make sure the API data file exists in the current directory.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

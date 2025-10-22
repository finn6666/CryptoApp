#!/usr/bin/env python3
"""
Test the new favorites functionality
"""

import requests
import json
import time
import sys

# Test server URL
BASE_URL = "http://localhost:8080"

def test_favorites_api():
    """Test the favorites API endpoints"""
    print("🧪 Testing Favorites API...")
    print("=" * 40)
    
    # Start the Flask app in background for testing
    import subprocess
    import threading
    
    def run_flask_app():
        try:
            subprocess.run([sys.executable, "web_app.py"], 
                         capture_output=True, timeout=10)
        except:
            pass
    
    # Start Flask app in background
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    time.sleep(3)  # Give Flask time to start
    
    try:
        # Test 1: Get empty favorites initially
        print("📋 Test 1: Get initial favorites...")
        response = requests.get(f"{BASE_URL}/api/favorites", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}, Count: {data['count']}")
        else:
            print(f"❌ Failed: Status {response.status_code}")
            return False
        
        # Test 2: Add a favorite coin
        print("\n⭐ Test 2: Add favorite coin...")
        test_coin = {
            "coin_id": "bitcoin",
            "coin_name": "Bitcoin"
        }
        response = requests.post(f"{BASE_URL}/api/favorites/add", 
                               json=test_coin, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
        else:
            print(f"❌ Failed: Status {response.status_code}")
            return False
        
        # Test 3: Get favorites (should have 1 now)
        print("\n📋 Test 3: Get favorites after adding...")
        response = requests.get(f"{BASE_URL}/api/favorites", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}, Count: {data['count']}")
            if data['count'] > 0:
                print(f"   First favorite: {data['favorites'][0]['name']}")
        else:
            print(f"❌ Failed: Status {response.status_code}")
            return False
        
        # Test 4: Remove the favorite
        print("\n🗑️  Test 4: Remove favorite coin...")
        remove_coin = {"coin_id": "bitcoin"}
        response = requests.post(f"{BASE_URL}/api/favorites/remove", 
                               json=remove_coin, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
        else:
            print(f"❌ Failed: Status {response.status_code}")
            return False
        
        print("\n🎉 All favorites tests passed!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask app. Try running:")
        print("   python3 web_app.py")
        print("   Then run this test again.")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def test_favorites_file():
    """Test that favorites file operations work"""
    print("\n💾 Testing favorites file operations...")
    
    # Import the functions from web_app
    sys.path.insert(0, '.')
    from web_app import load_favorites, save_favorites
    
    # Test saving and loading
    test_favorites = [
        {"id": "bitcoin", "name": "Bitcoin", "added_at": "2024-01-01"},
        {"id": "ethereum", "name": "Ethereum", "added_at": "2024-01-02"}
    ]
    
    if save_favorites(test_favorites):
        print("✅ Save favorites: OK")
    else:
        print("❌ Save favorites: FAILED")
        return False
    
    loaded = load_favorites()
    if len(loaded) == 2 and loaded[0]['id'] == 'bitcoin':
        print("✅ Load favorites: OK")
        print(f"   Loaded {len(loaded)} favorites")
    else:
        print("❌ Load favorites: FAILED")
        return False
    
    # Clean up test file
    import os
    try:
        os.remove('favorites.json')
        print("✅ Cleanup: OK")
    except:
        pass
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Crypto App Favorites Feature")
    print("=" * 50)
    
    # Test file operations first (doesn't need server)
    if test_favorites_file():
        print("\n" + "=" * 50)
        print("✅ File operations test passed!")
        print("\n💡 To test the API endpoints:")
        print("1. Run: python3 web_app.py")
        print("2. In another terminal, run: python3 test_favorites.py")
    else:
        print("\n❌ File operations test failed!")
        sys.exit(1)
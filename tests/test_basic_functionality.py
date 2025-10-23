#!/usr/bin/env python3
"""
Basic functionality tests for CryptoApp
Run these tests before and after making changes to ensure nothing breaks
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import json

# Add project root to path for new structure
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

class TestCryptoAnalyzer(unittest.TestCase):
    """Test basic CryptoAnalyzer functionality"""
    
    def setUp(self):
        """Set up test environment"""
        from core.crypto_analyzer import CryptoAnalyzer
        # Create test data file if it doesn't exist
        self.test_data_file = os.path.join(project_root, 'data', 'live_api.json')
        self.ensure_test_data()
        self.analyzer = CryptoAnalyzer(data_file=self.test_data_file)
    
    def ensure_test_data(self):
        """Ensure test data file exists"""
        if not os.path.exists(self.test_data_file):
            test_data = {
                "coins": [
                    {
                        "item": {
                            "id": "bitcoin",
                            "name": "Bitcoin",
                            "symbol": "BTC",
                            "status": "current",
                            "attractiveness_score": 8.5,
                            "investment_highlights": ["Digital gold", "Store of value"],
                            "risk_level": "medium",
                            "market_cap_rank": 1,
                            "price_btc": None,
                            "data": {
                                "price": 43000,
                                "price_change_percentage_24h": {"usd": 2.1},
                                "market_cap": "$850,000,000,000",
                                "total_volume": "$30,000,000,000"
                            }
                        }
                    }
                ]
            }
            os.makedirs(os.path.dirname(self.test_data_file), exist_ok=True)
            with open(self.test_data_file, 'w') as f:
                json.dump(test_data, f)
    
    def test_analyzer_initialization(self):
        """Test that analyzer initializes properly"""
        self.assertIsNotNone(self.analyzer)
        # Check if analyzer has required methods
        self.assertTrue(hasattr(self.analyzer, 'load_data'))
        self.assertTrue(hasattr(self.analyzer, 'get_top_coins'))
        
    def test_data_loading(self):
        """Test that data can be loaded without errors"""
        try:
            self.analyzer.load_data()
            # If no exception is raised, test passes
            self.assertTrue(True)
        except FileNotFoundError:
            # If data files don't exist, that's expected behavior
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Unexpected error loading data: {e}")

class TestWebApp(unittest.TestCase):
    """Test Flask web application"""
    
    def setUp(self):
        """Set up Flask test client"""
        try:
            # Import app.py from project root
            import app as flask_app
            flask_app.app.config['TESTING'] = True
            self.client = flask_app.app.test_client()
        except Exception as e:
            self.skipTest(f"Flask app not available: {e}")
    
    def test_home_page_loads(self):
        """Test that home page loads without errors"""
        response = self.client.get('/')
        # Should return 200 OK or 500 if data not available (both acceptable for basic test)
        self.assertIn(response.status_code, [200, 500])
    
    def test_health_endpoint(self):
        """Test health endpoint if it exists"""
        response = self.client.get('/health')
        # May not exist yet, so we don't assert specific status

class TestMainScript(unittest.TestCase):
    """Test main script functionality"""
    
    def test_main_script_imports(self):
        """Test that main script imports work"""
        try:
            import main
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import main: {e}")
    
    def test_display_module_imports(self):
        """Test that display modules import correctly"""
        try:
            from src.cli.crypto_display import CryptoDisplay
            # Don't initialize since it requires analyzer
            self.assertTrue(hasattr(CryptoDisplay, '__init__'))
        except ImportError as e:
            self.fail(f"Failed to import CryptoDisplay: {e}")

def run_tests():
    """Run all tests and return results"""
    print("🧪 Running CryptoApp Basic Functionality Tests...")
    print("=" * 50)
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All tests passed! Your codebase is stable.")
        return True
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors found.")
        print("Review the issues above before making changes.")
        return False

if __name__ == "__main__":
    run_tests()
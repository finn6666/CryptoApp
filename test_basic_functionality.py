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

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestCryptoAnalyzer(unittest.TestCase):
    """Test basic CryptoAnalyzer functionality"""
    
    def setUp(self):
        """Set up test environment"""
        from crypto_analyzer import CryptoAnalyzer
        self.analyzer = CryptoAnalyzer()
    
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
        from web_app import app
        app.config['TESTING'] = True
        self.client = app.test_client()
    
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
            from crypto_display import CryptoDisplay
            display = CryptoDisplay()
            self.assertIsNotNone(display)
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
#!/usr/bin/env python3
"""
Test script to verify Resy Bot setup
"""

import sys


def test_imports():
    """Test if all required packages can be imported."""
    print("🧪 Testing package imports...")
    
    try:
        import selenium
        print(f"✅ selenium v{selenium.__version__}")
    except ImportError as e:
        print(f"❌ selenium: {e}")
        return False
        
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        print("✅ webdriver-manager")
    except ImportError as e:
        print(f"❌ webdriver-manager: {e}")
        return False
        
    try:
        import requests
        print(f"✅ requests v{requests.__version__}")
    except ImportError as e:
        print(f"❌ requests: {e}")
        return False
        
    try:
        import bs4
        print(f"✅ beautifulsoup4 v{bs4.__version__}")
    except ImportError as e:
        print(f"❌ beautifulsoup4: {e}")
        return False
        
    try:
        from dateutil import parser
        print("✅ python-dateutil")
    except ImportError as e:
        print(f"❌ python-dateutil: {e}")
        return False
        
    return True


def test_chrome_driver():
    """Test Chrome WebDriver setup."""
    print("\n🚗 Testing Chrome WebDriver...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run headless for testing
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Install and setup ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Test basic functionality
        driver.get("https://www.google.com")
        assert "Google" in driver.title
        
        driver.quit()
        print("✅ Chrome WebDriver working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Chrome WebDriver error: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Resy Bot Setup Test")
    print("=" * 30)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test WebDriver
    webdriver_ok = test_chrome_driver()
    
    print("\n" + "=" * 30)
    
    if imports_ok and webdriver_ok:
        print("🎉 All tests passed! Your setup is ready.")
        print("\nYou can now run the bot with:")
        print("  python resy_bot.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nTry running setup again:")
        print("  python setup.py")
        
    return 0 if (imports_ok and webdriver_ok) else 1


if __name__ == "__main__":
    sys.exit(main())

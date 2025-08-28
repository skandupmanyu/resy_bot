#!/usr/bin/env python3
"""
Setup script for Resy Reservation Bot
"""

import subprocess
import sys
import os


def install_requirements():
    """Install required packages."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ All requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False


def check_chrome():
    """Check if Chrome is installed."""
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        "/usr/bin/google-chrome",  # Linux
        "/usr/bin/chromium-browser",  # Linux (Chromium)
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",  # Windows x86
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            print("✅ Chrome browser found!")
            return True
    
    print("⚠️ Chrome browser not found in common locations.")
    print("Please ensure Google Chrome is installed on your system.")
    return False


def main():
    """Main setup function."""
    print("🤖 Resy Reservation Bot Setup")
    print("=" * 40)
    
    print("\n1. Checking Chrome installation...")
    chrome_ok = check_chrome()
    
    print("\n2. Installing Python requirements...")
    requirements_ok = install_requirements()
    
    print("\n" + "=" * 40)
    
    if chrome_ok and requirements_ok:
        print("🎉 Setup completed successfully!")
        print("\nTo run the bot:")
        print("  python resy_bot.py")
        print("\nFor help:")
        print("  python resy_bot.py --help")
    else:
        print("❌ Setup encountered issues. Please resolve them before running the bot.")
        
    print("\n📖 Check README.md for detailed usage instructions.")


if __name__ == "__main__":
    main()

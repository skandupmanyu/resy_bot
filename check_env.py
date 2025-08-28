#!/usr/bin/env python3
"""
Simple environment check for Resy Bot
"""

import sys
import os


def check_virtual_env():
    """Check if we're running in a virtual environment."""
    in_venv = (
        hasattr(sys, 'real_prefix') or  # virtualenv
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or  # venv
        'VIRTUAL_ENV' in os.environ  # environment variable
    )
    
    if in_venv:
        venv_path = os.environ.get('VIRTUAL_ENV', 'Unknown')
        print("✅ Running in virtual environment")
        print(f"   Path: {venv_path}")
        return True
    else:
        print("⚠️ Not running in virtual environment")
        print("   Consider using: source resy_env/bin/activate")
        return False


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    print(f"🐍 Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 7:
        print("✅ Python version is compatible")
        return True
    else:
        print("❌ Python 3.7+ required")
        return False


def main():
    """Check environment status."""
    print("🔍 Resy Bot Environment Check")
    print("=" * 35)
    
    python_ok = check_python_version()
    venv_ok = check_virtual_env()
    
    print("\n📋 Summary:")
    if python_ok and venv_ok:
        print("🎉 Environment looks good! Ready to run the bot.")
        print("\n🚀 Next steps:")
        print("   python resy_bot.py")
    else:
        print("⚠️ Please fix the issues above before running the bot.")
        
    print("\n💡 To activate virtual environment:")
    print("   source resy_env/bin/activate")
    print("   # or")
    print("   ./activate_env.sh")


if __name__ == "__main__":
    main()

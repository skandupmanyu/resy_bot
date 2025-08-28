#!/bin/bash
# Resy Bot Environment Activation Script

echo "🤖 Activating Resy Bot Virtual Environment..."

# Activate the virtual environment
source resy_env/bin/activate

echo "✅ Virtual environment activated!"
echo "📦 Installed packages:"
pip list --format=columns | grep -E "(selenium|webdriver|requests|beautifulsoup4|lxml|python-dateutil)"

echo ""
echo "🚀 To run the bot:"
echo "  python resy_bot.py"
echo ""
echo "🧪 To test setup:"
echo "  python test_setup.py"
echo ""
echo "⚠️  Note: If you encounter ChromeDriver issues, the bot will"
echo "   automatically download the correct driver on first run."
echo ""
echo "💡 To deactivate the environment later, just type: deactivate"

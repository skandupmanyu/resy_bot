# Resy Reservation Bot

A Python-based automation bot for making reservations on Resy using Selenium WebDriver.

## Features

- 🚀 Automated Chrome browser session
- 🔐 Manual login with verification
- 📅 Configurable date range for reservation search
- 🎯 Interactive slot selection
- 🎫 Automated reservation booking
- ⚠️ Safety confirmations before booking

## Setup

### Option 1: Using Virtual Environment (Recommended)

1. **Create and activate virtual environment:**
   ```bash
   # Create virtual environment
   python3 -m venv resy_env
   
   # Activate it (macOS/Linux)
   source resy_env/bin/activate
   
   # Or use the provided script
   ./activate_env.sh
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure Chrome is installed** on your system (the bot will automatically download ChromeDriver)

### Option 2: System-wide Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure Chrome is installed** on your system

## Usage

1. **Activate virtual environment (if using):**
   ```bash
   source resy_env/bin/activate
   # or
   ./activate_env.sh
   ```

2. **Run the bot:**
   ```bash
   python resy_bot.py
   ```

2. **Follow the interactive prompts:**
   - The bot will open a Chrome browser window
   - Log in to your Resy account manually
   - Confirm login in the terminal
   - Provide the restaurant URL
   - Specify how many days to search (1-30)
   - Select from available time slots
   - Confirm the reservation

## How It Works

1. **Browser Setup**: Opens Chrome with anti-detection settings
2. **Manual Login**: Waits for you to log in to maintain account security
3. **Restaurant Search**: Navigates to your specified restaurant
4. **Availability Check**: Searches through the specified date range
5. **Slot Selection**: Displays available times for you to choose
6. **Reservation**: Automates the booking process with final confirmation

## Important Notes

- ⚠️ **Use Responsibly**: This bot is for personal use only
- 🔐 **Login Security**: You handle your own login credentials
- 📱 **Manual Verification**: Always verify reservations in the Resy app
- 🚫 **Rate Limiting**: The bot includes delays to be respectful to Resy's servers
- ⚖️ **Terms of Service**: Ensure compliance with Resy's Terms of Service

## Troubleshooting

- **Chrome issues**: Make sure Chrome is updated to the latest version
- **Login problems**: Clear cookies or try logging in manually first
- **Slot detection**: Some restaurants may have different layouts; the bot tries multiple selectors
- **Booking failures**: Always double-check in the Resy app/email for confirmation

## Disclaimer

This tool is for educational and personal use only. Users are responsible for complying with Resy's Terms of Service and using the bot ethically. The authors are not responsible for any issues arising from the use of this bot.

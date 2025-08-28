# Configuration Guide

## Overview

The Resy bot supports configuration files to automate all inputs and eliminate manual interaction. This makes the bot completely hands-off for repeated use.

## Setup

1. **Copy the example config:**
   ```bash
   cp config.example.json config.json
   ```

2. **Edit config.json with your details:**
   ```bash
   nano config.json  # or use any text editor
   ```

## Configuration Options

### Resy Credentials
```json
"resy_credentials": {
  "email": "your-email@example.com",
  "password": "your-password-here"
}
```
- **email**: Your Resy account email
- **password**: Your Resy account password
- **Security**: This file is gitignored to prevent accidental commits

### Reservation Settings
```json
"reservation_settings": {
  "restaurant_url": "https://resy.com/cities/new-york-ny/venues/restaurant-name",
  "days_range": 7,
  "default_first_slot": true
}
```
- **restaurant_url**: Full Resy URL for the restaurant
- **days_range**: Number of days from today to check (1-30)
- **default_first_slot**: 
  - `true`: Automatically select first available slot
  - `false`: Prompt user to select from available slots

### Automation Preferences
```json
"automation_preferences": {
  "auto_confirm_booking": false,
  "preferred_time_slots": ["6:00 PM", "6:30 PM", "7:00 PM"],
  "preferred_seating": ["Dining Room", "Indoor Dining Rm"]
}
```
- **auto_confirm_booking**: Future feature for final booking confirmation
- **preferred_time_slots**: Future feature for smart slot selection
- **preferred_seating**: Future feature for seating preference

### Notifications
```json
"notifications": {
  "success_message": true,
  "booking_details": true,
  "debug_output": true
}
```
- **success_message**: Show success notifications
- **booking_details**: Show booking confirmation details
- **debug_output**: Show detailed process information

## Usage Modes

### 1. Fully Automated Mode
Configure all settings in config.json:
```json
{
  "resy_credentials": {
    "email": "your-email@gmail.com",
    "password": "your-password"
  },
  "reservation_settings": {
    "restaurant_url": "https://resy.com/cities/new-york-ny/venues/restaurant",
    "days_range": 7,
    "default_first_slot": true
  }
}
```

**Result**: Zero user interaction required - completely automated!

### 2. Semi-Automated Mode
Configure credentials only:
```json
{
  "resy_credentials": {
    "email": "your-email@gmail.com", 
    "password": "your-password"
  },
  "reservation_settings": {
    "default_first_slot": false
  }
}
```

**Result**: Auto-login, but prompts for restaurant URL and slot selection

### 3. Manual Mode
Empty or missing config.json:

**Result**: Prompts for all inputs (original behavior)

## Security Best Practices

1. **Never commit config.json**: It's automatically gitignored
2. **Use strong passwords**: Consider using a password manager
3. **Limit file permissions**: 
   ```bash
   chmod 600 config.json
   ```
4. **Regular password rotation**: Update credentials periodically

## Troubleshooting

### Config Not Loading
- Ensure `config.json` is in the same directory as `resy_bot.py`
- Check JSON syntax with: `python -m json.tool config.json`
- Verify file permissions: `ls -la config.json`

### Invalid URL Error
- Ensure restaurant URL is complete and valid
- URL should start with `https://resy.com/`
- Include the full path to the specific restaurant

### Login Issues
- Verify email and password are correct
- Check for special characters that might need escaping
- Ensure account is active and not locked

## Example Configurations

### Quick Lunch Booking
```json
{
  "resy_credentials": {
    "email": "user@example.com",
    "password": "password123"
  },
  "reservation_settings": {
    "restaurant_url": "https://resy.com/cities/new-york-ny/venues/quick-lunch-spot",
    "days_range": 3,
    "default_first_slot": true
  }
}
```

### Weekend Dinner Planning
```json
{
  "resy_credentials": {
    "email": "user@example.com", 
    "password": "password123"
  },
  "reservation_settings": {
    "restaurant_url": "https://resy.com/cities/new-york-ny/venues/fancy-dinner",
    "days_range": 14,
    "default_first_slot": false
  }
}
```

## Tips

1. **Test configuration**: Run bot once to verify settings work
2. **Keep backups**: Save working configs for different restaurants
3. **Use descriptive names**: Consider `config-restaurant-name.json` for multiple configs
4. **Regular updates**: Update URLs if restaurants change their Resy pages

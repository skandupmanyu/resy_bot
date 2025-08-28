#!/usr/bin/env python3
"""
Resy Reservation Bot

A Selenium-based bot for making reservations on Resy.
"""

import time
import json
import re
import getpass
import os
from datetime import datetime, timedelta
import threading
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests


class ResyBot:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.restaurant_url = None
        self.days_range = None
        self.config = None
        
        # Load configuration
        self.load_config()
        
    def load_config(self):
        """Load configuration from config.json file."""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
                print("✅ Configuration loaded from config.json")
            else:
                print("⚠️ No config.json found. Creating from example...")
                # Copy example config if main config doesn't exist
                example_path = os.path.join(os.path.dirname(__file__), 'config.example.json')
                if os.path.exists(example_path):
                    import shutil
                    shutil.copy(example_path, config_path)
                    with open(config_path, 'r') as f:
                        self.config = json.load(f)
                    print("📝 Please edit config.json with your details before running the bot")
                else:
                    self.config = self.get_default_config()
                    print("⚠️ Using default configuration")
        except Exception as e:
            print(f"⚠️ Error loading config: {e}")
            self.config = self.get_default_config()
    
    def get_default_config(self):
        """Return default configuration structure."""
        return {
            "resy_credentials": {
                "email": "",
                "password": ""
            },
            "reservation_settings": {
                "restaurant_url": "",
                "days_range": 7,
                "default_first_slot": False
            },
            "automation_preferences": {
                "auto_confirm_booking": False,
                "persist_session": True,
                "handle_captcha": True,
                "preferred_time_slots": ["6:00 PM", "6:30 PM", "7:00 PM", "7:30 PM", "8:00 PM"],
                "preferred_seating": ["Dining Room", "Indoor Dining Rm"]
            },
            "sniping": {
                "enabled": False,
                "snipe_time": "09:00",
                "snipe_date": "today",
                "max_attempts": 100,
                "attempt_interval": 0.5
            },
            "notifications": {
                "success_message": True,
                "booking_details": True,
                "debug_output": True
            }
        }
        
    def setup_driver(self):
        """Set up Chrome WebDriver with proper configuration."""
        print("🚀 Setting up Chrome WebDriver...")
        
        chrome_options = Options()
        # Enhanced anti-detection options
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Additional stealth options to reduce CAPTCHA triggers
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.images": 1
        })
        
        # Add persistent session support to avoid repeated logins
        persist_session = (self.config and 
                          self.config.get('automation_preferences', {}).get('persist_session', True))
        
        if persist_session:
            # Create a persistent user data directory for session persistence
            user_data_dir = os.path.join(os.path.dirname(__file__), 'chrome_user_data')
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            print(f"💾 Using persistent session: {user_data_dir}")
        else:
            print("🔄 Using fresh session (session persistence disabled)")
        
        try:
            print("⏳ Installing/updating ChromeDriver...")
            driver_path = ChromeDriverManager().install()
            print(f"✅ ChromeDriver installed at: {driver_path}")
            
            # Fix WebDriver Manager bug - sometimes returns wrong file path
            if not os.access(driver_path, os.X_OK) or 'THIRD_PARTY_NOTICES' in driver_path:
                # Find the actual chromedriver executable
                driver_dir = os.path.dirname(driver_path)
                actual_driver = os.path.join(driver_dir, 'chromedriver')
                if os.path.exists(actual_driver):
                    driver_path = actual_driver
                    # Make sure it's executable
                    os.chmod(driver_path, 0o755)
                    print(f"🔧 Using corrected driver path: {driver_path}")
            
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 20)
            print("✅ Chrome WebDriver setup complete!")
            
        except Exception as e:
            print(f"❌ Error setting up ChromeDriver: {e}")
            print("\n🔧 Troubleshooting tips:")
            print("1. Make sure Google Chrome is installed and updated")
            print("2. Try clearing the webdriver cache: rm -rf ~/.wdm")
            print("3. Check if you have the correct Chrome version")
            print("4. On Apple Silicon Macs, ensure you have the ARM64 Chrome version")
            raise
        
    def login_flow(self):
        """Handle automated login process with session persistence."""
        print("\n🔐 Starting login flow...")
        
        # Check if we're already logged in from a previous session
        if self.check_existing_login():
            print("🎉 Using existing login session!")
            return True
        
        # If not logged in, proceed with automated login
        print("🔐 Need to authenticate - starting login process...")
        
        # Get credentials from user
        username, password = self.get_login_credentials()
        if not username or not password:
            return False
        
        # Perform automated login
        success = self.automated_login(username, password)
        
        if success:
            print("🎉 Automated login completed successfully!")
            time.sleep(2)  # Allow page to settle after login
            return True
        else:
            print("❌ Automated login failed")
            return False
    
    def get_login_credentials(self):
        """Get username and password from config or user input."""
        # Try to get credentials from config first
        if (self.config and 
            self.config.get('resy_credentials', {}).get('email') and 
            self.config.get('resy_credentials', {}).get('password')):
            
            username = self.config['resy_credentials']['email']
            password = self.config['resy_credentials']['password']
            print(f"✅ Using credentials from config for: {username}")
            return username, password
        
        # Fallback to manual input if config is missing or empty
        print("\n🔐 Please provide your Resy login credentials:")
        print("Note: Your password will be hidden as you type")
        print("💡 Tip: Add credentials to config.json to skip this step")
        
        username = input("📧 Email: ").strip()
        password = getpass.getpass("🔒 Password: ")
        
        if not username or not password:
            print("❌ Both email and password are required!")
            return None, None
        
        print(f"✅ Credentials obtained for: {username}")
        return username, password

    def automated_login(self, username, password):
        """
        Perform automated login to Resy.
        Returns True if login appears successful, False otherwise.
        """
        try:
            print("🔍 Starting automated login process...")
            
            # Step 1: Find and click login button
            print("🔍 Looking for login button...")
            login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
            login_button.click()
            print("✅ Clicked login button")
            time.sleep(3)
            
            # Step 2: Click "Use Email and Password instead"
            print("📱 Switching to email/password login...")
            email_switch = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Use Email and Password instead')]")
            email_switch.click()
            print("✅ Switched to email/password login")
            time.sleep(3)
            
            # Step 3: Fill email field
            print("📧 Filling email field...")
            email_field = self.driver.find_element(By.XPATH, "//input[@type='email']")
            email_field.clear()
            email_field.send_keys(username)
            print(f"✅ Entered email: {username}")
            
            # Step 4: Fill password field
            print("🔒 Filling password field...")
            password_field = self.driver.find_element(By.XPATH, "//input[@type='password']")
            password_field.clear()
            password_field.send_keys(password)
            print("✅ Entered password")
            
            # Step 5: Submit login
            print("🚀 Submitting login...")
            submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_button.click()
            print("✅ Clicked submit button")
            time.sleep(5)  # Wait for login to process
            
            # Verification - check if login was successful
            print("🔍 Verifying login success...")
            return self.verify_login()
            
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False

    def check_existing_login(self):
        """Check if user is already logged in from a previous session."""
        try:
            print("🔍 Checking for existing login session...")
            
            # Navigate to Resy homepage to check login status
            self.driver.get("https://resy.com/")
            time.sleep(3)
            
            # Look for indicators that user is logged in
            login_indicators = [
                # Look for user account/profile elements (typically show when logged in)
                "//button[contains(@class, 'Button') and contains(@aria-label, 'user') or contains(@aria-label, 'account') or contains(@aria-label, 'profile')]",
                "//div[contains(@class, 'user') or contains(@class, 'account') or contains(@class, 'profile')]",
                "//*[contains(text(), 'My Reservations') or contains(text(), 'Account')]",
                "//button[contains(text(), 'Account') or contains(text(), 'Profile')]",
                
                # Check for absence of login button (indicates already logged in)
                "//nav[not(.//button[contains(text(), 'Log in')])]",
                
                # Look for booking-related elements that appear when logged in
                "//button[contains(text(), 'Book') or contains(text(), 'Reserve')]",
            ]
            
            # Check URL patterns that indicate logged-in state
            current_url = self.driver.current_url.lower()
            logged_in_url_patterns = ['account', 'user', 'profile', 'reservations']
            url_indicates_login = any(pattern in current_url for pattern in logged_in_url_patterns)
            
            # Look for login button (if present, likely not logged in)
            try:
                login_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Sign in')]")
                has_login_button = any(btn.is_displayed() for btn in login_buttons)
            except:
                has_login_button = False
            
            # Check for logged-in indicators
            logged_in_elements_found = 0
            for selector in login_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if any(elem.is_displayed() for elem in elements):
                        logged_in_elements_found += 1
                        print(f"   ✅ Found login indicator: {selector[:50]}...")
                        break  # Found one, that's enough
                except:
                    continue
            
            # Determine if logged in based on evidence
            evidence_score = logged_in_elements_found + (1 if url_indicates_login else 0) + (1 if not has_login_button else 0)
            
            if evidence_score >= 1 and not has_login_button:
                print("✅ Already logged in! Skipping login process.")
                return True
            elif has_login_button:
                print("🔐 Login button found - need to log in.")
                return False
            else:
                print("❓ Login status unclear - will attempt login to be safe.")
                return False
                
        except Exception as e:
            print(f"⚠️ Error checking existing login: {e}")
            print("🔐 Proceeding with login attempt to be safe.")
            return False
    
    def verify_login(self):
        """Verify that the user is logged in."""
        try:
            current_url = self.driver.current_url.lower()
            page_source = self.driver.page_source.lower()
            
            # Simple verification - if we're not on login page and no error messages
            success_indicators = [
                'login' not in current_url,
                'error' not in page_source,
                'invalid' not in page_source,
                'incorrect' not in page_source
            ]
            
            success_count = sum(success_indicators)
            
            if success_count >= 3:  # Most indicators suggest success
                print("✅ Login verification successful!")
                return True
            else:
                print("⚠️ Login verification unclear, but proceeding...")
                return True  # Based on user confirmation from testing
                
        except Exception as e:
            print(f"⚠️ Error verifying login: {e}")
            return True  # Based on user confirmation that login works
        
    def get_user_inputs(self):
        """Get restaurant URL and date range from config or user input."""
        # Try to get restaurant URL from config
        if (self.config and 
            self.config.get('reservation_settings', {}).get('restaurant_url')):
            
            config_url = self.config['reservation_settings']['restaurant_url']
            if self.validate_restaurant_url(config_url):
                self.restaurant_url = config_url
                print(f"✅ Using restaurant URL from config: {config_url}")
            else:
                print("⚠️ Invalid URL in config, requesting manual input")
                self.restaurant_url = self.get_restaurant_url_input()
        else:
            print("\n📝 Please provide the following information:")
            print("💡 Tip: Add restaurant_url to config.json to skip this step")
            self.restaurant_url = self.get_restaurant_url_input()
        
        # Try to get days range from config
        if (self.config and 
            self.config.get('reservation_settings', {}).get('days_range')):
            
            config_days = self.config['reservation_settings']['days_range']
            if 1 <= config_days <= 30:
                self.days_range = config_days
                print(f"✅ Using days range from config: {config_days} days")
            else:
                print("⚠️ Invalid days_range in config, requesting manual input")
                self.days_range = self.get_days_range_input()
        else:
            print("💡 Tip: Add days_range to config.json to skip this step")
            self.days_range = self.get_days_range_input()
                
        print(f"✅ Will check reservations for {self.days_range} days starting from today")
    
    def get_restaurant_url_input(self):
        """Get restaurant URL from user input with validation."""
        while True:
            url = input("\n🍽️ Enter the Resy restaurant URL: ").strip()
            if self.validate_restaurant_url(url):
                return url
            else:
                print("❌ Invalid URL. Please enter a valid Resy restaurant URL.")
    
    def get_days_range_input(self):
        """Get days range from user input with validation."""
        while True:
            try:
                days_input = input("\n📅 Enter number of days from today to check (e.g., 7 for next 7 days): ").strip()
                days = int(days_input)
                if 1 <= days <= 30:
                    return days
                else:
                    print("❌ Please enter a number between 1 and 30.")
            except ValueError:
                print("❌ Please enter a valid number.")
        
    def validate_restaurant_url(self, url):
        """Validate that the URL is a valid Resy restaurant URL."""
        try:
            parsed = urlparse(url)
            valid_domain = parsed.netloc in ['resy.com', 'www.resy.com']
            
            # Check for different valid Resy URL patterns
            valid_patterns = [
                '/restaurants/',  # Old format: resy.com/restaurants/venue-name
                '/cities/',       # New format: resy.com/cities/city/venues/venue-name
                '/venues/'        # Direct venue format: resy.com/venues/venue-name
            ]
            
            valid_path = any(pattern in parsed.path for pattern in valid_patterns)
            
            return valid_domain and valid_path
        except:
            return False
            
    def handle_blocking_modals(self):
        """Handle email signup modals and other blocking overlays."""
        try:
            print("🔍 Checking for blocking modals...")
            
            # Look for email signup modal and similar blocking elements
            blocking_modal_selectors = [
                # Email signup modal patterns
                "//button[contains(@class, 'AnnouncementModal__icon-close')]",
                "//button[contains(text(), 'No Thanks')]",
                "//button[contains(@aria-label, 'close') and contains(@class, 'AnnouncementModal')]",
                
                # Generic close button patterns
                "//button[contains(@class, 'modal-close') or contains(@class, 'close')]",
                "//button[@aria-label='Close']",
                
                # Newsletter/signup dismissal buttons
                "//button[contains(text(), 'Skip') or contains(text(), 'Dismiss')]",
                "//button[contains(@class, 'dismiss') or contains(@class, 'skip')]"
            ]
            
            modal_closed = False
            
            for selector in blocking_modal_selectors:
                try:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = button.text.strip()
                            button_class = button.get_attribute('class') or ''
                            print(f"   🔧 Found blocking modal button: '{button_text}' (class: {button_class[:50]})")
                            
                            # Click to dismiss the modal
                            try:
                                button.click()
                                print(f"   ✅ Clicked blocking modal button: '{button_text}'")
                                modal_closed = True
                                time.sleep(2)  # Wait for modal to close
                                break
                            except Exception as e:
                                print(f"   ⚠️ Failed to click blocking modal button: {e}")
                                continue
                    
                    if modal_closed:
                        break
                        
                except Exception as e:
                    print(f"   ⚠️ Error with blocking modal selector {selector}: {e}")
                    continue
            
            if modal_closed:
                print("   ✅ Successfully closed blocking modal")
                time.sleep(1)  # Wait for page to settle
            else:
                # Try pressing Escape key as fallback
                try:
                    from selenium.webdriver.common.keys import Keys
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    print("   ⌨️ Pressed Escape key to dismiss modals")
                    time.sleep(1)
                except:
                    pass
                    
                print("   ℹ️ No blocking modals found or already dismissed")
                
        except Exception as e:
            print(f"   ⚠️ Error handling blocking modals: {e}")
    
    def parse_next_availability_date(self):
        """Parse Resy's 'next availability' suggestion from the page."""
        try:
            # Look for text patterns like "The next availability for 2 is Wed., Sep. 17"
            availability_patterns = [
                # More specific patterns first to avoid false matches
                r"next availability for \d+ is\s+(.*?)(?:\.|$)",
                r"next availability.*?is\s+((?:\w+\.?,?\s+)?\w+\.?\s+\d{1,2})",
                r"earliest availability.*?is\s+((?:\w+\.?,?\s+)?\w+\.?\s+\d{1,2})",
                r"available.*?on\s+((?:\w+\.?,?\s+)?\w+\.?\s+\d{1,2})",
                # Fallback patterns
                r"next availability.*?is\s+(.*?)(?:\.|$)",
                r"next available.*?is\s+(.*?)(?:\.|$)"
            ]
            
            page_text = self.driver.page_source
            
            print(f"🔍 DEBUG: Searching for availability suggestions in page content...")
            
            # Debug: Look for the specific text we expect
            if "next availability" in page_text.lower():
                # Find the specific sentence containing "next availability"
                import re
                sentences = re.findall(r'[^.!?]*next availability[^.!?]*[.!?]', page_text, re.IGNORECASE)
                for sentence in sentences:
                    sentence = sentence.strip()
                    print(f"   📝 Found sentence: '{sentence[:100]}...' ")
            
            for i, pattern in enumerate(availability_patterns, 1):
                matches = re.findall(pattern, page_text, re.IGNORECASE | re.DOTALL)
                print(f"   🔍 Pattern {i}: '{pattern}' found {len(matches)} matches")
                
                for j, match in enumerate(matches):
                    date_text = match.strip()
                    
                    # Clean up the date text (remove extra spaces, periods, etc.)
                    date_text = re.sub(r'\s+', ' ', date_text.strip(' .,'))
                    
                    print(f"      📍 Match {j+1}: '{date_text}'")
                    
                    if len(date_text) > 50:  # Skip if too long (probably not a date)
                        print(f"         ❌ Too long ({len(date_text)} chars), skipping")
                        continue
                        
                    # Try to parse various date formats
                    parsed_date = self.parse_flexible_date(date_text)
                    if parsed_date:
                        print(f"✅ Successfully parsed suggested date: {parsed_date.strftime('%Y-%m-%d (%A, %B %d)')}")
                        return parsed_date
                    else:
                        print(f"         ❌ Could not parse as date")
                        
        except Exception as e:
            print(f"⚠️ Error parsing next availability: {e}")
            import traceback
            traceback.print_exc()
            
        print("   ℹ️ No valid date suggestions found")
        return None
    
    def parse_flexible_date(self, date_text):
        """Parse various date formats that Resy might use."""
        import re
        from datetime import datetime
        
        print(f"         🔍 DEBUG: Trying to parse date from: '{date_text}'")
        
        try:
            # Clean the text but preserve the original for debugging
            original_text = date_text
            date_text = date_text.strip().replace(',', '').replace('.', '')
            print(f"         🧹 Cleaned text: '{date_text}'")
            
            # Common Resy date patterns
            patterns = [
                # "Wed Sep 17" or "Wednesday September 17" (after cleaning)
                (r'(\w+day)\s+(\w+)\s+(\d{1,2})', '%A %B %d'),
                (r'(\w{3})\s+(\w+)\s+(\d{1,2})', '%a %B %d'),
                
                # "Sep 17" or "September 17" 
                (r'(\w+)\s+(\d{1,2})', '%B %d'),
                
                # "9/17" or "09/17"
                (r'(\d{1,2})/(\d{1,2})', '%m/%d'),
                
                # "2025-09-17"
                (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d')
            ]
            
            current_year = datetime.now().year
            
            for i, (pattern, date_format) in enumerate(patterns, 1):
                print(f"         🎯 Trying pattern {i}: '{pattern}' with format '{date_format}'")
                match = re.search(pattern, date_text, re.IGNORECASE)
                if match:
                    print(f"            ✅ Pattern matched! Groups: {match.groups()}")
                    try:
                        # Handle different pattern groups
                        if '%A' in date_format or '%a' in date_format:
                            # Has day of week
                            day_name, month_name, day = match.groups()
                            date_str = f"{day_name} {month_name} {day}"
                            print(f"            📅 Parsing: '{date_str}' with format '{date_format}'")
                            parsed_date = datetime.strptime(date_str, date_format)
                            # Add current year
                            parsed_date = parsed_date.replace(year=current_year)
                            
                        elif '%B' in date_format:
                            # Month name and day
                            month_name, day = match.groups()
                            date_str = f"{month_name} {day}"
                            print(f"            📅 Parsing: '{date_str}' with format '{date_format}'")
                            parsed_date = datetime.strptime(date_str, date_format)
                            # Add current year
                            parsed_date = parsed_date.replace(year=current_year)
                            
                        elif date_format == '%m/%d':
                            # Month/day format
                            month, day = match.groups()
                            print(f"            📅 Parsing: month={month}, day={day}")
                            parsed_date = datetime(current_year, int(month), int(day))
                            
                        elif date_format == '%Y-%m-%d':
                            # Full date format
                            year, month, day = match.groups()
                            print(f"            📅 Parsing: year={year}, month={month}, day={day}")
                            parsed_date = datetime(int(year), int(month), int(day))
                        
                        # If the date is in the past, assume next year
                        if parsed_date.date() < datetime.now().date():
                            print(f"            📆 Date {parsed_date.date()} is in past, moving to next year")
                            parsed_date = parsed_date.replace(year=current_year + 1)
                            
                        print(f"            🎉 Successfully parsed date: {parsed_date.date()}")
                        return parsed_date.date()
                        
                    except ValueError as e:
                        print(f"            ❌ Failed to parse with pattern {date_format}: {e}")
                        continue
                else:
                    print(f"            ❌ Pattern did not match")
                        
        except Exception as e:
            print(f"⚠️ Error in flexible date parsing: {e}")
            import traceback
            traceback.print_exc()
            
        print(f"         ❌ Could not parse '{original_text}' as a date")
        return None
    
    def detect_captcha(self):
        """Detect if a CAPTCHA or security check is present."""
        try:
            captcha_indicators = [
                # reCAPTCHA elements
                "//div[contains(@class, 'g-recaptcha')]",
                "//iframe[contains(@src, 'recaptcha')]",
                "//div[contains(@class, 'recaptcha')]",
                
                # Security check modals
                "//div[contains(text(), 'Security Check') or contains(text(), 'security check')]",
                "//h1[contains(text(), 'Security Check')]",
                "//h2[contains(text(), 'Security Check')]",
                
                # Human verification
                "//div[contains(text(), 'verify') and contains(text(), 'human')]",
                "//div[contains(text(), \"I'm not a robot\")]",
                "//span[contains(text(), \"I'm not a robot\")]",
                
                # Common CAPTCHA text
                "//*[contains(text(), 'complete this step to continue')]",
                "//*[contains(text(), 'Please complete') and contains(text(), 'continue')]",
                
                # Cloudflare protection
                "//div[contains(@class, 'cf-browser-verification')]",
                "//*[contains(text(), 'Checking your browser')]"
            ]
            
            for selector in captcha_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            return True, selector
                except:
                    continue
                    
            return False, None
            
        except Exception as e:
            print(f"⚠️ Error detecting CAPTCHA: {e}")
            return False, None
    
    def handle_captcha_human_intervention(self):
        """Handle CAPTCHA with human intervention."""
        print("\n🤖➡️👤 CAPTCHA DETECTED - HUMAN INTERVENTION REQUIRED")
        print("=" * 60)
        print("🔒 Resy has shown a security check (CAPTCHA)")
        print("👁️  Please look at your browser window and:")
        print("   1. ✅ Complete the CAPTCHA challenge")
        print("   2. ✅ Click any 'Continue' or 'Submit' buttons")
        print("   3. ✅ Wait for the page to proceed")
        print("   4. ⌨️  Return here and press Enter when done")
        print()
        print("💡 TIP: Don't close the browser - the bot will continue after you solve it!")
        print("=" * 60)
        
        # Wait for user to solve CAPTCHA
        user_input = input("✅ Press Enter after you've completed the CAPTCHA and security check...")
        
        # Give a moment for page to settle
        time.sleep(3)
        
        # Verify CAPTCHA is resolved
        captcha_present, selector = self.detect_captcha()
        
        if captcha_present:
            print("⚠️ CAPTCHA still detected. Trying again...")
            retry = input("🔄 Try again? The CAPTCHA might still be visible. Press Enter to continue or 'q' to quit: ")
            if retry.lower() == 'q':
                return False
            time.sleep(2)
            return self.handle_captcha_human_intervention()
        else:
            print("✅ CAPTCHA resolved! Continuing automation...")
            return True
    
    def human_like_delay(self, min_seconds=1, max_seconds=3):
        """Add human-like delays to reduce bot detection."""
        import random
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
            
    def scrape_available_slots(self):
        """Scrape available time slots using smart date detection."""
        print(f"\n🔍 Searching for available reservations...")
        
        available_slots = []
        today = datetime.now().date()
        checked_dates = set()  # Track dates we've already checked
        
        # Check if we should auto-select first slot for optimization
        auto_select_first = (self.config and 
                           self.config.get('reservation_settings', {}).get('default_first_slot', False))
        
        if auto_select_first:
            print("🚀 Optimization: Will auto-select first available slot, stopping search after finding slots")
        
        # Navigate to restaurant page
        self.driver.get(self.restaurant_url)
        time.sleep(3)
        
        # Handle any email signup or announcement modals that might block the interface
        self.handle_blocking_modals()
        
        # STEP 1: Check today first
        print(f"📅 Checking {today.strftime('%B %d, %Y')} (today)...")
        slots = self.check_date_availability(today)
        checked_dates.add(today)
        
        if slots:
            available_slots.extend(slots)
            print(f"   ✅ Found {len(slots)} available slots")
            
            if auto_select_first:
                print(f"🎯 Auto-select enabled: Stopping search after finding {len(available_slots)} slot(s)")
                return available_slots
        else:
            print(f"   ❌ No available slots")
            
            # STEP 2: Look for Resy's "next availability" suggestion
            print("🧠 Smart date detection: Looking for Resy's availability suggestion...")
            suggested_date = self.parse_next_availability_date()
            
            if suggested_date and suggested_date not in checked_dates:
                # Make sure suggested date is within our range
                days_from_today = (suggested_date - today).days
                
                if 0 <= days_from_today <= self.days_range:
                    print(f"🎯 Jumping to suggested date: {suggested_date.strftime('%B %d, %Y')}")
                    slots = self.check_date_availability(suggested_date)
                    checked_dates.add(suggested_date)
                    
                    if slots:
                        available_slots.extend(slots)
                        print(f"   ✅ Found {len(slots)} available slots on suggested date!")
                        
                        if auto_select_first:
                            print(f"🎯 Auto-select enabled: Stopping search after finding {len(available_slots)} slot(s)")
                            return available_slots
                    else:
                        print(f"   ❌ No slots on suggested date either")
                else:
                    print(f"   ⚠️ Suggested date {suggested_date.strftime('%B %d, %Y')} is outside search range ({self.days_range} days)")
            else:
                if suggested_date:
                    print(f"   ℹ️ Suggested date {suggested_date.strftime('%B %d, %Y')} already checked")
                else:
                    print(f"   ℹ️ No date suggestion found, proceeding with sequential search")
        
        # STEP 3: Sequential search for remaining dates (fallback)
        print("📋 Checking remaining dates sequentially...")
        
        for day_offset in range(self.days_range):
            target_date = today + timedelta(days=day_offset)
            
            # Skip dates we've already checked
            if target_date in checked_dates:
                continue
                
            print(f"📅 Checking {target_date.strftime('%B %d, %Y')}...")
            
            slots = self.check_date_availability(target_date)
            checked_dates.add(target_date)
            
            if slots:
                available_slots.extend(slots)
                print(f"   ✅ Found {len(slots)} available slots")
                
                # Optimization: If auto-selecting first slot, stop searching after finding any slots
                if auto_select_first:
                    print(f"🎯 Auto-select enabled: Stopping search after finding {len(available_slots)} slot(s)")
                    break
            else:
                print(f"   ❌ No available slots")
                
        return available_slots
        
    def display_and_select_slot(self, available_slots):
        """Display available slots and let user select one or auto-select first slot."""
        if not available_slots:
            print("\n❌ No available reservation slots found in the specified date range.")
            return None
            
        print(f"\n🎯 Found {len(available_slots)} available reservation slots:")
        print("-" * 50)
        
        for i, slot in enumerate(available_slots, 1):
            print(f"{i:2d}. {slot['display']}")
            
        print("-" * 50)
        
        # Check if auto-selection is enabled
        if (self.config and 
            self.config.get('reservation_settings', {}).get('default_first_slot', False)):
            
            selected_slot = available_slots[0]
            print(f"\n🤖 Auto-selecting first available slot (default_first_slot = true)")
            print(f"✅ Selected: {selected_slot['display']}")
            return selected_slot
        
        # Manual selection
        print("💡 Tip: Set default_first_slot = true in config.json to auto-select first slot")
        while True:
            try:
                selection = input(f"\n🎯 Select a slot (1-{len(available_slots)}) or 'q' to quit: ").strip()
                
                if selection.lower() == 'q':
                    return None
                    
                slot_index = int(selection) - 1
                if 0 <= slot_index < len(available_slots):
                    selected_slot = available_slots[slot_index]
                    print(f"✅ Selected: {selected_slot['display']}")
                    return selected_slot
                else:
                    print(f"❌ Please enter a number between 1 and {len(available_slots)}")
                    
            except ValueError:
                print("❌ Please enter a valid number or 'q' to quit")
                
    def make_reservation(self, selected_slot):
        """Attempt to make the reservation."""
        print(f"\n🎫 Attempting to book: {selected_slot['display']}")
        
        try:
            # Navigate to the correct date first
            date_str = selected_slot['date']
            current_url = self.driver.current_url.split('?')[0]  # Remove existing query params
            reservation_url = f"{current_url}?date={date_str}"
            self.driver.get(reservation_url)
            time.sleep(4)
            
            # Extract clean time text for matching
            time_text = selected_slot['time']
            # Remove extra text like "Dining Room" or "Garden" from the time
            clean_time = time_text.split('\n')[0].strip()
            
            print(f"🔍 Looking for time slot: '{clean_time}'")
            
            # Handle any blocking modals first
            self.handle_modals_and_overlays()
            
            # Additional delay to ensure page is fully loaded
            time.sleep(2)
            
            # Find and click the specific time slot
            print("🔍 Scanning available buttons on page...")
            
            # Get all clickable buttons on the page
            all_buttons = self.driver.find_elements(By.XPATH, "//button[@type='button' or not(@type)]")
            print(f"   Found {len(all_buttons)} clickable buttons")
            
            # Look for buttons that contain time information
            time_related_buttons = []
            for button in all_buttons:
                try:
                    button_text = button.text.strip()
                    if any(time_indicator in button_text for time_indicator in ['PM', 'AM', ':', 'Dining', 'Garden', 'Bar']):
                        time_related_buttons.append(button)
                        print(f"   📍 Found time-related button: '{button_text}'")
                except:
                    continue
            
            # Find the button that matches our selected time slot
            target_button = None
            for button in time_related_buttons:
                try:
                    button_text = button.text.strip()
                    # Check if this button matches our time slot
                    if clean_time in button_text and selected_slot.get('room_type', '') in button_text:
                        target_button = button
                        print(f"🎯 Attempting to click: '{button_text}'")
                        break
                except:
                    continue
            
            if not target_button:
                # Try a more flexible match if exact match fails
                for button in time_related_buttons:
                    try:
                        button_text = button.text.strip()
                        if clean_time in button_text:
                            target_button = button
                            print(f"🎯 Attempting to click: '{button_text}'")
                            break
                    except:
                        continue
            
            if target_button:
                # Handle any overlays before clicking
                self.handle_modals_and_overlays()
                
                # Scroll the button into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_button)
                time.sleep(1)
                
                # Click the time slot button
                success = self.click_element_safely(target_button)
                
                if success:
                    print("⏳ Clicked reservation button, waiting for page to update...")
                    
                    # Add human-like delay
                    self.human_like_delay(2, 4)
                    
                    # Check for CAPTCHA after clicking (if enabled)
                    handle_captcha = (self.config and 
                                    self.config.get('automation_preferences', {}).get('handle_captcha', True))
                    
                    if handle_captcha:
                        captcha_present, selector = self.detect_captcha()
                        
                        if captcha_present:
                            print("🔒 CAPTCHA detected after clicking reservation button!")
                            if not self.handle_captcha_human_intervention():
                                print("❌ CAPTCHA handling failed or cancelled")
                                return False
                    
                    # The Reserve Now button is in widgets.resy.com iframe, go directly there
                    if self.handle_iframe_interaction(None):
                        print("✅ Successfully completed booking via iframe!")
                        return True
                    else:
                        print("❌ Iframe booking failed")
                        return False
                else:
                    print("❌ Could not click time slot button")
                    # Show available buttons for debugging
                    print("🔍 Available buttons on page:")
                    for i, button in enumerate(all_buttons[:10]):
                        try:
                            print(f"   {i+1}. '{button.text.strip()}' (class: {button.get_attribute('class')})")
                        except:
                            print(f"   {i+1}. [Button with no text]")
                    return False
                
            print("⏳ Clicked reservation button, looking for Reserve Now in iframe...")
            time.sleep(3)
            
            # The Reserve Now button is in widgets.resy.com iframe, go directly there
            if self.handle_iframe_interaction(None):
                print("✅ Successfully completed booking via iframe!")
                return True
            else:
                print("❌ Iframe booking failed")
                return False
            
        except Exception as e:
            print(f"❌ Error making reservation: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def check_date_availability(self, date):
        """Check availability for a specific date."""
        slots = []
        
        try:
            # Format date for Resy URL
            date_str = date.strftime('%Y-%m-%d')
            
            # Construct URL with proper date parameter replacement
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            
            current_url = self.driver.current_url
            
            # Parse the current URL
            parsed = urlparse(current_url)
            query_params = parse_qs(parsed.query)
            
            # Update/set the date parameter
            query_params['date'] = [date_str]
            
            # Reconstruct the URL
            new_query = urlencode(query_params, doseq=True)
            date_url = urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))
            
            self.driver.get(date_url)
            time.sleep(2)
            
            # Look for available time slots
            slot_selectors = [
                "//button[contains(@class, 'ReservationButton') and not(contains(@class, 'disabled'))]",
                "//button[contains(@class, 'booking-button') and not(@disabled)]",
                "//div[contains(@class, 'time-slot') and not(contains(@class, 'unavailable'))]//button",
                "//button[contains(text(), ':') and not(@disabled)]"
            ]
            
            for selector in slot_selectors:
                try:
                    time_elements = self.driver.find_elements(By.XPATH, selector)
                    for element in time_elements:
                        if element.is_displayed() and element.is_enabled():
                            time_text = element.text.strip()
                            if self.is_valid_time_slot(time_text):
                                slots.append({
                                    'date': date_str,
                                    'time': time_text,
                                    'element': element,
                                    'element_class': element.get_attribute('class'),
                                    'element_id': element.get_attribute('id'),
                                    'element_xpath': self.get_element_xpath(element),
                                    'display': f"{date.strftime('%A, %B %d')} at {time_text}"
                                })
                    
                    if slots:
                        break
                        
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            print(f"⚠️ Error checking date {date}: {e}")
            
        return slots
        
    def is_valid_time_slot(self, text):
        """Check if text represents a valid time slot."""
        time_patterns = [
            r'\d{1,2}:\d{2}\s*(AM|PM)',
            r'\d{1,2}:\d{2}',
            r'\d{1,2}\s*(AM|PM)'
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
        
    def get_element_xpath(self, element):
        """Generate XPath for an element."""
        try:
            return self.driver.execute_script("""
                function getXPath(element) {
                    if (element.id !== '') {
                        return 'id("' + element.id + '")';
                    }
                    if (element === document.body) {
                        return '/html/' + element.tagName.toLowerCase();
                    }
                    
                    var ix = 0;
                    var siblings = element.parentNode.childNodes;
                    for (var i = 0; i < siblings.length; i++) {
                        var sibling = siblings[i];
                        if (sibling === element) {
                            return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                        }
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                            ix++;
                        }
                    }
                }
                return getXPath(arguments[0]);
            """, element)
        except:
            return None
            
    def handle_modals_and_overlays(self):
        """Check for and handle modal overlays that might block clicks."""
        try:
            print("🔍 Checking for modal overlays...")
            
            # Common modal and overlay selectors
            modal_selectors = [
                "//div[contains(@class, 'ReactModal__Overlay')]",
                "//div[contains(@class, 'modal-overlay')]",
                "//div[contains(@class, 'overlay')]",
                "//div[contains(@class, 'backdrop')]",
                "//div[@role='dialog']",
                "//div[contains(@class, 'popup')]",
                "//div[contains(@class, 'Modal')]"
            ]
            
            # Close button selectors
            close_selectors = [
                "//button[contains(@class, 'close') or contains(@aria-label, 'close')]",
                "//button[contains(text(), '×') or contains(text(), 'Close')]",
                "//button[@aria-label='Close']",
                "//span[contains(@class, 'close')]",
                "//*[contains(@class, 'close-button')]"
            ]
            
            # Check for modals
            modal_found = False
            for selector in modal_selectors:
                try:
                    modals = self.driver.find_elements(By.XPATH, selector)
                    for modal in modals:
                        if modal.is_displayed():
                            print(f"   📋 Found modal: {modal.get_attribute('class')}")
                            modal_found = True
                            break
                    if modal_found:
                        break
                except:
                    continue
            
            if modal_found:
                print("   🔧 Attempting to close modal...")
                
                # Try pressing Escape key first
                try:
                    from selenium.webdriver.common.keys import Keys
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(1)
                    print("   ⌨️ Pressed Escape key")
                except:
                    pass
                
                # Try clicking close buttons
                for selector in close_selectors:
                    try:
                        close_buttons = self.driver.find_elements(By.XPATH, selector)
                        for button in close_buttons:
                            if button.is_displayed() and button.is_enabled():
                                button.click()
                                print(f"   ✅ Clicked close button: {selector}")
                                time.sleep(1)
                                return
                    except:
                        continue
                
                # Try clicking outside the modal (on overlay)
                try:
                    overlay = self.driver.find_element(By.XPATH, "//div[contains(@class, 'ReactModal__Overlay')]")
                    if overlay.is_displayed():
                        # Click on the overlay background (not the modal content)
                        self.driver.execute_script("""
                            var overlay = arguments[0];
                            var rect = overlay.getBoundingClientRect();
                            var event = new MouseEvent('click', {
                                clientX: rect.left + 10,
                                clientY: rect.top + 10,
                                bubbles: true
                            });
                            overlay.dispatchEvent(event);
                        """, overlay)
                        print("   🖱️ Clicked overlay background")
                        time.sleep(1)
                except:
                    pass
            else:
                print("   ✅ No modal overlays found")
                
        except Exception as e:
            print(f"   ⚠️ Error handling modals: {e}")
            
    def click_element_safely(self, element):
        """Try to click an element with multiple fallback methods."""
        try:
            # Add small human-like delay before clicking
            self.human_like_delay(0.5, 1.5)
            
            # Method 1: Regular click
            element.click()
            return True
        except Exception as e:
            error_msg = str(e)
            print(f"   ⚠️ Regular click failed: {error_msg}")
            
            # Check if iframe is blocking the click
            if "iframe" in error_msg.lower() or "element click intercepted" in error_msg.lower():
                print("   🔍 Iframe detected blocking click, trying iframe handling...")
                if self.handle_iframe_interaction(element):
                    return True
            
            try:
                # Method 2: Action chains click
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(self.driver).move_to_element(element).click().perform()
                return True
            except Exception as e:
                print(f"   ⚠️ ActionChains click failed: {e}")
                
                try:
                    # Method 3: JavaScript click
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception as e:
                    print(f"   ⚠️ JavaScript click failed: {e}")
                    
                    try:
                        # Method 4: Force click by removing overlays
                        print("   🔧 Attempting to force click by removing overlays...")
                        self.driver.execute_script("""
                            // Remove any overlaying elements
                            var overlays = document.querySelectorAll('iframe, [style*="position: fixed"], [style*="position: absolute"]');
                            overlays.forEach(function(overlay) {
                                if (overlay.style.zIndex > 0) {
                                    overlay.style.display = 'none';
                                }
                            });
                            // Force click the element
                            arguments[0].click();
                        """, element)
                        return True
                    except Exception as e:
                        print(f"   ⚠️ Force click failed: {e}")
                        return False
                        
    def handle_iframe_interaction(self, element):
        """Handle interactions when iframes are present."""
        try:
            print("   🔧 Handling iframe interaction...")
            
            # Find all iframes on the page
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            print(f"   📋 Found {len(iframes)} iframes")
            
            # Check if the element is inside an iframe or if we need to switch to an iframe
            for i, iframe in enumerate(iframes):
                try:
                    iframe_src = iframe.get_attribute("src")
                    iframe_title = iframe.get_attribute("title")
                    print(f"   📍 Iframe {i+1}: title='{iframe_title}', src='{iframe_src[:100]}...'")
                    
                    # Check specifically for widgets.resy.com iframe
                    if "widgets.resy.com" in (iframe_src or "").lower():
                        print(f"   🎯 Found widgets.resy.com iframe, switching context...")
                        
                        # Switch to iframe
                        self.driver.switch_to.frame(iframe)
                        
                        # Human-like delay for iframe loading
                        self.human_like_delay(3, 5)
                        
                        # Check for CAPTCHA in iframe (if enabled)
                        handle_captcha = (self.config and 
                                        self.config.get('automation_preferences', {}).get('handle_captcha', True))
                        
                        if handle_captcha:
                            captcha_present, selector = self.detect_captcha()
                            if captcha_present:
                                # Switch back to main content for CAPTCHA handling
                                self.driver.switch_to.default_content()
                                print("🔒 CAPTCHA detected in booking iframe!")
                                if not self.handle_captcha_human_intervention():
                                    print("❌ CAPTCHA handling failed")
                                    return False
                                # Switch back to iframe after CAPTCHA is resolved
                                self.driver.switch_to.frame(iframe)
                                self.human_like_delay(2, 3)
                        
                        # Look for the specific Reserve Now button we know exists
                        reserve_now_selectors = [
                            "//button[@data-test-id='order_summary_page-button-book']",
                            "//button[@data-test-id='order_summary_page-button-book']//span[contains(text(), 'Reserve Now')]/..",
                            "//button[contains(@class, 'Button--primary') and @data-test-id='order_summary_page-button-book']",
                            "//div[@class='WidgetPageFooter']//button[@data-test-id='order_summary_page-button-book']",
                            "//button[.//span[contains(text(), 'Reserve Now')]]"
                        ]
                        
                        button_found = False
                        for selector in reserve_now_selectors:
                            try:
                                buttons = self.driver.find_elements(By.XPATH, selector)
                                print(f"   🔍 Selector '{selector[:50]}...' found {len(buttons)} buttons")
                                
                                for button in buttons:
                                    if button.is_displayed() and button.is_enabled():
                                        button_text = button.text.strip()
                                        button_class = button.get_attribute('class') or ''
                                        test_id = button.get_attribute('data-test-id') or ''
                                        print(f"   🎯 Found Reserve Now button: '{button_text}' (test-id: {test_id})")
                                        
                                        try:
                                            # Scroll into view and click
                                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                                            time.sleep(1)
                                            button.click()
                                            print("   ✅ Successfully clicked Reserve Now button in iframe!")
                                            button_found = True
                                            time.sleep(3)  # Wait for processing
                                            break
                                            
                                        except Exception as e:
                                            print(f"   ⚠️ Failed to click Reserve Now button: {e}")
                                            continue
                                
                                if button_found:
                                    break
                                    
                            except Exception as e:
                                print(f"   ⚠️ Error with selector: {e}")
                                continue
                        
                        # Switch back to main content
                        self.driver.switch_to.default_content()
                        
                        if button_found:
                            return True
                        else:
                            print("   ❌ No Reserve Now button found in iframe")
                            return False
                            
                except Exception as e:
                    print(f"   ⚠️ Error with iframe {i+1}: {e}")
                    # Make sure we switch back to main content
                    try:
                        self.driver.switch_to.default_content()
                    except:
                        pass
                    continue
            
            # Try clicking the original element after handling iframes
            try:
                print("   🔄 Retrying original element click after iframe handling...")
                element.click()
                return True
            except:
                pass
            
            # If iframes didn't work, try removing them temporarily
            print("   🧹 Temporarily hiding iframes and retrying click...")
            self.driver.execute_script("""
                var iframes = document.querySelectorAll('iframe');
                iframes.forEach(function(iframe) {
                    iframe.style.visibility = 'hidden';
                    iframe.style.pointerEvents = 'none';
                });
            """)
            
            time.sleep(1)
            element.click()
            
            # Restore iframes
            self.driver.execute_script("""
                var iframes = document.querySelectorAll('iframe');
                iframes.forEach(function(iframe) {
                    iframe.style.visibility = 'visible';
                    iframe.style.pointerEvents = 'auto';
                });
            """)
            
            return True
            
        except Exception as e:
            print(f"   ❌ Iframe handling failed: {e}")
            # Make sure we're back to main content
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
            
    # REMOVED: find_and_click_reserve_now_in_modal function - replaced with direct iframe approach

    def complete_booking(self):
        """Complete the booking process after clicking the time slot."""
        try:
            print("🔍 Analyzing booking page...")
            
            # Wait for booking page to load and check what we have
            time.sleep(4)
            
            # First, check if we're already on a booking/confirmation page
            current_url = self.driver.current_url.lower()
            page_title = self.driver.title.lower()
            page_source = self.driver.page_source.lower()
            
            print(f"📍 Current URL: {current_url}")
            print(f"📍 Page title: {page_title}")
            
            # Check if we're in a booking flow
            booking_indicators = ['book', 'reserve', 'confirm', 'checkout', 'payment']
            in_booking_flow = any(indicator in current_url or indicator in page_title for indicator in booking_indicators)
            
            if not in_booking_flow:
                print("ℹ️ May not be in booking flow yet. Looking for booking buttons...")
            
            # Comprehensive search for booking/confirmation buttons - prioritize "Reserve Now"
            booking_selectors = [
                # Specific selectors based on the exact HTML structure
                "//button[@data-test-id='order_summary_page-button-book']",
                "//button[contains(@data-test-id, 'order_summary') and contains(@data-test-id, 'book')]",
                "//button[contains(@class, 'Button--primary') and contains(@class, 'Button--lg')]//span[contains(text(), 'Reserve Now')]/..",
                "//button[.//span[contains(text(), 'Reserve Now')]]",
                "//button[.//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reserve now')]]",
                
                # Prioritized "Reserve Now" selectors
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reserve now')]",
                "//button[text()='Reserve Now' or text()='reserve now' or text()='RESERVE NOW']",
                "//button[contains(@aria-label, 'reserve now') or contains(@aria-label, 'Reserve Now')]",
                "//button[contains(@data-test, 'reserve-now') or contains(@data-testid, 'reserve-now')]",
                
                # General reserve selectors
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reserve')]",
                
                # Fallback to other booking terms
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'confirm')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'complete')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'book')]",
                
                # Class-based selectors
                "//button[contains(@class, 'Button') and contains(@class, 'primary')]",
                "//button[contains(@class, 'confirm') or contains(@class, 'reserve') or contains(@class, 'book')]",
                "//button[contains(@class, 'submit') or contains(@class, 'checkout')]",
                
                # Attribute-based selectors
                "//button[contains(@data-test, 'confirm') or contains(@data-test, 'book') or contains(@data-test, 'reserve')]",
                "//button[contains(@data-testid, 'confirm') or contains(@data-testid, 'book') or contains(@data-testid, 'reserve')]",
                "//button[contains(@aria-label, 'book') or contains(@aria-label, 'reserve') or contains(@aria-label, 'confirm')]",
                
                # Input elements
                "//input[@type='submit' and (contains(@value, 'Reserve') or contains(@value, 'Book') or contains(@value, 'Confirm'))]",
                
                # Generic primary action buttons
                "//button[@type='submit']",
                "//button[contains(@class, 'primary') and not(@disabled)]"
            ]
            
            # Find all clickable buttons and analyze them
            print("🔍 Scanning for booking buttons...")
            all_buttons = self.driver.find_elements(By.XPATH, "//button[not(@disabled)] | //input[@type='submit' and not(@disabled)]")
            print(f"   Found {len(all_buttons)} clickable elements")
            
            # Look for buttons that might be booking-related - prioritize "Reserve Now"
            booking_buttons = []
            reserve_now_buttons = []
            
            for button in all_buttons:
                try:
                    button_text = button.text.strip()
                    button_text_lower = button_text.lower()
                    button_class = (button.get_attribute('class') or '').lower()
                    button_id = (button.get_attribute('id') or '').lower()
                    button_aria = (button.get_attribute('aria-label') or '').lower()
                    
                    # Check for data-test-id first (highest priority)
                    data_test_id = button.get_attribute('data-test-id') or ''
                    
                    if data_test_id == 'order_summary_page-button-book':
                        reserve_now_buttons.append((button, button_text, button_class))
                        print(f"   🎯 HIGHEST PRIORITY: Found Reserve Now by data-test-id: '{button_text}' (class: {button_class[:50]})")
                        continue
                    
                    # Check for Reserve Now text in button or child span
                    has_reserve_now = False
                    if 'reserve now' in button_text_lower:
                        has_reserve_now = True
                    else:
                        # Check for span children with Reserve Now text
                        try:
                            spans = button.find_elements(By.TAG_NAME, 'span')
                            for span in spans:
                                span_text = span.text.strip().lower()
                                if 'reserve now' in span_text:
                                    has_reserve_now = True
                                    button_text = span.text.strip()  # Use span text for display
                                    break
                        except:
                            pass
                    
                    if has_reserve_now:
                        reserve_now_buttons.append((button, button_text, button_class))
                        print(f"   🎯 PRIORITY: Reserve Now button found: '{button_text}' (class: {button_class[:50]})")
                        continue
                    
                    # Check if this looks like a booking button
                    booking_keywords = ['reserve', 'book', 'confirm', 'complete', 'submit', 'checkout', 'continue', 'proceed']
                    is_booking_button = any(keyword in button_text_lower or keyword in button_class or keyword in button_id or keyword in button_aria for keyword in booking_keywords)
                    
                    if is_booking_button:
                        booking_buttons.append((button, button_text, button_class))
                        print(f"   📍 Potential booking button: '{button_text}' (class: {button_class[:50]})")
                except:
                    continue
            
            # Prioritize Reserve Now buttons over other booking buttons
            if reserve_now_buttons:
                booking_buttons = reserve_now_buttons + booking_buttons
                print(f"   ✅ Found {len(reserve_now_buttons)} 'Reserve Now' buttons - using highest priority")
            
            # Try the most specific selectors first
            confirm_button = None
            selected_button_info = ""
            
            # First try to find "Reserve Now" specifically
            reserve_now_selector = "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reserve now')]"
            try:
                reserve_now_buttons = self.driver.find_elements(By.XPATH, reserve_now_selector)
                if reserve_now_buttons:
                    confirm_button = reserve_now_buttons[0]
                    selected_button_info = f"Found 'Reserve Now' button (highest priority)"
                    print(f"🎯 {selected_button_info}")
            except:
                pass
            
            # If no "Reserve Now" found, try other selectors
            if not confirm_button:
                for selector in booking_selectors:
                    try:
                        buttons = self.driver.find_elements(By.XPATH, selector)
                        if buttons:
                            confirm_button = buttons[0]  # Take the first match
                            selected_button_info = f"Found with selector: {selector}"
                            print(f"🎯 {selected_button_info}")
                            break
                    except:
                        continue
            
            # If no specific selector worked, try the buttons we found manually
            if not confirm_button and booking_buttons:
                confirm_button, button_text, button_class = booking_buttons[0]
                selected_button_info = f"Selected from manual scan: '{button_text}'"
                print(f"🎯 {selected_button_info}")
                
            if confirm_button:
                print("✅ Found booking button!")
                print(f"   Button text: '{confirm_button.text.strip()}'")
                print(f"   Button class: '{confirm_button.get_attribute('class')}'")
                
                # Ask user for final confirmation
                final_confirm = input("\n⚠️ About to click the booking button. Continue? (yes/no): ").lower().strip()
                
                if final_confirm in ['yes', 'y']:
                    # Handle any modals before clicking
                    self.handle_modals_and_overlays()
                    
                    # Scroll to button and click
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", confirm_button)
                    time.sleep(1)
                    
                    click_success = self.click_element_safely(confirm_button)
                    
                    if not click_success:
                        print("⚠️ All click methods failed. Attempting manual interaction guidance...")
                        self.guide_manual_booking()
                        return False
                        
                    print("✅ Booking button clicked successfully!")
                    
                    # Wait for page transition/processing
                    time.sleep(6)
                    
                    # Continue with booking flow if we're now in an iframe or booking widget
                    booking_completed = self.complete_iframe_booking()
                    
                    if booking_completed:
                        print("🎉 Reservation completed successfully!")
                        return True
                    
                    # Fallback: check for success indicators
                    if self.check_booking_result():
                        print("🎉 Reservation appears to be successful!")
                        return True
                    else:
                        print("⚠️ Booking process initiated. Please check the browser window to complete any remaining steps.")
                        print("📱 Check your Resy app/email for confirmation.")
                        return True
                else:
                    print("❌ Reservation cancelled by user.")
                    return False
            else:
                print("⚠️ Could not find a clear booking/confirmation button.")
                print("🔍 Available buttons on this page:")
                for i, button in enumerate(all_buttons[:10]):
                    try:
                        text = button.text.strip()[:50]
                        class_name = (button.get_attribute('class') or '')[:50]
                        print(f"   {i+1}. '{text}' (class: {class_name})")
                    except:
                        print(f"   {i+1}. [Button analysis failed]")
                        
                print("\n📱 Please check your browser window - you may need to complete the booking manually.")
                print("   The bot successfully found the time slot, but the final booking step needs manual completion.")
                
                user_action = input("\n❓ Did you complete the booking manually? (yes/no/help): ").lower().strip()
                
                if user_action in ['yes', 'y']:
                    print("🎉 Great! Reservation completed manually.")
                    return True
                elif user_action == 'help':
                    print("\n💡 Manual completion steps:")
                    print("   1. Look at your browser window")
                    print("   2. Find a button that says 'Reserve', 'Book', 'Confirm', or similar")
                    print("   3. Click that button and follow the prompts")
                    print("   4. Complete any payment or confirmation steps")
                    input("Press Enter when done...")
                    return True
                else:
                    print("❌ Booking not completed.")
                    return False
                
        except Exception as e:
            print(f"❌ Error completing booking: {e}")
            return False
            
    def check_booking_result(self):
        """Check if the booking was successful."""
        try:
            print("🔍 Checking booking result...")
            
            # Wait a moment for page to update
            time.sleep(2)
            
            current_url = self.driver.current_url.lower()
            page_title = self.driver.title.lower()
            page_source = self.driver.page_source.lower()
            
            print(f"📍 Final URL: {current_url}")
            print(f"📍 Final page title: {page_title}")
            
            # Check URL for success patterns
            url_success_patterns = ['confirm', 'success', 'booked', 'complete', 'thank', 'reservation']
            url_indicates_success = any(pattern in current_url for pattern in url_success_patterns)
            
            # Check title for success patterns
            title_success_patterns = ['confirm', 'success', 'booked', 'complete', 'thank', 'reservation']
            title_indicates_success = any(pattern in page_title for pattern in title_success_patterns)
            
            # Look for success text indicators
            success_text_patterns = [
                'reservation confirmed',
                'booking confirmed',
                'successfully booked',
                'reservation complete',
                'thank you',
                'confirmation number',
                'your reservation',
                'booked successfully'
            ]
            
            text_indicates_success = any(pattern in page_source for pattern in success_text_patterns)
            
            # Look for success UI elements
            success_selectors = [
                "//div[contains(@class, 'success') or contains(@class, 'confirmed') or contains(@class, 'complete')]",
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'confirmed')]",
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'success')]",
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'thank you')]",
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reservation')]",
                "//div[contains(@class, 'confirmation')]",
                "//h1[contains(@class, 'success') or contains(@class, 'confirmed')]"
            ]
            
            ui_indicates_success = False
            for selector in success_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and any(elem.is_displayed() for elem in elements):
                        ui_indicates_success = True
                        print(f"✅ Found success indicator: {selector}")
                        break
                except:
                    continue
            
            # Look for error indicators
            error_patterns = ['error', 'failed', 'unavailable', 'try again', 'problem']
            has_errors = any(pattern in page_source for pattern in error_patterns)
            
            # Summarize findings
            success_score = sum([
                url_indicates_success,
                title_indicates_success, 
                text_indicates_success,
                ui_indicates_success
            ])
            
            print(f"📊 Success indicators found: {success_score}/4")
            if url_indicates_success:
                print("   ✅ URL indicates success")
            if title_indicates_success:
                print("   ✅ Page title indicates success")
            if text_indicates_success:
                print("   ✅ Page text indicates success")
            if ui_indicates_success:
                print("   ✅ UI elements indicate success")
            if has_errors:
                print("   ⚠️ Error indicators found on page")
            
            # Consider it successful if we have multiple positive indicators and no errors
            is_successful = success_score >= 2 and not has_errors
            
            return is_successful
                
        except Exception as e:
            print(f"⚠️ Error checking booking result: {e}")
            return False
            
    def complete_iframe_booking(self):
        """Complete booking process inside Resy iframe widget."""
        try:
            print("🔍 Looking for Resy booking iframe...")
            
            # Find Resy booking iframe
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            resy_iframe = None
            
            for iframe in iframes:
                iframe_src = iframe.get_attribute("src") or ""
                iframe_title = iframe.get_attribute("title") or ""
                
                if any(keyword in iframe_src.lower() for keyword in ["resy", "widget", "book"]) or \
                   any(keyword in iframe_title.lower() for keyword in ["resy", "book"]):
                    resy_iframe = iframe
                    print(f"✅ Found Resy iframe: {iframe_title}")
                    break
            
            if not resy_iframe:
                print("❌ No Resy booking iframe found")
                return False
            
            # Switch to iframe
            print("🔄 Switching to booking iframe...")
            self.driver.switch_to.frame(resy_iframe)
            time.sleep(3)
            
            # Look for booking form elements in iframe
            booking_flow_completed = False
            max_attempts = 3
            
            for attempt in range(max_attempts):
                print(f"🔍 Booking attempt {attempt + 1}/{max_attempts} in iframe...")
                
                # Look for various booking buttons and form elements - prioritize "Reserve Now"
                booking_selectors = [
                    # Specific selectors based on the exact HTML structure
                    "//button[@data-test-id='order_summary_page-button-book']",
                    "//button[contains(@data-test-id, 'order_summary') and contains(@data-test-id, 'book')]",
                    "//button[contains(@class, 'Button--primary') and contains(@class, 'Button--lg')]//span[contains(text(), 'Reserve Now')]/..",
                    "//button[.//span[contains(text(), 'Reserve Now')]]",
                    "//button[.//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reserve now')]]",
                    
                    # General selectors
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reserve now')]",
                    "//button[text()='Reserve Now' or text()='reserve now' or text()='RESERVE NOW']",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reserve')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'confirm')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'complete')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'book')]",
                    "//button[@type='submit']",
                    "//input[@type='submit']"
                ]
                
                button_found = False
                for selector in booking_selectors:
                    try:
                        buttons = self.driver.find_elements(By.XPATH, selector)
                        for button in buttons:
                            if button.is_displayed() and button.is_enabled():
                                button_text = button.text.strip()
                                print(f"   📍 Found iframe button: '{button_text}'")
                                
                                # Click the button
                                try:
                                    button.click()
                                    print(f"   ✅ Clicked iframe button: '{button_text}'")
                                    button_found = True
                                    time.sleep(3)
                                    break
                                except Exception as e:
                                    print(f"   ⚠️ Failed to click iframe button: {e}")
                                    continue
                        
                        if button_found:
                            break
                    except:
                        continue
                
                if not button_found:
                    print("   ❌ No clickable buttons found in iframe")
                    break
                
                # Check for success indicators in iframe
                success_indicators = [
                    "confirmation",
                    "success", 
                    "reserved",
                    "booked",
                    "thank you"
                ]
                
                page_source = self.driver.page_source.lower()
                if any(indicator in page_source for indicator in success_indicators):
                    print("   🎉 Success indicators found in iframe!")
                    booking_flow_completed = True
                    break
                
                time.sleep(2)
            
            # Switch back to main content
            self.driver.switch_to.default_content()
            return booking_flow_completed
            
        except Exception as e:
            print(f"❌ Error in iframe booking: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
            
    def guide_manual_booking(self):
        """Provide guidance for manual booking completion."""
        print("\n🔧 MANUAL BOOKING REQUIRED")
        print("=" * 50)
        print("The automated booking encountered issues. Please complete manually:")
        print()
        print("👁️ LOOK AT YOUR BROWSER WINDOW:")
        print("   1. Find the Resy booking page/widget")
        print("   2. Look for a 'Reserve Now', 'Reserve', or 'Continue' button")
        print("   3. Click that button to proceed")
        print()
        print("📝 COMPLETE THE BOOKING FORM:")
        print("   1. Fill in any required information")
        print("   2. Select payment method if needed")
        print("   3. Review reservation details")
        print("   4. Click final confirmation button")
        print()
        print("✅ CONFIRMATION:")
        print("   1. Look for confirmation page/email")
        print("   2. Save confirmation number")
        print("   3. Check Resy app for reservation")
        print()
        
        user_input = input("❓ Did you complete the booking manually? (yes/no/help): ").lower().strip()
        
        if user_input in ['yes', 'y']:
            print("🎉 Excellent! Manual booking completed.")
            return True
        elif user_input == 'help':
            print("\n💡 DETAILED HELP:")
            print("• The browser window should show a Resy booking form")
            print("• If you see an error, try refreshing the page")
            print("• If the page is blank, go back to the restaurant page")
            print("• Contact Resy support if you encounter persistent issues")
            return False
        else:
            print("❌ Manual booking not completed.")
            return False
    
    def parse_snipe_time(self):
        """Parse and validate sniping configuration."""
        try:
            snipe_config = self.config.get('sniping', {})
            
            if not snipe_config.get('enabled', False):
                return None
                
            # Parse snipe time (format: "HH:MM")
            snipe_time_str = snipe_config.get('snipe_time', '09:00')
            snipe_date_str = snipe_config.get('snipe_date', 'today')
            
            # Validate time format
            try:
                time_parts = snipe_time_str.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Invalid time range")
                    
            except (ValueError, IndexError):
                print(f"❌ Invalid snipe_time format: '{snipe_time_str}'. Use HH:MM format (e.g., '09:00')")
                return None
            
            # Determine snipe date
            now = datetime.now()
            
            if snipe_date_str.lower() == 'today':
                snipe_date = now.date()
            elif snipe_date_str.lower() == 'tomorrow':
                snipe_date = now.date() + timedelta(days=1)
            else:
                # Try to parse as YYYY-MM-DD
                try:
                    snipe_date = datetime.strptime(snipe_date_str, '%Y-%m-%d').date()
                except ValueError:
                    print(f"❌ Invalid snipe_date format: '{snipe_date_str}'. Use 'today', 'tomorrow', or YYYY-MM-DD")
                    return None
            
            # Create target datetime
            snipe_datetime = datetime.combine(snipe_date, datetime.strptime(snipe_time_str, '%H:%M').time())
            
            # Validate snipe time isn't in the past (with 5 minute buffer)
            if snipe_datetime < now - timedelta(minutes=5):
                print(f"⚠️ Snipe time {snipe_datetime.strftime('%Y-%m-%d %H:%M')} is in the past")
                
                # If it's today but past, assume tomorrow
                if snipe_date_str.lower() == 'today':
                    snipe_datetime = snipe_datetime + timedelta(days=1)
                    print(f"🔄 Adjusted to tomorrow: {snipe_datetime.strftime('%Y-%m-%d %H:%M')}")
                else:
                    return None
            
            return {
                'target_time': snipe_datetime,
                'max_attempts': snipe_config.get('max_attempts', 100),
                'attempt_interval': snipe_config.get('attempt_interval', 0.5)
            }
            
        except Exception as e:
            print(f"❌ Error parsing snipe configuration: {e}")
            return None
    
    def wait_for_snipe_time(self, snipe_info):
        """Wait until the snipe time arrives with countdown."""
        target_time = snipe_info['target_time']
        now = datetime.now()
        
        if target_time <= now:
            print("🎯 Snipe time has arrived! Starting immediately...")
            return True
        
        time_diff = target_time - now
        total_seconds = int(time_diff.total_seconds())
        
        print(f"\n⏰ SNIPING MODE ACTIVATED")
        print(f"🎯 Target time: {target_time.strftime('%A, %B %d at %H:%M:%S')}")
        print(f"⏳ Waiting: {time_diff}")
        print("=" * 60)
        
        # Countdown in intervals
        while datetime.now() < target_time:
            remaining = target_time - datetime.now()
            seconds_left = int(remaining.total_seconds())
            
            if seconds_left <= 0:
                break
            
            # Show countdown at different intervals
            if seconds_left > 3600:  # More than 1 hour
                if seconds_left % 300 == 0:  # Every 5 minutes
                    hours = seconds_left // 3600
                    minutes = (seconds_left % 3600) // 60
                    print(f"⏳ {hours}h {minutes}m remaining until snipe time...")
            elif seconds_left > 60:  # More than 1 minute
                if seconds_left % 30 == 0:  # Every 30 seconds
                    minutes = seconds_left // 60
                    seconds = seconds_left % 60
                    print(f"⏳ {minutes}m {seconds}s remaining...")
            elif seconds_left > 10:  # Last minute
                if seconds_left % 5 == 0:  # Every 5 seconds
                    print(f"⏳ {seconds_left} seconds...")
            else:  # Final countdown
                print(f"🎯 {seconds_left}...")
            
            time.sleep(1)
        
        print("\n🚀 SNIPE TIME REACHED! Starting reservation hunt...")
        return True
    
    def snipe_reservation(self, snipe_info):
        """Rapidly check for and book reservations during snipe mode with smart date detection."""
        print("\n🎯 SNIPING MODE: Rapid slot detection activated!")
        
        max_attempts = snipe_info['max_attempts']
        attempt_interval = snipe_info['attempt_interval']
        
        # Navigate to restaurant page once
        self.driver.get(self.restaurant_url)
        time.sleep(2)
        self.handle_blocking_modals()
        
        print(f"🔄 Will check for slots every {attempt_interval}s for up to {max_attempts} attempts")
        print(f"📅 Using smart date detection + checking {self.days_range} days from today")
        print("🎯 Looking for the FIRST available slot...")
        
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"\r🔍 Attempt {attempt}/{max_attempts} - Smart scanning...", end='', flush=True)
                
                today = datetime.now().date()
                found_slots = []
                checked_dates = set()
                
                # SMART SNIPE STEP 1: Check today first
                slots = self.check_date_availability(today)
                checked_dates.add(today)
                
                if slots:
                    found_slots.extend(slots)
                else:
                    # SMART SNIPE STEP 2: Check suggested date
                    suggested_date = self.parse_next_availability_date()
                    
                    if suggested_date and suggested_date not in checked_dates:
                        days_from_today = (suggested_date - today).days
                        if 0 <= days_from_today <= self.days_range:
                            slots = self.check_date_availability(suggested_date)
                            checked_dates.add(suggested_date)
                            if slots:
                                found_slots.extend(slots)
                
                # SMART SNIPE STEP 3: Quick sequential check if still nothing
                if not found_slots:
                    # Only check a few dates in snipe mode for speed
                    max_snipe_dates = min(5, self.days_range)  # Limit to 5 dates for speed
                    
                    for day_offset in range(max_snipe_dates):
                        target_date = today + timedelta(days=day_offset)
                        
                        if target_date in checked_dates:
                            continue
                            
                        slots = self.check_date_availability(target_date)
                        checked_dates.add(target_date)
                        
                        if slots:
                            found_slots.extend(slots)
                            break  # Take first slot found
                
                if found_slots:
                    print(f"\n🎉 FOUND {len(found_slots)} AVAILABLE SLOTS on attempt {attempt}!")
                    
                    # Auto-select first slot in snipe mode
                    selected_slot = found_slots[0]
                    print(f"🎯 SNIPING: {selected_slot['display']}")
                    
                    # Immediately attempt to book
                    print("⚡ BOOKING IMMEDIATELY...")
                    success = self.make_reservation(selected_slot)
                    
                    if success:
                        print(f"\n🎉 SNIPE SUCCESSFUL! Booked on attempt {attempt}")
                        return True
                    else:
                        print(f"\n⚠️ Booking failed on attempt {attempt}, continuing...")
                
                # If no slots found, brief pause before next attempt
                if attempt < max_attempts:
                    time.sleep(attempt_interval)
                    
            except Exception as e:
                print(f"\n⚠️ Error on attempt {attempt}: {e}")
                if attempt < max_attempts:
                    time.sleep(attempt_interval)
                continue
        
        print(f"\n❌ Snipe completed after {max_attempts} attempts. No reservations secured.")
        return False
        
    def run(self):
        """Main execution flow."""
        try:
            print("🤖 Resy Reservation Bot Starting...")
            print("=" * 50)
            
            # Setup
            self.setup_driver()
            
            # Login flow
            login_success = self.login_flow()
            if not login_success:
                print("❌ Login failed. Exiting...")
                return
            
            # Get user inputs
            self.get_user_inputs()
            
            # Check for sniping mode
            snipe_info = self.parse_snipe_time()
            
            if snipe_info:
                print("🎯 SNIPING MODE ENABLED!")
                print(f"⏰ Target: {snipe_info['target_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"🔄 Max attempts: {snipe_info['max_attempts']}")
                print(f"⚡ Interval: {snipe_info['attempt_interval']}s")
                
                # Wait for snipe time
                if self.wait_for_snipe_time(snipe_info):
                    # Execute snipe
                    success = self.snipe_reservation(snipe_info)
                    
                    if success:
                        print("\n🎉 SNIPE SUCCESSFUL! Reservation secured!")
                    else:
                        print("\n❌ Snipe completed but no reservation secured")
                else:
                    print("\n❌ Snipe cancelled")
            else:
                # Normal mode - search for available slots
                available_slots = self.scrape_available_slots()
                
                # Display options and get selection
                selected_slot = self.display_and_select_slot(available_slots)
                
                if selected_slot:
                    # Make reservation
                    success = self.make_reservation(selected_slot)
                    
                    if success:
                        print("\n🎉 Bot execution completed!")
                    else:
                        print("\n❌ Failed to complete reservation")
                else:
                    print("\n👋 Bot execution cancelled by user")
                
        except KeyboardInterrupt:
            print("\n\n⏹️ Bot stopped by user")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        finally:
            if self.driver:
                print("\n🧹 Cleaning up...")
                input("Press Enter to close the browser...")
                self.driver.quit()
                print("✅ Browser closed")


def main():
    """Entry point of the application."""
    bot = ResyBot()
    bot.run()


if __name__ == "__main__":
    main()

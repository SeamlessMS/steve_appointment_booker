#!/usr/bin/env python3
"""
Steve Appointment Booker - System Test Script
This script performs comprehensive system tests to verify that all components are working correctly.
"""

import os
import sys
import json
import time
import logging
import requests
import argparse
import sqlite3
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("system_test")

# Constants
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')
CONFIG_PATH = os.path.join(BACKEND_DIR, 'config.json')
DB_PATH = os.path.join(BACKEND_DIR, 'database.db')

# Load configuration
def load_config():
    """Load configuration from config.json file"""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None

class SystemTester:
    def __init__(self):
        """Initialize the system tester"""
        self.config = load_config()
        self.test_results = {
            "config": False,
            "database": False,
            "twilio": False,
            "openai": False,
            "elevenlabs": False,
            "backend": False,
            "call": False,
            "webhook": False
        }
        self.test_phone = None
        
    def set_test_phone(self, phone_number):
        """Set the phone number to use for testing"""
        self.test_phone = phone_number
        logger.info(f"Using phone number: {phone_number} for tests")
        
    def run_all_tests(self):
        """Run all system tests"""
        logger.info("Starting comprehensive system test...")
        
        self.test_config()
        self.test_database()
        
        if self.test_results["config"]:
            self.test_twilio_credentials()
            self.test_openai_api()
            self.test_elevenlabs()
        
        self.test_backend_server()
        
        if self.test_phone and self.test_results["twilio"] and self.test_results["backend"]:
            self.test_make_call()
        
        self.print_results()
        return all(self.test_results.values())
    
    def test_config(self):
        """Test configuration file"""
        logger.info("Testing configuration...")
        
        if not self.config:
            logger.error("Failed to load configuration file")
            return
        
        # Check essential keys
        essential_keys = [
            'TWILIO_ACCOUNT_SID', 
            'TWILIO_AUTH_TOKEN', 
            'TWILIO_PHONE_NUMBER',
            'LLM_API_KEY',
            'ELEVENLABS_API_KEY',
            'ELEVENLABS_VOICE_ID',
            'CALLBACK_URL'
        ]
        
        missing_keys = [key for key in essential_keys if not self.config.get(key)]
        
        if missing_keys:
            logger.warning(f"Missing essential configuration keys: {', '.join(missing_keys)}")
            logger.warning("Some tests may fail due to missing configuration")
        else:
            logger.info("All essential configuration keys are present")
            
        # Verify webhook URL format
        callback_url = self.config.get('CALLBACK_URL', '')
        if not callback_url.startswith('http'):
            logger.warning(f"CALLBACK_URL '{callback_url}' does not appear to be a valid URL")
        
        self.test_results["config"] = True
        logger.info("Configuration test passed")
        
    def test_database(self):
        """Test database connection and structure"""
        logger.info("Testing database...")
        
        if not os.path.exists(DB_PATH):
            logger.error(f"Database file not found: {DB_PATH}")
            return
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if essential tables exist
            tables = [
                "leads",
                "call_logs",
                "appointments",
                "industry_patterns",
                "settings"
            ]
            
            for table in tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    logger.warning(f"Table '{table}' not found in database")
            
            # Count records in leads table
            cursor.execute("SELECT COUNT(*) FROM leads")
            lead_count = cursor.fetchone()[0]
            logger.info(f"Found {lead_count} leads in database")
            
            conn.close()
            self.test_results["database"] = True
            logger.info("Database test passed")
        except Exception as e:
            logger.error(f"Database test failed: {e}")
    
    def test_twilio_credentials(self):
        """Test Twilio credentials"""
        logger.info("Testing Twilio credentials...")
        
        account_sid = self.config.get('TWILIO_ACCOUNT_SID')
        auth_token = self.config.get('TWILIO_AUTH_TOKEN')
        phone_number = self.config.get('TWILIO_PHONE_NUMBER')
        
        if not account_sid or not auth_token or not phone_number:
            logger.error("Missing Twilio credentials in config")
            return
        
        try:
            client = Client(account_sid, auth_token)
            
            # Test if we can fetch account info
            account = client.api.accounts(account_sid).fetch()
            logger.info(f"Successfully authenticated with Twilio account: {account.friendly_name}")
            
            # Check if the phone number exists
            try:
                numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
                if numbers:
                    logger.info(f"Phone number {phone_number} is valid and belongs to this account")
                else:
                    logger.warning(f"Phone number {phone_number} not found in this account")
                    available_numbers = client.incoming_phone_numbers.list(limit=5)
                    if available_numbers:
                        for number in available_numbers:
                            logger.info(f"Available number: {number.phone_number}")
            except Exception as e:
                logger.error(f"Error checking phone number: {str(e)}")
            
            # Check account balance
            balance = client.api.accounts(account_sid).balance.fetch()
            logger.info(f"Account balance: ${balance.balance}")
            
            self.test_results["twilio"] = True
            logger.info("Twilio credentials test passed")
        except TwilioRestException as e:
            logger.error(f"Twilio authentication error: {e.msg}")
        except Exception as e:
            logger.error(f"Unexpected error testing Twilio: {str(e)}")
    
    def test_openai_api(self):
        """Test OpenAI API key"""
        logger.info("Testing OpenAI API...")
        
        api_key = self.config.get('LLM_API_KEY')
        if not api_key:
            logger.error("OpenAI API key not found in config")
            return
        
        try:
            # Simplified version without importing openai
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers=headers
            )
            
            if response.status_code == 200:
                models = response.json()
                logger.info(f"Successfully connected to OpenAI API. Available models: {len(models.get('data', []))}")
                self.test_results["openai"] = True
                logger.info("OpenAI API test passed")
            else:
                logger.error(f"OpenAI API test failed with status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.error(f"Error testing OpenAI API: {str(e)}")
    
    def test_elevenlabs(self):
        """Test ElevenLabs API key"""
        logger.info("Testing ElevenLabs API...")
        
        api_key = self.config.get('ELEVENLABS_API_KEY')
        voice_id = self.config.get('ELEVENLABS_VOICE_ID')
        
        if not api_key or not voice_id:
            logger.error("ElevenLabs API key or Voice ID not found in config")
            return
        
        try:
            # Check if the voice ID exists
            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json"
            }
            response = requests.get(
                f"https://api.elevenlabs.io/v1/voices/{voice_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                voice_data = response.json()
                logger.info(f"Successfully connected to ElevenLabs API. Voice name: {voice_data.get('name', 'Unknown')}")
                self.test_results["elevenlabs"] = True
                logger.info("ElevenLabs API test passed")
            else:
                logger.error(f"ElevenLabs API test failed with status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.error(f"Error testing ElevenLabs API: {str(e)}")
    
    def test_backend_server(self):
        """Test backend server"""
        logger.info("Testing backend server...")
        
        # Check if the backend server is running
        try:
            response = requests.get("http://localhost:5001", timeout=2)
            if response.status_code == 200:
                logger.info("Backend server is running")
                self.test_results["backend"] = True
                logger.info("Backend server test passed")
                return
        except requests.exceptions.RequestException:
            pass
        
        logger.warning("Backend server is not running, attempting to start it...")
        
        # Try to start the backend server
        try:
            current_dir = os.getcwd()
            os.chdir(BACKEND_DIR)
            
            # Use different start commands based on the platform
            if sys.platform == 'win32':
                os.system(f"start python app.py")
            else:
                os.system(f"python app.py &")
                
            os.chdir(current_dir)
            
            # Wait for the server to start
            for attempt in range(10):
                time.sleep(1)
                try:
                    response = requests.get("http://localhost:5001", timeout=2)
                    if response.status_code == 200:
                        logger.info("Backend server started successfully")
                        self.test_results["backend"] = True
                        logger.info("Backend server test passed")
                        return
                except requests.exceptions.RequestException:
                    logger.info(f"Waiting for backend to start... ({attempt+1}/10)")
            
            logger.error("Failed to start backend server")
        except Exception as e:
            logger.error(f"Error starting backend server: {str(e)}")
    
    def test_make_call(self):
        """Test making a call through the API"""
        if not self.test_phone:
            logger.warning("No test phone number provided, skipping call test")
            return
        
        logger.info(f"Testing making a call to {self.test_phone}...")
        
        # First check if we have a lead with this number
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM leads WHERE phone = ?", (self.test_phone,))
            lead = cursor.fetchone()
            
            lead_id = None
            if lead:
                lead_id = lead[0]
                logger.info(f"Found existing lead with ID {lead_id}")
            else:
                # Create a test lead
                cursor.execute('''
                    INSERT INTO leads (name, phone, category, status, employee_count, uses_mobile_devices, industry)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', ("Test User", self.test_phone, "Test", "Not Called", 10, "Yes", "Technology"))
                conn.commit()
                lead_id = cursor.lastrowid
                logger.info(f"Created test lead with ID {lead_id}")
            
            conn.close()
            
            # Make a call through the API
            url = "http://localhost:5001/api/call"
            headers = {
                "Content-Type": "application/json"
            }
            data = {
                "lead_id": lead_id,
                "is_manual": True,
                "script": "Hello! This is a test call from the Steve appointment booker system. This is just a test to confirm our system is working correctly."
            }
            
            logger.info(f"Making API call with data: {data}")
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Call API response: {response_data}")
                call_sid = response_data.get('callSid')
                
                if call_sid:
                    logger.info(f"Call initiated with SID: {call_sid}")
                    self.test_results["call"] = True
                    logger.info("Call test passed")
                else:
                    logger.warning("Call API did not return a call SID")
            else:
                logger.error(f"Call API request failed with status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.error(f"Error making test call: {str(e)}")
    
    def print_results(self):
        """Print test results summary"""
        logger.info("\n=== System Test Results ===")
        for test, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test.upper()}: {status}")
        
        if all(self.test_results.values()):
            logger.info("\n🎉 All system tests passed! The system is ready to use.")
        else:
            logger.warning("\n⚠️ Some tests failed. The system may not function correctly.")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Steve Appointment Booker System Test')
    parser.add_argument('--phone', type=str, help='Phone number to use for test calls (format: 1234567890)')
    parser.add_argument('--test', type=str, help='Run specific test (config, database, twilio, openai, elevenlabs, backend, call)')
    args = parser.parse_args()
    
    tester = SystemTester()
    
    if args.phone:
        tester.set_test_phone(args.phone)
    
    if args.test:
        # Run specific test
        test_method = f"test_{args.test}"
        if hasattr(tester, test_method) and callable(getattr(tester, test_method)):
            getattr(tester, test_method)()
            tester.print_results()
        else:
            logger.error(f"Unknown test: {args.test}")
            logger.info("Available tests: config, database, twilio, openai, elevenlabs, backend, call")
    else:
        # Run all tests
        tester.run_all_tests()

if __name__ == "__main__":
    main() 
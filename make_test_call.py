#!/usr/bin/env python3
"""
Steve Appointment Booker - Test Call (Redirector)
This script is a redirector to tests/test_twilio_call.py for backward compatibility.
"""

import os
import sys
import argparse

# Add tests directory to path
sys.path.append(os.path.dirname(__file__))

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test Twilio credentials and make a test call')
    parser.add_argument('--phone', type=str, help='Phone number to call (format: 1234567890)')
    args = parser.parse_args()
    
    # Import the real test module
    from tests.test_twilio_call import main as original_main
    
    # Run the original main function
    original_main()

if __name__ == "__main__":
    main() 
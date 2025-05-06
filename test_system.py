#!/usr/bin/env python3
"""
Steve Appointment Booker - System Test Script (Redirector)
This script is a redirector to tests/test_system.py for backward compatibility.
"""

import os
import sys
import argparse

# Add tests directory to path
sys.path.append(os.path.dirname(__file__))

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Steve Appointment Booker System Test')
    parser.add_argument('--phone', type=str, help='Phone number to use for test calls (format: 1234567890)')
    parser.add_argument('--test', type=str, help='Run specific test (config, database, twilio, openai, elevenlabs, backend, call)')
    args = parser.parse_args()
    
    # Import the real test module
    from tests.test_system import SystemTester, main as original_main
    
    # Run the original main function
    original_main()

if __name__ == "__main__":
    main() 
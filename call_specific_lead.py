#!/usr/bin/env python3
"""
Script to test calling a specific lead in the database
This uses the call API endpoint which handles conversation recording properly
"""

import json
import requests
import argparse
import sys
import sqlite3

def find_lead_by_phone(phone_number, db_name=None):
    """Find a lead in the databases by phone number"""
    databases = []
    
    if db_name:
        # Specific database requested
        databases = [f'backend/{db_name}']
    else:
        # Check all databases
        databases = [
            'backend/database.db',
            'backend/leads.db'
        ]
    
    for db_path in databases:
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if leads table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leads';")
            if cursor.fetchone():
                # Find leads with this phone number
                cursor.execute('SELECT id, name, phone, status FROM leads WHERE phone LIKE ?', 
                            (f'%{phone_number}%',))
                lead = cursor.fetchone()
                if lead:
                    conn.close()
                    return dict(lead), db_path
            
            conn.close()
        except Exception as e:
            print(f"Error checking database {db_path}: {e}")
    
    return None, None

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test calling a specific lead')
    parser.add_argument('--phone', type=str, required=True, help='Phone number of the lead to call (format: 1234567890)')
    parser.add_argument('--db', type=str, help='Specific database to use (example: database.db)')
    args = parser.parse_args()
    
    # Validate phone number format
    phone = args.phone.strip()
    
    # Find lead in database
    lead, db_path = find_lead_by_phone(phone, args.db)
    if not lead:
        print(f"No lead found with phone number {phone}")
        sys.exit(1)
    
    print(f"Found lead: ID={lead['id']}, Name={lead['name']}, Phone={lead['phone']}, Status={lead['status']}")
    print(f"In database: {db_path}")
    
    # Ask for confirmation
    confirm = input(f"Do you want to call this lead? (y/n): ")
    if confirm.lower() != 'y':
        print("Call canceled")
        sys.exit(0)
    
    # Prepare API call
    try:
        # Load configuration to get API endpoint
        with open('backend/config.json', 'r') as f:
            config = json.load(f)
        
        # API endpoint
        api_url = "http://localhost:5001/api/call"
        
        # Payload
        payload = {
            "lead_id": lead['id'],
            "is_manual": True  # Bypass time restrictions
        }
        
        # Make API call
        print(f"Calling lead {lead['id']} at {lead['phone']}...")
        response = requests.post(api_url, json=payload)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            if 'call_sid' in result:
                print(f"Call initiated with SID: {result['call_sid']}")
                if result.get('dummy', False):
                    print("Note: This was a dummy call (no actual call placed)")
            else:
                print(f"API call successful but no call_sid returned: {result}")
        else:
            print(f"API call failed with status code {response.status_code}")
            print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"Error making API call: {e}")

if __name__ == "__main__":
    main() 
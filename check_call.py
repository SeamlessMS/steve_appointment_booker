#!/usr/bin/env python3
import json
import sqlite3
from twilio.rest import Client
import os

# Load configuration
with open('backend/config.json', 'r') as f:
    config = json.load(f)

# Initialize Twilio client
client = Client(config['TWILIO_ACCOUNT_SID'], config['TWILIO_AUTH_TOKEN'])

# Check call status
call_sid = 'CAab9584ef820af39f9df12c605a84d9cf'
call = client.calls(call_sid).fetch()

print("\n=== TWILIO CALL STATUS ===")
print(f"Call to: {call.to}")
try:
    print(f"From: {call.from_}")
except AttributeError:
    print(f"From: {getattr(call, 'from_', '')}")
print(f"Status: {call.status}")
print(f"Direction: {call.direction}")
print(f"Duration: {call.duration} seconds")
print(f"Start time: {call.start_time}")
print(f"End time: {call.end_time}")

# Check each database file
database_files = [
    'backend/app.db',
    'backend/database.db',
    'backend/leads.db'
]

phone = call.to.replace('+1', '')  # Remove country code for matching

for db_path in database_files:
    if not os.path.exists(db_path):
        print(f"\nDatabase file not found: {db_path}")
        continue
        
    print(f"\n=== DATABASE: {os.path.basename(db_path)} ===")
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables in database: {', '.join([t[0] for t in tables])}")
        
        # Check for leads table
        if any(t[0] == 'leads' for t in tables):
            # Find leads with phone number matching the one we called
            cursor.execute('SELECT id, name, phone, status FROM leads WHERE phone LIKE ?', (f'%{phone}%',))
            leads = cursor.fetchall()
            
            if leads:
                print(f"\nFound {len(leads)} lead(s) with matching phone number:")
                for lead in leads:
                    lead_id = lead['id']
                    print(f"\nLead ID: {lead_id}")
                    print(f"Name: {lead['name']}")
                    print(f"Phone: {lead['phone']}")
                    print(f"Status: {lead['status']}")
                    
                    # Check if call_logs table exists
                    if any(t[0] == 'call_logs' for t in tables):
                        # Get call logs for this lead
                        cursor.execute('SELECT * FROM call_logs WHERE lead_id = ? ORDER BY created_at DESC', (lead_id,))
                        logs = cursor.fetchall()
                        
                        if logs:
                            print(f"\nFound {len(logs)} call log entries:")
                            for i, log in enumerate(logs, 1):
                                print(f"\n  {i}. Status: {log['call_status']}")
                                print(f"     Time: {log['created_at']}")
                                if log['transcript']:
                                    print(f"     Transcript: {log['transcript'][:100]}...")
                        else:
                            print("\nNo call logs found for this lead.")
                    else:
                        print("\nNo call_logs table found in this database.")
            else:
                print("\nNo matching leads found in this database.")
        else:
            print("\nNo leads table found in this database.")
            
        # Check all call logs regardless of lead ID (for test calls)
        if any(t[0] == 'call_logs' for t in tables):
            print("\n--- All Call Logs (recent) ---")
            cursor.execute('SELECT * FROM call_logs ORDER BY created_at DESC LIMIT 10')
            logs = cursor.fetchall()
            
            if logs:
                print(f"Found {len(logs)} recent call log entries:")
                for i, log in enumerate(logs, 1):
                    print(f"\n  {i}. Lead ID: {log['lead_id']}")
                    print(f"     Status: {log['call_status']}")
                    print(f"     Time: {log['created_at']}")
                    if log['transcript']:
                        print(f"     Transcript: {log['transcript'][:100]}...")
            else:
                print("No call logs found in this database.")
            
    except Exception as e:
        print(f"Error accessing database: {str(e)}")
    finally:
        if conn:
            conn.close() 
import sqlite3
import os
import sys
import argparse

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check call logs for a specific phone number')
    parser.add_argument('--phone', type=str, help='Phone number to check (format: 1234567890)')
    args = parser.parse_args()
    
    # Get the phone number
    phone_number = args.phone
    
    # Ask for phone number if not provided
    if not phone_number:
        print("Please enter a phone number to check logs for (or press Enter to exit):")
        phone_number = input().strip()
        
    if not phone_number:
        print("No phone number provided. Exiting.")
        return
    
    print(f"Checking logs for phone number: {phone_number}")
    
    db_path = 'backend/database.db'
    
    # Make sure the database exists
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First check if the lead exists
    cursor.execute("SELECT * FROM leads WHERE phone = ?", (phone_number,))
    lead = cursor.fetchone()
    
    if not lead:
        print("No lead found with that phone number.")
        return
    
    lead_id = lead[0]
    print(f"Lead found with ID: {lead_id}")
    print(f"Lead details: {lead}")
    
    # Check for call logs
    cursor.execute("SELECT * FROM call_logs WHERE lead_id = ?", (lead_id,))
    logs = cursor.fetchall()
    
    print(f"Found {len(logs)} call logs:")
    for log in logs:
        print(f"Log ID: {log[0]}, Status: {log[2]}, Time: {log[4]}")
        print(f"Transcript: {log[3]}")
        print("-" * 50)
    
    # Check the status of the lead
    cursor.execute("SELECT status FROM leads WHERE id = ?", (lead_id,))
    status = cursor.fetchone()[0]
    print(f"Current lead status: {status}")
    
    conn.close()

if __name__ == "__main__":
    main() 
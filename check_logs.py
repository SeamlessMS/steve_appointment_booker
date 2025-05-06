import sqlite3
import os
import sys

def main():
    db_path = 'backend/database.db'
    
    # Make sure the database exists
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First check if the lead exists
    cursor.execute("SELECT * FROM leads WHERE phone = '3036426337'")
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
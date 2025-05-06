import requests
import json
import sys
import os
import sqlite3

def fix_phone_number():
    db_path = 'backend/database.db'
    target_phone = "3036426337"  # The phone number you want to call
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if lead ID 1 exists
    cursor.execute("SELECT id, phone FROM leads WHERE id = 1")
    lead = cursor.fetchone()
    
    if not lead:
        print("Lead with ID 1 not found. Creating a new lead.")
        cursor.execute('''
            INSERT INTO leads (id, name, phone, category, address, status, employee_count, uses_mobile_devices, industry, city, state) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (1, "Test User", target_phone, "Test", "123 Test St", "Not Called", 10, "Yes", "Technology", "Denver", "CO"))
        conn.commit()
        print(f"Created lead with ID: 1, phone: {target_phone}")
    else:
        lead_id, current_phone = lead
        print(f"Found lead with ID: 1, current phone: {current_phone}")
        
        # Update the phone number
        cursor.execute("UPDATE leads SET phone = ? WHERE id = ?", (target_phone, 1))
        conn.commit()
        print(f"Updated phone number to: {target_phone}")
    
    # Verify the update
    cursor.execute("SELECT phone FROM leads WHERE id = 1")
    updated_phone = cursor.fetchone()[0]
    print(f"Phone number in database is now: {updated_phone}")
    
    conn.close()
    return True

def make_call_to_api():
    url = "http://localhost:5001/api/call"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "lead_id": 1,
        "is_manual": True,
        "script": "Hello! This is Steve with Seamless Mobile Services. I'm calling to see if your company uses mobile phones or tablets for work. This is just a test call to confirm our system is working correctly."
    }
    
    print(f"Making call to API with data: {data}")
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        return True
    except Exception as e:
        print(f"Error making API call: {e}")
        return False

def main():
    print("Step 1: Fixing phone number in database...")
    if fix_phone_number():
        print("\nStep 2: Making call via API...")
        make_call_to_api()
    else:
        print("Failed to fix phone number. Aborting call.")

if __name__ == "__main__":
    main() 
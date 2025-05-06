import requests
import json
import sys
import os
import sqlite3

def init_db():
    db_path = 'backend/database.db'
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create the leads table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        category TEXT,
        address TEXT,
        website TEXT,
        status TEXT DEFAULT 'Not Called',
        employee_count INTEGER DEFAULT 0,
        uses_mobile_devices TEXT DEFAULT 'Unknown',
        industry TEXT,
        city TEXT,
        state TEXT,
        email TEXT,
        company TEXT,
        position TEXT,
        location TEXT,
        qualification_status TEXT DEFAULT 'Unknown',
        appointment_date TEXT,
        appointment_time TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create other required tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS call_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        call_status TEXT,
        transcript TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (lead_id) REFERENCES leads(id)
    )
    ''')
    
    conn.commit()
    return conn

def main():
    conn = init_db()
    cursor = conn.cursor()
    
    # Get the test phone number to call
    phone_number = "3036426337"  # Hard-coded for this test
    
    # Find the lead with the phone number
    cursor.execute("SELECT id, phone FROM leads WHERE phone = ?", (phone_number,))
    lead = cursor.fetchone()
    
    if not lead:
        print(f"No lead found with phone number {phone_number}. Creating one...")
        cursor.execute('''
            INSERT INTO leads (name, phone, category, address, status, employee_count, uses_mobile_devices, industry, city, state) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("Test User", phone_number, "Test", "123 Test St", "Not Called", 10, "Yes", "Technology", "Denver", "CO"))
        conn.commit()
        lead_id = cursor.lastrowid
        print(f"Created lead with ID: {lead_id}, phone: {phone_number}")
    else:
        lead_id, db_phone = lead
        print(f"Found existing lead with ID: {lead_id}, phone: {db_phone}")
        
        # Update phone if it's not exactly matching
        if db_phone != phone_number:
            print(f"WARNING: Phone number in database ({db_phone}) doesn't match expected format ({phone_number})")
            cursor.execute("UPDATE leads SET phone = ? WHERE id = ?", (phone_number, lead_id))
            conn.commit()
            print(f"Updated phone number to: {phone_number}")
    
    # Double-check that the phone number is formatted correctly
    cursor.execute("SELECT phone FROM leads WHERE id = ?", (lead_id,))
    phone_in_db = cursor.fetchone()[0]
    print(f"Phone number in database: {phone_in_db}")
    
    # Now make the call
    url = "http://localhost:5001/api/call"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "lead_id": lead_id,
        "is_manual": True,
        # Add phone explicitly to make sure the right number is called
        "phone": phone_number  
    }
    
    print(f"Making call to API with data: {data}")
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # Check the lead status after the call
        cursor.execute("SELECT status FROM leads WHERE id = ?", (lead_id,))
        new_status = cursor.fetchone()[0]
        print(f"Lead status after API call: {new_status}")
        
    except Exception as e:
        print(f"Error making API call: {e}")
    
    conn.close()

if __name__ == "__main__":
    main() 
import sqlite3

def update_bright_data_settings():
    """Update Bright Data settings in the database."""
    print("Updating Bright Data settings...")
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Insert or replace Bright Data settings
    cursor.execute(
        'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
        ('BRIGHTDATA_API_TOKEN', '4b73ea546673851974fe17047cffa177ab51ae4570ad67b312e70f592a8b774f')
    )
    
    cursor.execute(
        'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
        ('BRIGHTDATA_WEB_UNLOCKER_ZONE', 'seamlessms')
    )
    
    conn.commit()
    
    # Verify settings were updated
    cursor.execute('SELECT key, value FROM settings WHERE key IN ("BRIGHTDATA_API_TOKEN", "BRIGHTDATA_WEB_UNLOCKER_ZONE")')
    results = cursor.fetchall()
    
    print("Updated settings:")
    for key, value in results:
        if key == 'BRIGHTDATA_API_TOKEN':
            print(f"- {key}: {value[:10]}...{value[-10:]}")
        else:
            print(f"- {key}: {value}")
    
    conn.close()
    print("Bright Data settings updated successfully.")

if __name__ == "__main__":
    update_bright_data_settings() 
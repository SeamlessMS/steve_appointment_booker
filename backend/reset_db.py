import os
import sqlite3
from models import init_db

# Remove the existing database if it exists
if os.path.exists('leads.db'):
    print("Removing existing database...")
    os.remove('leads.db')

# Initialize the database
print("Initializing new database...")
init_db()

# Manually add columns if they're missing
print("Checking for missing columns...")
conn = sqlite3.connect('leads.db')
cursor = conn.cursor()

# Define all columns that should be present
needed_columns = [
    ('status', 'TEXT DEFAULT "Not Called"'),
    ('employee_count', 'INTEGER DEFAULT 0'),
    ('uses_mobile_devices', 'TEXT DEFAULT "Unknown"'),
    ('industry', 'TEXT'),
    ('city', 'TEXT'),
    ('state', 'TEXT'),
    ('appointment_date', 'TEXT'),
    ('appointment_time', 'TEXT'),
    ('qualification_status', 'TEXT DEFAULT "Not Qualified"'),
    ('notes', 'TEXT')
]

# Get current columns
cursor.execute("PRAGMA table_info(leads);")
existing_columns = [column[1] for column in cursor.fetchall()]
print(f"Existing columns: {existing_columns}")

# Add missing columns
for col_name, col_type in needed_columns:
    if col_name not in existing_columns:
        print(f"Adding missing column: {col_name}")
        cursor.execute(f'ALTER TABLE leads ADD COLUMN {col_name} {col_type}')

conn.commit()

# Get schema for leads table after changes
print("\nUpdated schema for leads table:")
cursor.execute("PRAGMA table_info(leads);")
columns = cursor.fetchall()
for column in columns:
    print(f"  {column[1]} ({column[2]})")

# Get list of all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("\nTables in the database:")
for table in tables:
    print(f"- {table[0]}")

conn.close()

print("\nDatabase reset complete!") 
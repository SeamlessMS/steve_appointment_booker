import sqlite3

# Connect to the database
conn = sqlite3.connect('leads.db')
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in the database:")
for table in tables:
    print(f"- {table[0]}")

# Get schema for each table
for table in tables:
    print(f"\nSchema for table {table[0]}:")
    cursor.execute(f"PRAGMA table_info({table[0]});")
    columns = cursor.fetchall()
    for column in columns:
        print(f"  {column[1]} ({column[2]})")

# Check if there are any leads
cursor.execute("SELECT COUNT(*) FROM leads;")
lead_count = cursor.fetchone()[0]
print(f"\nNumber of leads in the database: {lead_count}")

# Close the connection
conn.close() 
import sqlite3
import json

# Connect to the database
conn = sqlite3.connect('leads.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check if learning_patterns table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='learning_patterns'")
table_exists = cursor.fetchone()

print(f"Learning patterns table exists: {bool(table_exists)}")

# Create the table if it doesn't exist
if not table_exists:
    print("Creating learning_patterns table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            industry TEXT,
            patterns TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    print("Table created successfully.")

# Check if table has data
cursor.execute("SELECT COUNT(*) FROM learning_patterns")
count = cursor.fetchone()[0]
print(f"Number of patterns stored: {count}")

# Insert a sample pattern for testing if none exist
if count == 0:
    sample_pattern = {
        "count": 5,
        "successful_phrases": {
            "we can help reduce your mobile expenses by up to 30%": 3,
            "our telecom expense management system identifies billing errors automatically": 2
        },
        "objection_responses": {
            "objection:not interested": [
                "I understand. Many of our clients initially felt the same way until they saw how much they could save. Would you be open to a 15-minute demo to see if it might be helpful for your business?"
            ]
        }
    }
    
    print("Adding sample pattern for testing...")
    cursor.execute(
        "INSERT INTO learning_patterns (industry, patterns) VALUES (?, ?)",
        ("generic", json.dumps(sample_pattern))
    )
    conn.commit()
    print("Sample pattern added.")

# Display all patterns
cursor.execute("SELECT * FROM learning_patterns")
patterns = cursor.fetchall()

if patterns:
    print("\nStored patterns:")
    for pattern in patterns:
        print(f"- Industry: {pattern['industry']}")
        data = json.loads(pattern['patterns'])
        print(f"  Count: {data['count']}")
        print(f"  Successful phrases: {len(data['successful_phrases'])}")
        print(f"  Objection responses: {len(data['objection_responses'])}")

conn.close() 
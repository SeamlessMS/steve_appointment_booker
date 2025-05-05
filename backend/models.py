import sqlite3
from contextlib import contextmanager
import os

DB_PATH = os.environ.get('DATABASE_URL', 'leads.db').replace('sqlite:///', '')

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                category TEXT,
                address TEXT,
                website TEXT,
                status TEXT DEFAULT 'Not Called',
                employee_count INTEGER DEFAULT 0,
                uses_mobile_devices TEXT DEFAULT 'Unknown',
                industry TEXT,
                city TEXT,
                state TEXT,
                appointment_date TEXT,
                appointment_time TEXT,
                qualification_status TEXT DEFAULT 'Not Qualified',
                notes TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                call_status TEXT,
                transcript TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                date TEXT,
                time TEXT,
                status TEXT DEFAULT 'Scheduled',
                medium TEXT DEFAULT 'Phone',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        ''')
        conn.commit()
        
        # Check if new columns exist and add them if not
        columns_to_add = [
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
        
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(f'SELECT {col_name} FROM leads LIMIT 1')
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                conn.execute(f'ALTER TABLE leads ADD COLUMN {col_name} {col_type}')
                conn.commit()

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
    """Initialize the database with required tables"""
    with get_db() as conn:
        # Create leads table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                email TEXT,
                company TEXT,
                industry TEXT,
                category TEXT,
                status TEXT DEFAULT 'Not Called',
                qualification_status TEXT DEFAULT 'Not Qualified',
                uses_mobile_devices TEXT DEFAULT 'Unknown',
                employee_count INTEGER DEFAULT 0,
                appointment_date TEXT,
                appointment_time TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create call_logs table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                call_status TEXT,
                transcript TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        ''')
        
        # Create appointments table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                date TEXT,
                time TEXT,
                status TEXT DEFAULT 'Scheduled',
                medium TEXT DEFAULT 'Phone',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        ''')
        
        # Create follow_ups table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS follow_ups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                scheduled_time TIMESTAMP,
                priority INTEGER DEFAULT 5,
                reason TEXT,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        ''')
        
        # Create industry_patterns table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS industry_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                industry TEXT,
                pattern_type TEXT,
                pattern_key TEXT,
                pattern_value TEXT,
                success_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(industry, pattern_type, pattern_key)
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

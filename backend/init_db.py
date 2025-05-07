import sqlite3
import os
import sys

def init_db():
    """Initialize the database with required tables."""
    # Database file path
    DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')
    
    # Check if database exists
    db_exists = os.path.exists(DB_PATH)
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Create tables if they don't exist
    with conn:
        # Create leads table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            company TEXT,
            position TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zipcode TEXT,
            industry TEXT,
            employee_count INTEGER,
            notes TEXT,
            status TEXT DEFAULT 'Not Called',
            qualification_status TEXT DEFAULT 'Unknown',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT,
            source TEXT
        )
        ''')
        
        # Create call_logs table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY,
            lead_id INTEGER NOT NULL,
            call_status TEXT NOT NULL,
            transcript TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
        ''')
        
        # Create appointments table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY,
            lead_id INTEGER NOT NULL,
            lead_name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            medium TEXT NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'Scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            zoho_synced INTEGER DEFAULT 0,
            zoho_id TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
        ''')

        # Create followups table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS followups (
            id INTEGER PRIMARY KEY,
            lead_id INTEGER NOT NULL,
            lead_name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
        ''')
        
        # Create settings table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create ai_patterns table for storing learned patterns
        conn.execute('''
        CREATE TABLE IF NOT EXISTS ai_patterns (
            id INTEGER PRIMARY KEY,
            patterns TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create ai_feedback table for storing user feedback
        conn.execute('''
        CREATE TABLE IF NOT EXISTS ai_feedback (
            id INTEGER PRIMARY KEY,
            feedback TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create sync_logs table for tracking CRM syncs
        conn.execute('''
        CREATE TABLE IF NOT EXISTS sync_logs (
            id INTEGER PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            destination TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create voice_settings table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS voice_settings (
            id INTEGER PRIMARY KEY,
            voice_id TEXT NOT NULL,
            voice_name TEXT NOT NULL,
            pitch REAL DEFAULT 1.0,
            speed REAL DEFAULT 1.0,
            stability REAL DEFAULT 0.5,
            is_default INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Insert default settings if they don't exist
        settings = [
            ('OPENAI_API_KEY', ''),
            ('ELEVENLABS_API_KEY', ''),
            ('TEST_MODE', 'true'),
            ('AUTO_QUALIFICATION', 'true'),
            ('APPOINTMENT_LINK', 'https://calendly.com/seamless-mobile'),
            ('ZOHO_API_KEY', ''),
            ('ZOHO_ENABLED', 'false'),
            ('DEFAULT_VOICE_ID', 'voice1'),
            ('CONFIRM_DELETIONS', 'true'),
        ]
        
        for key, value in settings:
            conn.execute(
                'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
                (key, value)
            )
            
        # Insert default voice if table is empty
        voice_count = conn.execute('SELECT COUNT(*) FROM voice_settings').fetchone()[0]
        if voice_count == 0:
            conn.execute('''
                INSERT INTO voice_settings 
                (voice_id, voice_name, pitch, speed, stability, is_default) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('voice5', 'Sales Expert Male', 1.0, 1.0, 0.5, 1))

    print("Database initialized successfully.")
    
    # Only insert test data if database was just created
    if not db_exists:
        insert_test_data(conn)
        print("Test data inserted successfully.")
    
    conn.close()


def insert_test_data(conn):
    """Insert test data into the database."""
    # Insert test leads
    test_leads = [
        ('Acme Construction', 'John Smith', 'CEO', '555-1234', 'john@acme.com', '123 Main St', 'Denver', 'CO', '80202', 'Construction', 25, 'Looking for mobile solutions', 'Not Called', 'Unknown', 'Construction', 'Manual'),
        ('Tech Solutions', 'Jane Doe', 'CTO', '555-5678', 'jane@techsolutions.com', '456 Tech Ave', 'Boulder', 'CO', '80301', 'Technology', 50, 'Interested in field service management', 'Not Called', 'Unknown', 'Technology', 'Manual'),
        ('Green Landscaping', 'Bob Green', 'Owner', '555-9876', 'bob@greenlandscaping.com', '789 Garden Rd', 'Fort Collins', 'CO', '80525', 'Landscaping', 10, 'Needs mobile solution for field team', 'Not Called', 'Unknown', 'Landscaping', 'Manual'),
        ('Reliable Plumbing', 'Mike Johnson', 'Operations Manager', '555-4321', 'mike@reliableplumbing.com', '321 Water St', 'Denver', 'CO', '80210', 'Plumbing', 15, 'Current provider is expensive', 'Not Called', 'Unknown', 'Plumbing', 'Manual'),
        ('Mountain Electric', 'Sarah Williams', 'Owner', '555-8765', 'sarah@mountainelectric.com', '654 Volt Ave', 'Colorado Springs', 'CO', '80903', 'Electrical', 8, 'Looking to improve scheduling', 'Not Called', 'Unknown', 'Electrical', 'Manual'),
    ]

    for lead in test_leads:
        conn.execute('''
        INSERT INTO leads 
        (company, name, position, phone, email, address, city, state, zipcode, industry, employee_count, notes, status, qualification_status, category, source) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', lead)
    
    # Insert sample AI patterns
    sample_patterns = {
        'objectionHandling': [
            "I understand your concern about price. Many of our clients initially felt the same way, but they found the ROI within just a few months.",
            "That's a valid concern. What if we could show you how this solution pays for itself through improved efficiency?"
        ],
        'valuePropositions': [
            "Our mobile solution helps field service businesses reduce paperwork by 80% and increase technician productivity by 25%.",
            "By implementing our system, most clients see a 30% reduction in scheduling errors and a 40% improvement in customer satisfaction."
        ],
        'qualificationQuestions': [
            "How many field technicians do you currently have on your team?",
            "What's your current process for scheduling and dispatching your field teams?"
        ],
        'closingTechniques': [
            "Based on what you've shared, I think we should schedule a demo with our product specialist. How does next Tuesday at 2 PM work for your schedule?",
            "It sounds like we're a good fit for your needs. The next step would be to set up a quick follow-up call with our implementation team. Would you prefer morning or afternoon?"
        ]
    }
    
    conn.execute(
        'INSERT INTO ai_patterns (patterns, created_at) VALUES (?, datetime("now"))',
        (json.dumps(sample_patterns),)
    )

    conn.commit()


if __name__ == '__main__':
    import json
    init_db()
    print("Database initialization complete.") 
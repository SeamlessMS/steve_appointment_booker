-- SQLite schema for the appointment booker application

-- Leads table
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
);

-- Call logs table
CREATE TABLE IF NOT EXISTS call_logs (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER NOT NULL,
    call_status TEXT NOT NULL,
    transcript TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads (id)
);

-- Appointments table
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
);

-- Follow-ups table
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
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI patterns table for storing learned patterns
CREATE TABLE IF NOT EXISTS ai_patterns (
    id INTEGER PRIMARY KEY,
    patterns TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI feedback table for storing user feedback
CREATE TABLE IF NOT EXISTS ai_feedback (
    id INTEGER PRIMARY KEY,
    feedback TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sync logs table for tracking CRM syncs
CREATE TABLE IF NOT EXISTS sync_logs (
    id INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    destination TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Voice settings table
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
);

-- Default settings
INSERT OR IGNORE INTO settings (key, value) VALUES
('OPENAI_API_KEY', ''),
('ELEVENLABS_API_KEY', ''),
('TEST_MODE', 'true'),
('AUTO_QUALIFICATION', 'true'),
('APPOINTMENT_LINK', 'https://calendly.com/seamless-mobile'),
('ZOHO_API_KEY', ''),
('ZOHO_ENABLED', 'false'),
('DEFAULT_VOICE_ID', 'voice1');

-- Default voice settings
INSERT OR IGNORE INTO voice_settings 
    (voice_id, voice_name, pitch, speed, stability, is_default) 
VALUES 
    ('voice5', 'Sales Expert Male', 1.0, 1.0, 0.5, 1);

-- Sample AI patterns
INSERT OR IGNORE INTO ai_patterns (patterns, created_at) VALUES
(
    '{"objectionHandling":["I understand your concern about price. Many of our clients initially felt the same way, but they found the ROI within just a few months.","That\'s a valid concern. What if we could show you how this solution pays for itself through improved efficiency?"],"valuePropositions":["Our mobile solution helps field service businesses reduce paperwork by 80% and increase technician productivity by 25%.","By implementing our system, most clients see a 30% reduction in scheduling errors and a 40% improvement in customer satisfaction."],"qualificationQuestions":["How many field technicians do you currently have on your team?","What\'s your current process for scheduling and dispatching your field teams?"],"closingTechniques":["Based on what you\'ve shared, I think we should schedule a demo with our product specialist. How does next Tuesday at 2 PM work for your schedule?","It sounds like we\'re a good fit for your needs. The next step would be to set up a quick follow-up call with our implementation team. Would you prefer morning or afternoon?"]}',
    datetime('now')
); 
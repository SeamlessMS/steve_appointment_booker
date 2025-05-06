"""
Steve Appointment Booker - Conversation Test
This script tests the full conversation functionality with a test lead.
"""

import os
import sys
import requests
import json
import logging
import time

# Add the parent directory to the Python path to import from backend
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
from backend.models import get_db, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_lead():
    """Create a test lead in the database"""
    # Initialize database
    init_db()
    
    with get_db() as conn:
        # Insert test lead
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO leads (name, phone, industry, category)
            VALUES (?, ?, ?, ?)
        ''', ('Test Lead', '+15551234567', 'Technology', 'Technology'))
        
        # Get the lead ID
        lead_id = cursor.lastrowid
        
        # Commit changes
        conn.commit()
        
        logger.info(f"Created test lead with ID: {lead_id}")
        return lead_id

def test_webhook_response(lead_id):
    """Test the webhook response handling"""
    # Simulate a user's response
    url = 'http://localhost:5001/webhook/response'
    params = {'lead_id': lead_id}
    data = {'SpeechResult': "Yes, I'm interested in learning more about your services."}
    
    logger.info("Testing webhook response...")
    response = requests.post(url, params=params, data=data)
    
    if response.status_code == 200:
        logger.info("Webhook response successful!")
        logger.info("Response TwiML:")
        logger.info(response.text)
        return True
    else:
        logger.error(f"Webhook response failed with status code: {response.status_code}")
        logger.error(f"Response: {response.text}")
        return False

def test_conversation():
    """Test the conversation functionality"""
    try:
        # Create test lead
        lead_id = create_test_lead()
        
        # Verify lead was created
        with get_db() as conn:
            lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
            if not lead:
                logger.error("Failed to create test lead")
                return
            logger.info(f"Successfully created lead: {dict(lead)}")
        
        # Make test call
        url = 'http://localhost:5001/api/call'
        data = {
            'lead_id': lead_id,
            'is_manual': True,
            'script': 'Hello, this is a test call to verify the conversation functionality.'
        }
        
        logger.info("Making test call...")
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            logger.info("Test call successful!")
            logger.info(f"Response: {response.json()}")
            
            # Wait a moment for the call to be established
            time.sleep(2)
            
            # Test webhook response
            test_webhook_response(lead_id)
            
            # Wait a moment for the response to be processed
            time.sleep(2)
            
            # Check call logs
            with get_db() as conn:
                logs = conn.execute('''
                    SELECT transcript, created_at 
                    FROM call_logs 
                    WHERE lead_id = ? 
                    ORDER BY created_at ASC
                ''', (lead_id,)).fetchall()
                
                if logs:
                    logger.info("\nConversation transcript:")
                    for log in logs:
                        logger.info(f"{log['transcript']}")
                else:
                    logger.warning("No conversation logs found")
        else:
            logger.error(f"Test call failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        raise

if __name__ == '__main__':
    test_conversation() 
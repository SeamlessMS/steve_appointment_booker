import os
import json
import logging
import functools
from datetime import datetime, time, timedelta
import pytz
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from models import get_db, init_db
from voice import place_call, get_voice_response, process_lead_response, update_industry_patterns, elevenlabs_tts
from config import get_config
from scraper import scrape_business_leads
from twilio.twiml.voice_response import VoiceResponse
import csv
import io
import urllib.parse
from twilio.rest import Client
import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize database
init_db()

# --- Authentication and Setup ---
@app.before_request
def setup():
    if not hasattr(app, 'db_initialized'):
        init_db()
        app.db_initialized = True

# API authentication decorator
def require_api_key(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth for webhook endpoints
        if request.path.startswith('/webhook'):
            return f(*args, **kwargs)
            
        config = get_config()
        api_key = config.get('API_KEY')
        
        # If no API key is configured, don't enforce authentication
        if not api_key:
            return f(*args, **kwargs)
            
        # Check for API key in headers or query parameters
        request_api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if request_api_key != api_key:
            return {'error': 'Unauthorized. Invalid or missing API key.'}, 401
            
        return f(*args, **kwargs)
    return decorated_function

# Apply the decorator to all /api routes
@app.before_request
def check_auth():
    if request.path.startswith('/api'):
        config = get_config()
        api_key = config.get('API_KEY')
        
        # If no API key is configured, don't enforce authentication
        if not api_key:
            return
            
        # Skip auth for API configuration endpoints
        if request.path == '/api/config' and request.method == 'GET':
            return
            
        # Check for API key in headers or query parameters
        request_api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if request_api_key != api_key:
            return {'error': 'Unauthorized. Invalid or missing API key.'}, 401

# Time restrictions for calls
def is_within_call_hours():
    """Check if current time is within acceptable calling hours based on configuration"""
    config = get_config()
    business_hours = config.get('BUSINESS_HOURS', {})
    
    # Get timezone from config
    tz_name = business_hours.get('timezone', 'US/Mountain')
    try:
        timezone = pytz.timezone(tz_name)
    except:
        # Fallback to Mountain time if invalid timezone
        timezone = pytz.timezone('US/Mountain')
    
    now = datetime.now(timezone)
    current_time = now.time()
    is_weekend = now.weekday() >= 5  # 5 = Saturday, 6 = Sunday
    
    # Parse business hours from config
    if is_weekend:
        # Check if weekend calling is enabled
        if not business_hours.get('weekend_enabled', False):
            return False
            
        # Parse weekend hours
        try:
            start_time = time(*map(int, business_hours.get('weekend_start', '10:00').split(':')))
            end_time = time(*map(int, business_hours.get('weekend_end', '14:00').split(':')))
        except:
            # Fallback to default weekend hours
            start_time = time(10, 0)
            end_time = time(14, 0)
    else:
        # Parse weekday hours
        try:
            start_time = time(*map(int, business_hours.get('weekday_start', '09:30').split(':')))
            end_time = time(*map(int, business_hours.get('weekday_end', '16:00').split(':')))
        except:
            # Fallback to default weekday hours
            start_time = time(9, 30)
            end_time = time(16, 0)
    
    return start_time <= current_time <= end_time

def is_call_in_progress(lead_id):
    """Check if a call is already in progress for this lead"""
    if not lead_id:
        return False
        
    with get_db() as conn:
        # Get the most recent call log entry
        recent_log = conn.execute('''
            SELECT * FROM call_logs 
            WHERE lead_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (lead_id,)).fetchone()
        
        if not recent_log:
            return False
            
        # Check if the call is in progress (started within the last 30 minutes)
        if recent_log['call_status'] in ['Started', 'In Progress']:
            try:
                created_at = datetime.strptime(recent_log['created_at'], '%Y-%m-%d %H:%M:%S')
                now = datetime.now()
                # If the call started within the last 30 minutes, consider it in progress
                if (now - created_at).total_seconds() < 1800:  # 30 minutes in seconds
                    return True
            except:
                pass
                
    return False

def should_allow_call(lead_id=None):
    """Determine if a call should be allowed based on time restrictions and call status"""
    # Check if we're in test mode
    config = get_config()
    if config.get('TEST_MODE', False):
        return True
        
    # If it's within call hours, always allow
    if is_within_call_hours():
        return True
        
    # If outside call hours, check if call is already in progress
    return is_call_in_progress(lead_id)

def log_outside_hours_attempt(lead_id=None, call_type="outbound"):
    """Log an attempt to make/receive calls outside of business hours"""
    mountain_tz = pytz.timezone('US/Mountain')
    now = datetime.now(mountain_tz)
    
    message = f"Call attempt {call_type} outside business hours at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    logger.warning(message)
    
    if lead_id:
        try:
            with get_db() as conn:
                conn.execute('''INSERT INTO call_logs 
                              (lead_id, call_status, transcript) 
                              VALUES (?, ?, ?)''',
                           (lead_id, 'Failed', f"System: {message} - Call blocked by time restrictions"))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log outside hours attempt: {str(e)}")
    
    return message

@app.route('/')
def index():
    return {'status': 'Mobile Solutions API running'}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    from datetime import datetime
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'ngrok_url': app.config.get('CALLBACK_URL', 'Not configured')
    }

# --- Twilio Webhook Routes ---
@app.route('/webhook', methods=['GET'])
def webhook_root():
    """Root webhook endpoint for testing connectivity"""
    return {
        'status': 'ok',
        'message': 'Webhook endpoint is working',
        'endpoints': [
            '/webhook/voice',
            '/webhook/response',
            '/webhook/status',
            '/webhook/recording'
        ]
    }

@app.route('/webhook/voice', methods=['GET', 'POST'])
def webhook_voice():
    """Handle incoming voice call from Twilio"""
    # If it's a GET request, return a simple response for testing
    if request.method == 'GET':
        return {
            'status': 'ok',
            'message': 'Webhook voice endpoint is working',
            'usage': 'This endpoint is designed to be called by Twilio with POST requests'
        }
        
    # Get lead_id if provided
    lead_id = request.args.get('lead_id')
    
    # Check time restrictions
    if not should_allow_call(lead_id):
        log_outside_hours_attempt(lead_id, "inbound webhook")
        response = VoiceResponse()
        response.say("We are currently outside of business hours. Our calling hours are Monday through Friday, 9:30 AM to 4:00 PM Mountain Time. Goodbye.")
        response.hangup()
        return str(response)
    
    # Get initial script from query params or use default
    script = request.args.get('script', "Hello, this is Steve with Seamless Mobile Services. I'll be brief.")
    
    # Get lead data if a lead_id is provided
    lead_data = None
    if lead_id:
        with get_db() as conn:
            lead_data = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
            if lead_data:
                lead_data = dict(lead_data)
    
    # Generate TwiML response for the call
    response = get_voice_response(script, lead_data)
    
    # Store initial conversation in call_logs if lead_id is provided
    if lead_id:
        with get_db() as conn:
            conn.execute('''INSERT INTO call_logs 
                          (lead_id, call_status, transcript) 
                          VALUES (?, ?, ?)''',
                       (lead_id, 'Started', f"Bot: {script}"))
            conn.commit()
    
    return str(response)

@app.route('/webhook/amd_status', methods=['GET', 'POST'])
def webhook_amd_status():
    """Handle answering machine detection status callback from Twilio"""
    # If it's a GET request, return a simple response for testing
    if request.method == 'GET':
        return {
            'status': 'ok',
            'message': 'AMD status webhook endpoint is working',
            'usage': 'This endpoint is designed to be called by Twilio with POST requests'
        }
    
    # Get lead_id if provided
    lead_id = request.args.get('lead_id')
    
    # Get AMD detection result
    answered_by = request.values.get('AnsweredBy', 'unknown')
    machine_detection_duration = request.values.get('MachineDetectionDuration', '0')
    call_sid = request.values.get('CallSid', 'unknown')
    
    # Log AMD status for debugging
    logger.info(f"AMD Status: Call {call_sid} was answered by: {answered_by} (detection took {machine_detection_duration}ms)")
    
    # Store AMD result in database if lead_id is provided
    if lead_id:
        with get_db() as conn:
            conn.execute('''INSERT INTO call_logs 
                          (lead_id, call_status, transcript, call_sid) 
                          VALUES (?, ?, ?, ?)''',
                       (lead_id, 'AMD Detection', f"Call was answered by: {answered_by} (detection took {machine_detection_duration}ms)", call_sid))
            conn.commit()
    
    # Check if this is a voicemail/answering machine
    is_voicemail = answered_by in ['machine_end_beep', 'machine_end_silence', 'machine_end_other']
    
    if is_voicemail:
        logger.info(f"Voicemail detected for call {call_sid}. Updating TwiML for voicemail.")
        
        # Get initial script from the lead data or use default
        script = None
        lead_data = None
        if lead_id:
            with get_db() as conn:
                lead_result = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
                if lead_result:
                    lead_data = dict(lead_result)
                    # TODO: In the future, we might want to get a personalized voicemail script
                    # For now we'll use a default
        
        if not script:
            script = "I'm calling about helping your company save money on mobile device management. Our clients typically save 20% on their mobile costs."
        
        # Generate new TwiML for voicemail
        from voice import get_voice_response
        voicemail_twiml = get_voice_response(script, lead_data=lead_data, is_voicemail=True)
        
        # Store the voicemail TwiML in the call_logs table with the call_sid
        with get_db() as conn:
            # First check if we already have a voicemail TwiML entry for this call_sid
            existing = conn.execute('SELECT id FROM call_logs WHERE call_sid = ? AND call_status = ?', 
                                   (call_sid, 'VoicemailTwiML')).fetchone()
            
            if existing:
                # Update the existing entry
                conn.execute('UPDATE call_logs SET transcript = ? WHERE id = ?', 
                           (voicemail_twiml, existing['id']))
            else:
                # Create a new entry
                conn.execute('INSERT INTO call_logs (lead_id, call_status, transcript, call_sid) VALUES (?, ?, ?, ?)',
                           (lead_id, 'VoicemailTwiML', voicemail_twiml, call_sid))
            
            conn.commit()
        
        # Update the call with new TwiML for voicemail
        try:
            config = get_config()
            client = Client(config['TWILIO_ACCOUNT_SID'], config['TWILIO_AUTH_TOKEN'])
            
            # Get webhook URL 
            webhook_url = config.get('CALLBACK_URL', 'http://localhost:5001').rstrip('/webhook')
            
            # Create URL for voicemail TwiML
            voicemail_twiml_url = f"{webhook_url}/webhook/voicemail_twiml?call_sid={call_sid}"
            
            # Update the call to use the new TwiML URL
            client.calls(call_sid).update(
                method='GET',
                url=voicemail_twiml_url
            )
            
            logger.info(f"Successfully updated call {call_sid} to use voicemail TwiML.")
        except Exception as e:
            logger.error(f"Error updating call for voicemail: {str(e)}")
    
    # Return a 200 OK response to Twilio
    return ('', 204)

# Add a new endpoint to serve the voicemail TwiML
@app.route('/webhook/voicemail_twiml', methods=['GET'])
def voicemail_twiml():
    """Serve the voicemail TwiML that was generated in the AMD callback"""
    call_sid = request.args.get('call_sid', '')
    
    # Retrieve the stored TwiML for this call_sid
    if call_sid:
        with get_db() as conn:
            result = conn.execute('SELECT transcript FROM call_logs WHERE call_sid = ? AND call_status = ?',
                               (call_sid, 'VoicemailTwiML')).fetchone()
            
            if result and result['transcript']:
                logger.info(f"Retrieved voicemail TwiML for call {call_sid}")
                return result['transcript']
    
    # If no TwiML found or no call_sid provided, generate a default response
    logger.warning(f"No voicemail TwiML found for call {call_sid}, using default")
    response = VoiceResponse()
    response.say("Hello, this is Steve from Seamless Mobile Services with a message about mobile device management. Please call us back at your convenience. Thank you.")
    response.hangup()
    
    return str(response)

@app.route('/webhook/response', methods=['GET', 'POST'])
def webhook_response():
    """Handle speech recognition results from Twilio"""
    # If it's a GET request, return a simple response for testing
    if request.method == 'GET':
        return {
            'status': 'ok',
            'message': 'Webhook response endpoint is working',
            'usage': 'This endpoint is designed to be called by Twilio with POST requests'
        }
    
    # Get lead_id if provided
    lead_id = request.args.get('lead_id')
    
    # Check time restrictions
    if not should_allow_call(lead_id):
        log_outside_hours_attempt(lead_id, "inbound response")
        response = VoiceResponse()
        response.say("I apologize, but we are now outside of business hours. I'll have to call you back during our business hours, which are Monday through Friday, 9:30 AM to 4:00 PM Mountain Time. Thank you and goodbye.")
        response.hangup()
        return str(response)
    
    # Get speech recognition result from Twilio
    speech_result = request.values.get('SpeechResult')
    
    # Get lead data
    lead_data = None
    conversation_history = []
    
    if lead_id:
        with get_db() as conn:
            lead_data = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
            if lead_data:
                lead_data = dict(lead_data)
                
            # Retrieve conversation history from call logs
            logs = conn.execute('SELECT transcript FROM call_logs WHERE lead_id = ? ORDER BY created_at ASC', 
                             (lead_id,)).fetchall()
            
            # Parse conversation history into format for LLM
            for log in logs:
                transcript = log['transcript']
                if transcript.startswith('Bot: '):
                    conversation_history.append({"role": "assistant", "content": transcript[5:]})
                elif transcript.startswith('Lead: '):
                    conversation_history.append({"role": "user", "content": transcript[6:]})
    
    # Process the lead's response
    result = process_lead_response(
        speech_result, 
        lead_data, 
        conversation_history
    )
    
    # Handle different return formats (compatibility with older and newer versions)
    if len(result) == 4:
        # New version with follow-up recommendation
        ai_response, updated_history, conversation_result, follow_up = result
    else:
        # Old version without follow-up recommendation
        ai_response, updated_history, conversation_result = result
        follow_up = None
    
    # Generate voice response for the next interaction
    response = get_voice_response(ai_response, lead_data, updated_history)
    
    # Save the transcript to call logs
    if lead_id:
        with get_db() as conn:
            # Save the lead's response
            conn.execute('''INSERT INTO call_logs 
                          (lead_id, call_status, transcript) 
                          VALUES (?, ?, ?)''',
                       (lead_id, 'In Progress', f"Lead: {speech_result}"))
            
            # Save the bot's response
            conn.execute('''INSERT INTO call_logs 
                          (lead_id, call_status, transcript) 
                          VALUES (?, ?, ?)''',
                       (lead_id, 'In Progress', f"Bot: {ai_response}"))
            
            # If the conversation is complete, update the lead status
            if conversation_result["status"] == "complete":
                if conversation_result["appointment_set"]:
                    # Update lead status and add appointment
                    conn.execute('''UPDATE leads SET 
                                  status = ?, 
                                  qualification_status = ?,
                                  uses_mobile_devices = ?,
                                  employee_count = ?,
                                  appointment_date = ?,
                                  appointment_time = ?
                                  WHERE id = ?''',
                               ('Appointment Set', 'Qualified', 
                                conversation_result.get("uses_mobile", "Yes"),
                                conversation_result.get("employee_count", 10),
                                conversation_result.get("appointment_date", ""),
                                conversation_result.get("appointment_time", ""),
                                lead_id))
                    
                    # Create appointment if date and time were extracted
                    if conversation_result.get("appointment_date") and conversation_result.get("appointment_time"):
                        conn.execute('''INSERT INTO appointments 
                                      (lead_id, date, time, status, medium) 
                                      VALUES (?, ?, ?, ?, ?)''',
                                   (lead_id, 
                                    conversation_result["appointment_date"], 
                                    conversation_result["appointment_time"],
                                    'Scheduled',
                                    'Phone'))
                else:
                    # Update lead status based on qualification
                    qual_status = 'Qualified' if conversation_result.get("qualified", False) else 'Not Qualified'
                    conn.execute('''UPDATE leads SET 
                                  status = ?, 
                                  qualification_status = ?,
                                  uses_mobile_devices = ?,
                                  employee_count = ?
                                  WHERE id = ?''',
                               ('Completed', qual_status, 
                                conversation_result.get("uses_mobile", "Unknown"),
                                conversation_result.get("employee_count", 0),
                                lead_id))
                
                # If follow-up is recommended, create a follow-up record
                if follow_up and follow_up["recommended"] and follow_up["scheduled_time"]:
                    try:
                        # Format datetime for SQLite
                        scheduled_time_str = follow_up["scheduled_time"].strftime('%Y-%m-%d %H:%M:%S')
                        
                        conn.execute('''INSERT INTO follow_ups 
                                      (lead_id, scheduled_time, status, priority, reason) 
                                      VALUES (?, ?, ?, ?, ?)''',
                                   (lead_id, 
                                    scheduled_time_str,
                                    'Pending',
                                    follow_up["priority"],
                                    follow_up["reason"]))
                        
                        # Also update the lead with a note about the scheduled follow-up
                        conn.execute('''UPDATE leads SET 
                                      notes = CASE 
                                         WHEN notes IS NULL OR notes = '' THEN ? 
                                         ELSE notes || char(10) || ? 
                                      END
                                      WHERE id = ?''',
                                   (f"Follow-up scheduled for {scheduled_time_str}: {follow_up['reason']}",
                                    f"Follow-up scheduled for {scheduled_time_str}: {follow_up['reason']}",
                                    lead_id))
                        
                        # Log the follow-up
                        logger.info(f"Follow-up scheduled for lead {lead_id} at {scheduled_time_str}: {follow_up['reason']}")
                    except Exception as e:
                        logger.error(f"Error scheduling follow-up: {str(e)}")
            
            conn.commit()
    
    return str(response)

@app.route('/webhook/status', methods=['GET', 'POST'])
def webhook_status():
    """Handle call status callbacks from Twilio"""
    # If it's a GET request, return a simple response for testing
    if request.method == 'GET':
        return {
            'status': 'ok',
            'message': 'Webhook status endpoint is working',
            'usage': 'This endpoint is designed to be called by Twilio with POST requests'
        }
        
    call_sid = request.values.get('CallSid')
    call_status = request.values.get('CallStatus')
    
    # Get the lead_id associated with this call
    lead_id = request.args.get('lead_id')
    
    if lead_id and call_status in ['completed', 'failed', 'busy', 'no-answer']:
        with get_db() as conn:
            # Update the lead status if call ended without setting appointment
            current = conn.execute('SELECT status FROM leads WHERE id = ?', (lead_id,)).fetchone()
            
            # Only update if status is still "Calling" (not changed by webhook)
            if current and current['status'] == 'Calling':
                conn.execute('UPDATE leads SET status = ? WHERE id = ?', 
                           ('Call Attempted', lead_id))
                
                # Log the call outcome
                conn.execute('''INSERT INTO call_logs 
                              (lead_id, call_status, transcript) 
                              VALUES (?, ?, ?)''',
                           (lead_id, call_status, f"Call ended with status: {call_status}"))
                
                conn.commit()
    
    return '', 204  # No content needed for status callbacks

@app.route('/webhook/recording', methods=['GET', 'POST'])
def webhook_recording():
    """Handle recording status callbacks from Twilio"""
    # If it's a GET request, return a simple response for testing
    if request.method == 'GET':
        return {
            'status': 'ok',
            'message': 'Webhook recording endpoint is working',
            'usage': 'This endpoint is designed to be called by Twilio with POST requests'
        }
        
    recording_url = request.values.get('RecordingUrl')
    recording_sid = request.values.get('RecordingSid')
    call_sid = request.values.get('CallSid')
    recording_status = request.values.get('RecordingStatus')
    
    # Get the lead_id associated with this call
    lead_id = request.args.get('lead_id')
    
    if lead_id and recording_status == 'completed' and recording_url:
        with get_db() as conn:
            # Update the call logs to include the recording URL
            conn.execute('''UPDATE call_logs 
                          SET transcript = transcript || '\nRecording URL: ' || ? 
                          WHERE lead_id = ? AND call_status IN ('Started', 'In Progress')
                          ORDER BY created_at DESC LIMIT 1''',
                       (recording_url, lead_id))
                
            # Also save a separate log entry for the recording
            conn.execute('''INSERT INTO call_logs 
                          (lead_id, call_status, transcript) 
                          VALUES (?, ?, ?)''',
                       (lead_id, 'Recording', f"Call recording available at: {recording_url}"))
            
            conn.commit()
            
            # Log the recording URL
            logger.info(f"Call recording for lead {lead_id}: {recording_url}")
    
    return '', 204  # No content response

# --- Leads CRUD ---
@app.route('/api/leads', methods=['GET'])
def get_leads():
    # Check if we're filtering by status
    status = request.args.get('status')
    
    with get_db() as conn:
        if status:
            # Filter leads by status
            leads = conn.execute('SELECT * FROM leads WHERE status = ?', (status,)).fetchall()
        else:
            # Get all leads
            leads = conn.execute('SELECT * FROM leads').fetchall()
        
        return jsonify([dict(row) for row in leads])

@app.route('/api/leads', methods=['POST'])
def add_lead():
    data = request.json
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO leads (name, phone, category, address, website, status, 
                 employee_count, uses_mobile_devices, industry, city, state) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data['name'], data['phone'], data['category'], data['address'], 
                   data.get('website', ''), data.get('status', 'Not Called'), 
                   data.get('employee_count', 0), data.get('uses_mobile_devices', 'Unknown'),
                   data.get('industry', ''), data.get('city', ''), data.get('state', '')))
        conn.commit()
        return {'id': c.lastrowid}, 201

@app.route('/api/leads/<int:lead_id>', methods=['PATCH'])
def update_lead(lead_id):
    try:
        data = request.json
        with get_db() as conn:
            conn.execute('UPDATE leads SET name = COALESCE(?, name), phone = COALESCE(?, phone), email = COALESCE(?, email), company = COALESCE(?, company), position = COALESCE(?, position), industry = COALESCE(?, industry), location = COALESCE(?, location), status = COALESCE(?, status), employee_count = COALESCE(?, employee_count), qualification_status = COALESCE(?, qualification_status), uses_mobile_devices = COALESCE(?, uses_mobile_devices), address = COALESCE(?, address), notes = COALESCE(?, notes), website = COALESCE(?, website), updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                       (data.get('name'), data.get('phone'), data.get('email'), data.get('company'), data.get('position'), data.get('industry'), data.get('location'), data.get('status'), data.get('employee_count'), data.get('qualification_status'), data.get('uses_mobile_devices'), data.get('address'), data.get('notes'), data.get('website'), lead_id))
            conn.commit()
        
        return {'message': 'Lead updated successfully'}
    except Exception as e:
        print(f"Error: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/api/leads/<int:lead_id>', methods=['DELETE'])
def delete_lead(lead_id):
    try:
        with get_db() as conn:
            # Check if lead exists
            lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
            if not lead:
                return {'error': 'Lead not found'}, 404
                
            # Delete call logs associated with this lead
            conn.execute('DELETE FROM call_logs WHERE lead_id = ?', (lead_id,))
            
            # Delete follow-ups associated with this lead
            conn.execute('DELETE FROM follow_ups WHERE lead_id = ?', (lead_id,))
            
            # Delete appointments associated with this lead
            conn.execute('DELETE FROM appointments WHERE lead_id = ?', (lead_id,))
            
            # Finally delete the lead
            conn.execute('DELETE FROM leads WHERE id = ?', (lead_id,))
            conn.commit()
        
        return {'message': 'Lead deleted successfully'}
    except Exception as e:
        print(f"Error deleting lead: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/api/leads/batch-delete', methods=['POST'])
def batch_delete_leads():
    try:
        data = request.json
        lead_ids = data.get('lead_ids', [])
        
        if not lead_ids:
            return {'error': 'No lead IDs provided'}, 400
            
        with get_db() as conn:
            # Prepare placeholder string for SQL IN clause
            placeholders = ','.join(['?' for _ in lead_ids])
            
            # Delete associated records first
            conn.execute(f'DELETE FROM call_logs WHERE lead_id IN ({placeholders})', lead_ids)
            conn.execute(f'DELETE FROM follow_ups WHERE lead_id IN ({placeholders})', lead_ids)
            conn.execute(f'DELETE FROM appointments WHERE lead_id IN ({placeholders})', lead_ids)
            
            # Delete the leads
            result = conn.execute(f'DELETE FROM leads WHERE id IN ({placeholders})', lead_ids)
            conn.commit()
            
            deleted_count = result.rowcount
        
        return {'message': f'{deleted_count} leads deleted successfully'}
    except Exception as e:
        print(f"Error batch deleting leads: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/api/scrape', methods=['POST'])
def scrape_new_leads():
    config = get_config()
    # Get location and industry from request or use default
    location = request.json.get('location', 'Denver, CO')
    industry = request.json.get('industry', 'Plumbing')
    limit = request.json.get('limit', 30)
    
    # Call the scraper for business leads
    scraped = scrape_business_leads(location=location, industry=industry, limit=limit)
    
    with get_db() as conn:
        c = conn.cursor()
        new_ids = []
        for lead in scraped:
            c.execute('''INSERT INTO leads (
                    name, phone, category, address, website, status, 
                    employee_count, industry, city, state, uses_mobile_devices
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (lead['name'], lead['phone'], lead['category'], lead['address'], 
                       lead.get('website', ''), 'Not Called', lead.get('employee_count', 0),
                       lead.get('industry', ''), lead.get('city', ''), lead.get('state', ''),
                       'Unknown'))
            new_ids.append(c.lastrowid)
        conn.commit()
    
    # Optionally sync with Zoho CRM if credentials are present
    if config.get('ZOHO_REFRESH_TOKEN') and config.get('ZOHO_CLIENT_ID') and config.get('ZOHO_CLIENT_SECRET'):
        sync_leads_to_zoho(new_ids)
    
    is_dummy = not config['BRIGHTDATA_API_TOKEN']
    return {'inserted_ids': new_ids, 'count': len(new_ids), 'dummy': is_dummy}

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'GET':
        return jsonify(get_config())
    else:
        data = request.json or {}
        save_config(data)
        return {'status': 'updated'}

# --- Call Logs ---
@app.route('/api/call_logs', methods=['POST'])
def add_call_log():
    data = request.json
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO call_logs (lead_id, call_status, transcript) VALUES (?, ?, ?)''',
                  (data['lead_id'], data['call_status'], data.get('transcript', '')))
        conn.commit()
        return {'id': c.lastrowid}, 201

@app.route('/api/call_logs/<int:lead_id>', methods=['GET'])
def get_call_logs(lead_id):
    with get_db() as conn:
        logs = conn.execute('SELECT * FROM call_logs WHERE lead_id = ? ORDER BY created_at DESC', (lead_id,)).fetchall()
        return jsonify([dict(row) for row in logs])

@app.route('/api/call', methods=['POST'])
def call_lead():
    data = request.json
    lead_id = data['lead_id']
    script = data.get('script')
    config = get_config()
    
    # Get manual flag - if True, bypass time restrictions
    is_manual = data.get('is_manual', False)
    
    logger.info(f"Attempting to call lead {lead_id}")
    logger.info(f"Config: {json.dumps(config, indent=2)}")
    
    # Check time restrictions - only if not a manual call
    if not is_manual and not should_allow_call(lead_id):
        message = log_outside_hours_attempt(lead_id, "outbound")
        return {
            'error': 'Outside of calling hours', 
            'message': 'Calls can only be made Monday through Friday, 9:30 AM to 4:00 PM Mountain Time.'
        }, 400
    
    # Get lead info to generate script if not provided
    with get_db() as conn:
        lead_row = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead_row:
            logger.error(f"Lead {lead_id} not found")
            return {'error': 'Lead not found'}, 404
        
        # Convert SQLite Row to dictionary
        lead = dict(lead_row)
        logger.info(f"Lead data: {json.dumps(lead, indent=2)}")
        
        # Generate script based on lead data if not provided
        if not script:
            contact_name = lead['name'].split()[0] if lead['name'] else "there"
            company_name = lead['name']
            industry = lead.get('industry', lead.get('category', 'business'))
            city = lead.get('city', 'your area')
            
            # Steve Schiffman-style script
            script = f"Hello, is this {contact_name}? This is Steve with Seamless Mobile Services. I'll be brief. I understand your company provides {industry} services in {city}. Quick question: do your field crews use mobile phones or tablets for work?"
    
    # Check if we should use dummy mode
    dummy_reasons = []
    if config.get('TEST_MODE', False):
        dummy_reasons.append("TEST_MODE is enabled")
    if not config.get('TWILIO_ACCOUNT_SID'):
        dummy_reasons.append("TWILIO_ACCOUNT_SID is missing")
    if not config.get('TWILIO_AUTH_TOKEN'):
        dummy_reasons.append("TWILIO_AUTH_TOKEN is missing")
    if not config.get('ELEVENLABS_API_KEY'):
        dummy_reasons.append("ELEVENLABS_API_KEY is missing")
    if not config.get('ELEVENLABS_VOICE_ID'):
        dummy_reasons.append("ELEVENLABS_VOICE_ID is missing")
    if not config.get('TWILIO_PHONE_NUMBER') or config.get('TWILIO_PHONE_NUMBER').strip() == '':
        dummy_reasons.append("TWILIO_PHONE_NUMBER is missing or empty")
    
    if dummy_reasons:
        logger.warning(f"Using dummy mode due to: {', '.join(dummy_reasons)}")
        logger.info(f"TEST_MODE: {config.get('TEST_MODE')}")
        logger.info(f"TWILIO_ACCOUNT_SID: {config.get('TWILIO_ACCOUNT_SID')}")
        logger.info(f"TWILIO_AUTH_TOKEN: {config.get('TWILIO_AUTH_TOKEN')}")
        logger.info(f"ELEVENLABS_API_KEY: {config.get('ELEVENLABS_API_KEY')}")
        logger.info(f"ELEVENLABS_VOICE_ID: {config.get('ELEVENLABS_VOICE_ID')}")
        logger.info(f"TWILIO_PHONE_NUMBER: {config.get('TWILIO_PHONE_NUMBER')}")
        logger.info(f"Full config: {json.dumps(config, indent=2)}")
        
        with get_db() as conn:
            conn.execute('UPDATE leads SET status = ? WHERE id = ?', ("Calling", lead_id))
            conn.commit()
        return {'call_sid': 'dummy-call', 'dummy': True}
    
    # Real mode
    try:
        logger.info("Attempting to place real call")
        call_sid = place_call(lead['phone'], script)
        logger.info(f"Call placed successfully with SID: {call_sid}")
        with get_db() as conn:
            conn.execute('UPDATE leads SET status = ? WHERE id = ?', ("Calling", lead_id))
            conn.commit()
        return {'call_sid': call_sid}
    except Exception as e:
        logger.error(f"Error placing call: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/api/appointments', methods=['GET'])
def get_appointments():
    with get_db() as conn:
        appointments = conn.execute('''
            SELECT a.*, l.name as lead_name, l.phone as lead_phone 
            FROM appointments a 
            JOIN leads l ON a.lead_id = l.id 
            ORDER BY a.date, a.time
        ''').fetchall()
        return jsonify([dict(row) for row in appointments])

@app.route('/api/appointments', methods=['POST'])
def add_appointment():
    data = request.json
    lead_id = data['lead_id']
    date = data['date']
    time = data['time']
    status = data.get('status', 'Scheduled')
    medium = data.get('medium', 'Phone')
    
    with get_db() as conn:
        # Add appointment
        c = conn.cursor()
        c.execute('''INSERT INTO appointments (lead_id, date, time, status, medium) 
                   VALUES (?, ?, ?, ?, ?)''',
                  (lead_id, date, time, status, medium))
        appointment_id = c.lastrowid
        
        # Update lead status and appointment info
        conn.execute('''UPDATE leads SET 
                      status = ?, 
                      qualification_status = ?, 
                      appointment_date = ?, 
                      appointment_time = ? 
                      WHERE id = ?''',
                    ('Appointment Set', 'Qualified', date, time, lead_id))
        conn.commit()
        
        # Sync with Zoho if configured
        config = get_config()
        if config.get('ZOHO_REFRESH_TOKEN') and lead_id:
            create_zoho_appointment(lead_id, date, time, medium)
        
        return {'id': appointment_id}, 201

@app.route('/api/appointments/<int:appointment_id>', methods=['PATCH'])
def update_appointment(appointment_id):
    data = request.json
    
    fields = []
    values = []
    for k in ['date', 'time', 'status', 'medium']:
        if k in data:
            fields.append(f"{k} = ?")
            values.append(data[k])
    
    if not fields:
        return {'error': 'No fields to update'}, 400
    
    values.append(appointment_id)
    
    with get_db() as conn:
        # Get the appointment to update
        appointment = conn.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,)).fetchone()
        if not appointment:
            return {'error': 'Appointment not found'}, 404
        
        # Update the appointment
        conn.execute(f"UPDATE appointments SET {', '.join(fields)} WHERE id = ?", values)
        
        # If date or time changed, update the lead record as well
        if 'date' in data or 'time' in data:
            lead_updates = []
            lead_values = []
            
            if 'date' in data:
                lead_updates.append("appointment_date = ?")
                lead_values.append(data['date'])
            
            if 'time' in data:
                lead_updates.append("appointment_time = ?")
                lead_values.append(data['time'])
            
            if lead_updates:
                lead_values.append(appointment['lead_id'])
                conn.execute(f"UPDATE leads SET {', '.join(lead_updates)} WHERE id = ?", lead_values)
        
        conn.commit()
        
        # Sync with Zoho if configured
        config = get_config()
        if config.get('ZOHO_REFRESH_TOKEN') and 'date' in data or 'time' in data:
            # Get the updated appointment info
            updated = conn.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,)).fetchone()
            update_zoho_appointment(appointment['lead_id'], updated['date'], updated['time'], updated['medium'])
        
        return {'status': 'updated'}

@app.route('/api/qualify/<int:lead_id>', methods=['POST'])
def qualify_lead(lead_id):
    data = request.json
    is_qualified = data.get('qualified', False)
    uses_mobile = data.get('uses_mobile_devices', 'Unknown')
    employee_count = data.get('employee_count', 0)
    notes = data.get('notes', '')
    
    qualification_status = 'Qualified' if is_qualified else 'Not Qualified'
    
    with get_db() as conn:
        conn.execute('''UPDATE leads SET 
                      qualification_status = ?, 
                      uses_mobile_devices = ?, 
                      employee_count = ?,
                      notes = ?
                      WHERE id = ?''',
                    (qualification_status, uses_mobile, employee_count, notes, lead_id))
        conn.commit()
        
        # Sync with Zoho if configured
        config = get_config()
        if config.get('ZOHO_REFRESH_TOKEN'):
            update_zoho_lead_qualification(lead_id, qualification_status, uses_mobile, employee_count, notes)
        
        return {'status': 'updated', 'qualification_status': qualification_status}

@app.route('/api/availability', methods=['GET'])
def get_availability():
    """Get available time slots for appointments"""
    date = request.args.get('date')
    
    # Default available hours (9am to 5pm)
    available_hours = list(range(9, 17))
    
    # Check which slots are already booked
    if date:
        with get_db() as conn:
            # Get all appointments for the requested date
            booked = conn.execute(
                'SELECT time FROM appointments WHERE date = ? AND status != "Canceled"', 
                (date,)
            ).fetchall()
            
            # Remove booked times from available hours
            for appt in booked:
                try:
                    hour = int(appt['time'].split(':')[0])
                    if hour in available_hours:
                        available_hours.remove(hour)
                except (ValueError, IndexError):
                    pass
    
    # Format times as "HH:00"
    available_slots = [f"{hour:02d}:00" for hour in available_hours]
    
    # Alternatively, check Zoho Calendar if configured
    config = get_config()
    if date and config.get('ZOHO_REFRESH_TOKEN') and config.get('ZOHO_CLIENT_ID'):
        zoho_slots = get_zoho_availability(date)
        if zoho_slots:
            # Use Zoho's availability instead
            return jsonify(zoho_slots)
    
    return jsonify(available_slots)

@app.route('/api/check_business_hours', methods=['GET'])
def check_business_hours():
    """Check if current time is within business hours"""
    config = get_config()
    business_hours = config.get('BUSINESS_HOURS', {})
    
    # Get timezone from config
    tz_name = business_hours.get('timezone', 'US/Mountain')
    try:
        timezone = pytz.timezone(tz_name)
    except:
        # Fallback to Mountain time if invalid timezone
        timezone = pytz.timezone('US/Mountain')
    
    now = datetime.now(timezone)
    is_weekend = now.weekday() >= 5  # 5 = Saturday, 6 = Sunday
    within_hours = is_within_call_hours()
    
    # Format times for display
    weekday_start = business_hours.get('weekday_start', '09:30')
    weekday_end = business_hours.get('weekday_end', '16:00')
    weekend_enabled = business_hours.get('weekend_enabled', False)
    weekend_start = business_hours.get('weekend_start', '10:00')
    weekend_end = business_hours.get('weekend_end', '14:00')
    
    # Format display strings
    try:
        weekday_start_display = datetime.strptime(weekday_start, '%H:%M').strftime('%I:%M %p')
        weekday_end_display = datetime.strptime(weekday_end, '%H:%M').strftime('%I:%M %p')
        weekend_start_display = datetime.strptime(weekend_start, '%H:%M').strftime('%I:%M %p')
        weekend_end_display = datetime.strptime(weekend_end, '%H:%M').strftime('%I:%M %p')
    except:
        weekday_start_display = '9:30 AM'
        weekday_end_display = '4:00 PM'
        weekend_start_display = '10:00 AM'
        weekend_end_display = '2:00 PM'
    
    return {
        'within_business_hours': within_hours,
        'current_time': now.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'is_weekend': is_weekend,
        'business_hours': {
            'timezone': tz_name,
            'days': 'Monday-Friday' if not weekend_enabled else 'Monday-Sunday',
            'weekday_start': weekday_start_display,
            'weekday_end': weekday_end_display,
            'weekend_enabled': weekend_enabled,
            'weekend_start': weekend_start_display,
            'weekend_end': weekend_end_display
        }
    }

# --- Zoho Integration Functions ---

def get_zoho_access_token():
    """Get an access token for Zoho CRM API"""
    config = get_config()
    refresh_token = config.get('ZOHO_REFRESH_TOKEN')
    client_id = config.get('ZOHO_CLIENT_ID')
    client_secret = config.get('ZOHO_CLIENT_SECRET')
    
    if not refresh_token or not client_id or not client_secret:
        return None
    
    url = "https://accounts.zoho.com/oauth/v2/token"
    data = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json().get('access_token')
    except Exception as e:
        logger.error(f"Error getting Zoho access token: {str(e)}")
    
    return None

def sync_leads_to_zoho(lead_ids):
    """Sync leads to Zoho CRM"""
    access_token = get_zoho_access_token()
    if not access_token:
        return False
    
    config = get_config()
    org_id = config.get('ZOHO_ORG_ID')
    department_id = config.get('ZOHO_DEPARTMENT_ID')
    
    with get_db() as conn:
        for lead_id in lead_ids:
            lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
            if not lead:
                continue
            
            # Format lead data for Zoho
            lead_data = {
                "data": [{
                    "Company": lead['name'],
                    "Phone": lead['phone'],
                    "Industry": lead['industry'] or lead['category'],
                    "Address": lead['address'],
                    "Website": lead['website'],
                    "City": lead['city'],
                    "State": lead['state'],
                    "Description": f"Employee Count: {lead['employee_count']}\nUses Mobile Devices: {lead['uses_mobile_devices']}",
                    "Lead_Source": "AI Assistant",
                    "Department": department_id
                }]
            }
            
            # Create lead in Zoho
            url = "https://www.zohoapis.com/crm/v2/Leads"
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Content-Type": "application/json"
            }
            
            if org_id:
                headers["X-ORGID"] = org_id
                
            try:
                response = requests.post(url, headers=headers, json=lead_data)
                if response.status_code == 201:
                    zoho_id = response.json()['data'][0]['details']['id']
                    # Store Zoho ID in local DB for future reference
                    conn.execute('UPDATE leads SET notes = ? WHERE id = ?', 
                               (f"Zoho Lead ID: {zoho_id}", lead_id))
                    conn.commit()
            except Exception as e:
                logger.error(f"Error creating lead in Zoho: {str(e)}")
    
    return True

def create_zoho_appointment(lead_id, date, time, medium):
    """Create an appointment in Zoho Calendar"""
    access_token = get_zoho_access_token()
    if not access_token:
        return False
    
    config = get_config()
    org_id = config.get('ZOHO_ORG_ID')
    department_id = config.get('ZOHO_DEPARTMENT_ID')
    
    with get_db() as conn:
        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return False
        
        # Extract Zoho Lead ID if available
        zoho_lead_id = None
        if lead['notes'] and "Zoho Lead ID:" in lead['notes']:
            try:
                zoho_lead_id = lead['notes'].split("Zoho Lead ID:")[1].strip().split()[0]
            except:
                pass
        
        # Format appointment data
        start_datetime = f"{date}T{time}:00"
        end_datetime = increment_time(start_datetime, minutes=30)
        
        # Create event in Zoho Calendar
        url = "https://www.zohoapis.com/crm/v2/Events"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json"
        }
        
        if org_id:
            headers["X-ORGID"] = org_id
        
        event_data = {
            "data": [{
                "Subject": f"Meeting with {lead['name']}",
                "Start_DateTime": start_datetime,
                "End_DateTime": end_datetime,
                "Event_Title": f"Mobile Solutions Consultation with {lead['name']}",
                "Location": "Phone Call" if medium == "Phone" else "Zoom Meeting",
                "Department": department_id
            }]
        }
        
        # Link to lead if we have the Zoho Lead ID
        if zoho_lead_id:
            event_data["data"][0]["What_Id"] = zoho_lead_id
            event_data["data"][0]["$se_module"] = "Leads"
        
        try:
            response = requests.post(url, headers=headers, json=event_data)
            if response.status_code == 201:
                event_id = response.json()['data'][0]['details']['id']
                # Store Event ID in appointment notes for future reference
                with get_db() as conn:
                    appointment = conn.execute(
                        'SELECT id FROM appointments WHERE lead_id = ? AND date = ? AND time = ?',
                        (lead_id, date, time)
                    ).fetchone()
                    if appointment:
                        conn.execute('UPDATE appointments SET notes = ? WHERE id = ?',
                                   (f"Zoho Event ID: {event_id}", appointment['id']))
                        conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error creating event in Zoho: {str(e)}")
    
    return False

def update_zoho_appointment(lead_id, date, time, medium):
    """Update an existing appointment in Zoho"""
    access_token = get_zoho_access_token()
    if not access_token:
        return False
    
    config = get_config()
    org_id = config.get('ZOHO_ORG_ID')
    
    with get_db() as conn:
        # Get the appointment details from our database
        appointment = conn.execute('''
            SELECT a.*, l.notes 
            FROM appointments a 
            JOIN leads l ON a.lead_id = l.id 
            WHERE a.lead_id = ? AND a.date = ? AND a.time = ?
        ''', (lead_id, date, time)).fetchone()
        
        if not appointment:
            return False
        
        # Extract Zoho Event ID if available in notes
        zoho_event_id = None
        if appointment['notes'] and "Zoho Event ID:" in appointment['notes']:
            try:
                zoho_event_id = appointment['notes'].split("Zoho Event ID:")[1].strip().split()[0]
            except:
                pass
        
        if not zoho_event_id:
            # If no event ID, create a new appointment instead
            return create_zoho_appointment(lead_id, date, time, medium)
        
        # Format appointment data
        start_datetime = f"{date}T{time}:00"
        end_datetime = increment_time(start_datetime, minutes=30)
        
        # Update event in Zoho Calendar
        url = f"https://www.zohoapis.com/crm/v2/Events/{zoho_event_id}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json"
        }
        
        if org_id:
            headers["X-ORGID"] = org_id
        
        # Get lead information
        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return False
        
        event_data = {
            "data": [{
                "Start_DateTime": start_datetime,
                "End_DateTime": end_datetime,
                "Location": "Phone Call" if medium == "Phone" else "Zoom Meeting"
            }]
        }
        
        try:
            response = requests.put(url, headers=headers, json=event_data)
            return response.status_code in (200, 201, 204)
        except Exception as e:
            logger.error(f"Error updating event in Zoho: {str(e)}")
            return False

def update_zoho_lead_qualification(lead_id, qualification_status, uses_mobile, employee_count, notes):
    """Update lead qualification status in Zoho CRM"""
    access_token = get_zoho_access_token()
    if not access_token:
        return False
    
    config = get_config()
    org_id = config.get('ZOHO_ORG_ID')
    
    with get_db() as conn:
        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return False
        
        # Extract Zoho Lead ID if available
        zoho_lead_id = None
        if lead['notes'] and "Zoho Lead ID:" in lead['notes']:
            try:
                zoho_lead_id = lead['notes'].split("Zoho Lead ID:")[1].strip().split()[0]
            except:
                pass
        
        if not zoho_lead_id:
            # If no Zoho ID, we can't update the lead
            return False
        
        # Format lead data for update
        lead_data = {
            "data": [{
                "Description": f"Employee Count: {employee_count}\nUses Mobile Devices: {uses_mobile}\n\n{notes or ''}",
                # Custom fields - these would need to match your actual Zoho CRM setup
                "$se_module": "Leads"
            }]
        }
        
        # Add a custom field for qualification status if your Zoho has one
        if qualification_status == 'Qualified':
            lead_data["data"][0]["Lead_Status"] = "Qualified"
        else:
            lead_data["data"][0]["Lead_Status"] = "Not Qualified"
        
        # Update lead in Zoho
        url = f"https://www.zohoapis.com/crm/v2/Leads/{zoho_lead_id}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json"
        }
        
        if org_id:
            headers["X-ORGID"] = org_id
        
        try:
            response = requests.put(url, headers=headers, json=lead_data)
            return response.status_code in (200, 201, 204)
        except Exception as e:
            logger.error(f"Error updating lead in Zoho: {str(e)}")
            return False

def get_zoho_availability(date):
    """Get available time slots from Zoho Calendar"""
    access_token = get_zoho_access_token()
    if not access_token:
        return []
    
    config = get_config()
    org_id = config.get('ZOHO_ORG_ID')
    
    # Format date for Zoho API
    try:
        dt = datetime.fromisoformat(f"{date}T00:00:00")
        
        # Get start of day and end of day
        start_time = dt.isoformat() + 'Z'
        end_time = dt.replace(hour=23, minute=59, second=59).isoformat() + 'Z'
    except:
        # If date parsing fails, return empty list
        return []
    
    try:
        # Get user ID - needed for free/busy lookup
        user_url = "https://www.zohoapis.com/crm/v2/users?type=CurrentUser"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}"
        }
        
        if org_id:
            headers["X-ORGID"] = org_id
        
        user_response = requests.get(user_url, headers=headers)
        if user_response.status_code != 200:
            return []
        
        user_id = user_response.json()['users'][0]['id']
        
        # Get free/busy information from Zoho Calendar
        calendar_url = "https://www.zohoapis.com/calendar/v1/freebusy"
        params = {
            "users": user_id,
            "starttime": start_time,
            "endtime": end_time
        }
        
        response = requests.get(calendar_url, headers=headers, params=params)
        if response.status_code != 200:
            return []
        
        # Extract busy times
        busy_times = []
        try:
            freebusy_data = response.json()
            if 'users' in freebusy_data and len(freebusy_data['users']) > 0:
                busy_periods = freebusy_data['users'][0]['busy']
                for period in busy_periods:
                    start = datetime.fromisoformat(period['startTime'].replace('Z', ''))
                    end = datetime.fromisoformat(period['endTime'].replace('Z', ''))
                    busy_times.append((start, end))
        except Exception as e:
            logger.error(f"Error parsing Zoho freebusy response: {str(e)}")
            return []
        
        # Generate all available slots during business hours (9am-5pm)
        all_slots = []
        business_start = dt.replace(hour=9, minute=0, second=0)
        business_end = dt.replace(hour=17, minute=0, second=0)
        
        # Create 30-minute slots
        current_slot = business_start
        while current_slot < business_end:
            slot_end = current_slot + timedelta(minutes=30)
            
            # Check if slot overlaps with any busy time
            is_available = True
            for busy_start, busy_end in busy_times:
                # Slot is unavailable if it overlaps with a busy period
                if not (slot_end <= busy_start or current_slot >= busy_end):
                    is_available = False
                    break
            
            if is_available:
                all_slots.append(current_slot.strftime('%H:%M'))
            
            current_slot = slot_end
        
        return all_slots
    except Exception as e:
        logger.error(f"Error getting Zoho availability: {str(e)}")
        return []

def increment_time(datetime_str, minutes=30):
    """Add minutes to a datetime string in ISO format"""
    dt = datetime.fromisoformat(datetime_str)
    dt = dt + timedelta(minutes=minutes)
    return dt.isoformat()

def extract_city_state(address):
    """Extract city and state from an address string"""
    if not address:
        return None, None
    
    parts = address.split(',')
    if len(parts) >= 2:
        city = parts[-2].strip()
        state_zip = parts[-1].strip().split()
        state = state_zip[0] if state_zip else None
        return city, state
    
    return None, None

@app.route('/api/auto_dial', methods=['POST'])
def auto_dial_leads():
    """Auto-dial leads - strictly enforces business hours"""
    data = request.json
    lead_ids = data.get('lead_ids', [])
    
    # Strictly check business hours - no exceptions
    if not is_within_call_hours():
        mountain_tz = pytz.timezone('US/Mountain')
        now = datetime.now(mountain_tz)
        message = f"Auto-dialer attempt outside business hours at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        logger.warning(message)
        
        return {
            'error': 'Outside of calling hours', 
            'message': 'Auto-dialer can only be used Monday through Friday, 9:30 AM to 4:00 PM Mountain Time.'
        }, 400
    
    # If we have no leads to call, return error
    if not lead_ids:
        return {'error': 'No leads provided'}, 400
    
    results = []
    
    # Process each lead
    for lead_id in lead_ids:
        try:
            with get_db() as conn:
                lead_row = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
                if not lead_row:
                    results.append({'lead_id': lead_id, 'status': 'error', 'message': 'Lead not found'})
                    continue
                
                # Convert SQLite Row to dictionary
                lead = dict(lead_row)
                
                # Generate script based on lead data
                contact_name = lead['name'].split()[0] if lead['name'] else "there"
                company_name = lead['name']
                industry = lead.get('industry', lead.get('category', 'business'))
                city = lead.get('city', 'your area')
                
                script = f"Hello, is this {contact_name}? This is Steve with Seamless Mobile Services. I'll be brief. I understand your company provides {industry} services in {city}. Quick question: do your field crews use mobile phones or tablets for work?"
                
                # Make the call
                config = get_config()
                if config.get('TEST_MODE', False) or not config['TWILIO_ACCOUNT_SID'] or not config['TWILIO_AUTH_TOKEN'] or not config['ELEVENLABS_API_KEY'] or not config['ELEVENLABS_VOICE_ID'] or not config['TWILIO_PHONE_NUMBER']:
                    # Dummy mode
                    conn.execute('UPDATE leads SET status = ? WHERE id = ?', ("Calling", lead_id))
                    results.append({'lead_id': lead_id, 'status': 'success', 'call_sid': 'dummy-call', 'dummy': True})
                else:
                    # Real mode
                    call_sid = place_call(lead['phone'], script)
                    conn.execute('UPDATE leads SET status = ? WHERE id = ?', ("Calling", lead_id))
                    results.append({'lead_id': lead_id, 'status': 'success', 'call_sid': call_sid})
                
                conn.commit()
                
        except Exception as e:
            results.append({'lead_id': lead_id, 'status': 'error', 'message': str(e)})
    
    return {'results': results}

@app.route('/api/lead_history/<int:lead_id>', methods=['GET'])
def get_lead_history(lead_id):
    """Get complete history for a lead including all interactions"""
    with get_db() as conn:
        # Get the lead info
        lead_row = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead_row:
            return {'error': 'Lead not found'}, 404
        
        lead = dict(lead_row)
        
        # Get all call logs
        call_logs = conn.execute('''
            SELECT * FROM call_logs 
            WHERE lead_id = ? 
            ORDER BY created_at ASC
        ''', (lead_id,)).fetchall()
        
        # Get all appointments
        appointments = conn.execute('''
            SELECT * FROM appointments 
            WHERE lead_id = ? 
            ORDER BY date ASC, time ASC
        ''', (lead_id,)).fetchall()
        
        # Get all follow-ups
        follow_ups = conn.execute('''
            SELECT * FROM follow_ups
            WHERE lead_id = ?
            ORDER BY scheduled_time ASC
        ''', (lead_id,)).fetchall()
        
        # Convert to dictionaries
        call_logs = [dict(log) for log in call_logs]
        appointments = [dict(appt) for appt in appointments]
        follow_ups = [dict(fu) for fu in follow_ups]
        
        # Create a timeline of all interactions
        timeline = []
        
        # Add call logs to timeline
        for log in call_logs:
            timeline.append({
                'type': 'call_log',
                'timestamp': log['created_at'],
                'status': log['call_status'],
                'transcript': log['transcript'],
                'data': log
            })
        
        # Add appointments to timeline
        for appt in appointments:
            # Create a timestamp from date and time
            try:
                timestamp = f"{appt['date']} {appt['time']}"
            except:
                timestamp = appt['created_at']
                
            timeline.append({
                'type': 'appointment',
                'timestamp': timestamp,
                'status': appt['status'],
                'medium': appt['medium'],
                'data': appt
            })
        
        # Add follow-ups to timeline
        for follow_up in follow_ups:
            timeline.append({
                'type': 'follow_up',
                'timestamp': follow_up['scheduled_time'],
                'status': follow_up['status'],
                'priority': follow_up['priority'],
                'reason': follow_up['reason'],
                'data': follow_up
            })
        
        # Add lead status changes if we can derive them
        if lead.get('qualification_status'):
            timeline.append({
                'type': 'qualification',
                'timestamp': lead.get('notes', ''),
                'status': lead['qualification_status'],
                'data': {
                    'employee_count': lead.get('employee_count'),
                    'uses_mobile_devices': lead.get('uses_mobile_devices')
                }
            })
        
        # Sort timeline by timestamp (most recent first for display)
        timeline.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '', reverse=True)
        
        return {
            'lead': lead,
            'call_logs': call_logs,
            'appointments': appointments,
            'follow_ups': follow_ups,
            'timeline': timeline
        }

# --- Leads Import/Export ---
@app.route('/api/leads/export', methods=['GET'])
def export_leads():
    """Export leads to CSV file"""
    with get_db() as conn:
        leads = conn.execute('SELECT * FROM leads').fetchall()
        
        if not leads:
            return {'error': 'No leads to export'}, 404
            
        # Create a CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header row based on columns
        columns = [key for key in dict(leads[0]).keys()]
        writer.writerow(columns)
        
        # Write data rows
        for lead in leads:
            writer.writerow([lead[col] for col in columns])
        
        # Create a temporary file to send
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', newline='', encoding='utf-8') as f:
            f.write(output.getvalue())
            temp_file_path = f.name
        
        # Send the file
        return send_file(
            temp_file_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'leads_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )

@app.route('/api/leads/import', methods=['POST'])
def import_leads():
    """Import leads from CSV file"""
    if 'file' not in request.files:
        return {'error': 'No file part'}, 400
        
    file = request.files['file']
    if file.filename == '':
        return {'error': 'No selected file'}, 400
        
    if not file.filename.endswith('.csv'):
        return {'error': 'File must be a CSV'}, 400
    
    # Read CSV file
    stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
    csv_reader = csv.DictReader(stream)
    
    # Get column names from the CSV
    try:
        # Check header row
        column_names = csv_reader.fieldnames
        required_columns = ['name', 'phone']
        
        # Check if required columns exist
        for col in required_columns:
            if col not in column_names:
                return {'error': f'Missing required column: {col}'}, 400
        
        # Process rows
        imported_count = 0
        errors = []
        
        with get_db() as conn:
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 for row number (header is 1)
                # Basic validation
                if not row['name'] or not row['phone']:
                    errors.append(f"Row {row_num}: Missing name or phone")
                    continue
                
                # Check for duplicate phone number
                existing = conn.execute('SELECT id FROM leads WHERE phone = ?', (row['phone'],)).fetchone()
                if existing:
                    errors.append(f"Row {row_num}: Duplicate phone number {row['phone']}")
                    continue
                
                try:
                    # Prepare SQL parameters (handle both required and optional fields)
                    params = {
                        'name': row['name'],
                        'phone': row['phone'],
                        'category': row.get('category', ''),
                        'address': row.get('address', ''),
                        'website': row.get('website', ''),
                        'status': row.get('status', 'Not Called'),
                        'employee_count': int(row.get('employee_count', 0)) if row.get('employee_count', '').isdigit() else 0,
                        'uses_mobile_devices': row.get('uses_mobile_devices', 'Unknown'),
                        'industry': row.get('industry', ''),
                        'city': row.get('city', ''),
                        'state': row.get('state', '')
                    }
                    
                    # Insert the lead
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO leads (name, phone, category, address, website, status, 
                                          employee_count, uses_mobile_devices, industry, city, state) 
                        VALUES (:name, :phone, :category, :address, :website, :status, 
                               :employee_count, :uses_mobile_devices, :industry, :city, :state)
                    ''', params)
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: Error - {str(e)}")
            
            conn.commit()
        
        # Generate response
        result = {
            'success': True,
            'imported_count': imported_count,
            'errors': errors,
            'error_count': len(errors)
        }
        
        return jsonify(result)
        
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/leads/sample', methods=['GET'])
def get_sample_csv():
    """Get a sample CSV file for leads import"""
    # Create a sample CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    headers = ['name', 'phone', 'category', 'address', 'website', 'industry', 'city', 'state', 'employee_count', 'uses_mobile_devices']
    writer.writerow(headers)
    
    # Write sample data rows
    sample_data = [
        ['ABC Plumbing', '7205551234', 'Plumbing', '123 Main St', 'www.abcplumbing.com', 'Plumbing', 'Denver', 'CO', '15', 'Yes'],
        ['XYZ Electric', '3035556789', 'Electrical', '456 Oak Ave', 'www.xyzelectric.com', 'Electrical', 'Colorado Springs', 'CO', '25', 'Yes'],
        ['Mile High HVAC', '7195554321', 'HVAC', '789 Pine Blvd', 'www.milehighhvac.com', 'HVAC', 'Denver', 'CO', '12', 'Unknown']
    ]
    
    for row in sample_data:
        writer.writerow(row)
    
    # Create a temporary file to send
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', newline='', encoding='utf-8') as f:
        f.write(output.getvalue())
        temp_file_path = f.name
    
    # Send the file
    return send_file(
        temp_file_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name='leads_sample.csv'
    )

# --- Follow-up Management Routes ---
@app.route('/api/follow_ups', methods=['GET'])
def get_follow_ups():
    """Get all follow-ups with optional filtering"""
    # Parse filters from query params
    status = request.args.get('status')  # 'Pending', 'Completed', 'Cancelled'
    min_priority = request.args.get('min_priority')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    lead_id = request.args.get('lead_id')
    
    # Build query conditions
    conditions = []
    params = []
    
    if status:
        conditions.append("f.status = ?")
        params.append(status)
    
    if min_priority:
        conditions.append("f.priority >= ?")
        params.append(int(min_priority))
    
    if start_date:
        conditions.append("f.scheduled_time >= ?")
        params.append(start_date)
    
    if end_date:
        conditions.append("f.scheduled_time <= ?")
        params.append(end_date)
    
    if lead_id:
        conditions.append("f.lead_id = ?")
        params.append(int(lead_id))
    
    # Build WHERE clause
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    with get_db() as conn:
        query = f"""
            SELECT f.*, l.name as lead_name, l.phone as lead_phone 
            FROM follow_ups f
            JOIN leads l ON f.lead_id = l.id
            WHERE {where_clause}
            ORDER BY f.scheduled_time ASC
        """
        follow_ups = conn.execute(query, params).fetchall()
        return jsonify([dict(row) for row in follow_ups])

@app.route('/api/follow_ups/<int:follow_up_id>', methods=['PATCH'])
def update_follow_up(follow_up_id):
    """Update a follow-up record"""
    data = request.json
    
    fields = []
    values = []
    for k in ['scheduled_time', 'status', 'priority', 'reason', 'notes']:
        if k in data:
            fields.append(f"{k} = ?")
            values.append(data[k])
    
    if not fields:
        return {'error': 'No fields to update'}, 400
    
    values.append(follow_up_id)
    
    with get_db() as conn:
        # Get the follow-up to update
        follow_up = conn.execute('SELECT * FROM follow_ups WHERE id = ?', (follow_up_id,)).fetchone()
        if not follow_up:
            return {'error': 'Follow-up not found'}, 404
        
        # Update the follow-up
        conn.execute(f"UPDATE follow_ups SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        
        # If status was updated to Completed, update the lead status as well
        if 'status' in data and data['status'] == 'Completed':
            conn.execute('''UPDATE leads SET 
                          notes = CASE 
                             WHEN notes IS NULL OR notes = '' THEN ? 
                             ELSE notes || char(10) || ? 
                          END
                          WHERE id = ?''',
                       (f"Follow-up completed on {datetime.now().strftime('%Y-%m-%d %H:%M')}: {follow_up['reason']}",
                        f"Follow-up completed on {datetime.now().strftime('%Y-%m-%d %H:%M')}: {follow_up['reason']}",
                        follow_up['lead_id']))
            conn.commit()
        
        return {'status': 'updated'}

@app.route('/api/follow_ups', methods=['POST'])
def add_follow_up():
    """Manually create a follow-up"""
    data = request.json
    
    # Required fields
    lead_id = data.get('lead_id')
    if not lead_id:
        return {'error': 'lead_id is required'}, 400
    
    scheduled_time = data.get('scheduled_time')
    if not scheduled_time:
        return {'error': 'scheduled_time is required'}, 400
    
    # Optional fields with defaults
    status = data.get('status', 'Pending')
    priority = data.get('priority', 5)
    reason = data.get('reason', 'Manual follow-up')
    notes = data.get('notes', '')
    
    with get_db() as conn:
        # Check if lead exists
        lead = conn.execute('SELECT id FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return {'error': 'Lead not found'}, 404
        
        # Insert the follow-up
        c = conn.cursor()
        c.execute('''INSERT INTO follow_ups 
                   (lead_id, scheduled_time, status, priority, reason, notes) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                  (lead_id, scheduled_time, status, priority, reason, notes))
        
        follow_up_id = c.lastrowid
        
        # Update lead notes
        conn.execute('''UPDATE leads SET 
                      notes = CASE 
                         WHEN notes IS NULL OR notes = '' THEN ? 
                         ELSE notes || char(10) || ? 
                      END
                      WHERE id = ?''',
                   (f"Follow-up scheduled for {scheduled_time}: {reason}",
                    f"Follow-up scheduled for {scheduled_time}: {reason}",
                    lead_id))
        
        conn.commit()
        
        return {'id': follow_up_id}, 201

@app.route('/api/auto_follow_up', methods=['POST'])
def auto_follow_up():
    """Automatically process and dial follow-ups that are due"""
    # Check business hours
    if not is_within_call_hours():
        return {
            'error': 'Outside of calling hours', 
            'message': 'Auto-follow-up can only be run during business hours.'
        }, 400
    
    # Get the max number of calls to make
    max_calls = request.json.get('max_calls', 10)
    
    # Get current time
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with get_db() as conn:
        # Find follow-ups that are due (scheduled time before now)
        query = """
            SELECT f.*, l.id as lead_id, l.name as lead_name, l.phone as lead_phone, 
                   l.status as lead_status, l.industry, l.city 
            FROM follow_ups f
            JOIN leads l ON f.lead_id = l.id
            WHERE f.status = 'Pending' AND f.scheduled_time <= ?
            ORDER BY f.priority DESC, f.scheduled_time ASC
            LIMIT ?
        """
        
        due_follow_ups = conn.execute(query, (now, max_calls)).fetchall()
        
        if not due_follow_ups:
            return {'message': 'No follow-ups due at this time'}, 200
        
        # Process each follow-up
        results = []
        for follow_up in due_follow_ups:
            try:
                # Convert to dictionary
                follow_up = dict(follow_up)
                lead_id = follow_up['lead_id']
                
                # Generate personalized follow-up script
                script = generate_follow_up_script(follow_up)
                
                # Make the call
                config = get_config()
                if config.get('TEST_MODE', False) or not config['TWILIO_ACCOUNT_SID'] or not config['TWILIO_AUTH_TOKEN'] or not config['ELEVENLABS_API_KEY'] or not config['ELEVENLABS_VOICE_ID'] or not config['TWILIO_PHONE_NUMBER']:
                    # Dummy mode
                    conn.execute('UPDATE leads SET status = ? WHERE id = ?', ("Calling", lead_id))
                    results.append({
                        'follow_up_id': follow_up['id'],
                        'lead_id': lead_id,
                        'status': 'success', 
                        'call_sid': 'dummy-call',
                        'dummy': True
                    })
                else:
                    # Real mode - place the call
                    call_sid = place_call(follow_up['lead_phone'], script)
                    conn.execute('UPDATE leads SET status = ? WHERE id = ?', ("Calling", lead_id))
                    results.append({
                        'follow_up_id': follow_up['id'],
                        'lead_id': lead_id,
                        'status': 'success',
                        'call_sid': call_sid
                    })
                
                # Update follow-up status to 'In Progress'
                conn.execute('UPDATE follow_ups SET status = ? WHERE id = ?', 
                           ('In Progress', follow_up['id']))
                
                conn.commit()
                
            except Exception as e:
                results.append({
                    'follow_up_id': follow_up['id'],
                    'lead_id': follow_up['lead_id'],
                    'status': 'error',
                    'message': str(e)
                })
        
        return {'results': results, 'count': len(results)}

def generate_follow_up_script(follow_up):
    """Generate a personalized script for follow-up calls"""
    lead_name = follow_up.get('lead_name', '')
    contact_name = lead_name.split()[0] if lead_name else "there"
    reason = follow_up.get('reason', '')
    
    # Generate script based on reason and context
    script = f"Hello, is this {contact_name}? This is Steve with Seamless Mobile Services following up on our previous conversation."
    
    if "not a good time" in reason.lower() or "busy" in reason.lower():
        script += f" You mentioned earlier that it wasn't a good time to talk. I hope this is a better time to discuss how our telecom expense management and mobile device management services can help your business."
    
    elif "qualified" in reason.lower():
        script += f" In our previous conversation, I learned that your company uses mobile devices. I'd like to discuss how we can help optimize your mobile operations, reduce costs through our telecom expense management, and improve your mobile device management."
    
    elif "callback" in reason.lower():
        script += f" I'm calling back as requested during our previous conversation. I wanted to discuss how we can help with your telecom expenses and mobile device management."
    
    else:
        # Generic follow-up
        script += f" I'm following up to see if you've had a chance to consider our telecom expense management and mobile device management solutions for your business. Do you have a few minutes to talk?"
    
    return script

@app.route('/api/analytics/learn', methods=['POST'])
def learn_from_successful_calls():
    """Analyze successful calls to improve future conversations"""
    from voice import update_industry_patterns
    
    with get_db() as conn:
        # Get all successful appointments from the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        appointments = conn.execute('''
            SELECT a.*, l.industry, l.employee_count, l.uses_mobile_devices
            FROM appointments a
            JOIN leads l ON a.lead_id = l.id
            WHERE a.created_at > ?
            AND a.status = 'Scheduled'
        ''', (thirty_days_ago,)).fetchall()
        
        # For each successful appointment, analyze the conversation that led to it
        for appt in appointments:
            lead_id = appt['lead_id']
            industry = appt['industry'] or 'generic'
            
            # Get the call logs for this lead
            logs = conn.execute('''
                SELECT transcript, created_at
                FROM call_logs
                WHERE lead_id = ?
                ORDER BY created_at ASC
            ''', (lead_id,)).fetchall()
            
            # Only analyze if we have enough conversation data
            if len(logs) < 4:
                continue
                
            # Extract the full conversation
            conversation = []
            for log in logs:
                transcript = log['transcript']
                if transcript.startswith('Bot: '):
                    conversation.append({"role": "assistant", "content": transcript[5:]})
                elif transcript.startswith('Lead: '):
                    conversation.append({"role": "user", "content": transcript[6:]})
            
            # Analyze the conversation for patterns
            for i in range(len(conversation) - 1):
                if conversation[i]["role"] == "assistant" and conversation[i+1]["role"] == "user":
                    bot_message = conversation[i]["content"]
                    lead_response = conversation[i+1]["content"].lower()
                    
                    # Check if this was a value proposition that led to interest
                    if "save" in bot_message.lower() or "help" in bot_message.lower():
                        if "yes" in lead_response or "interested" in lead_response:
                            # This was a successful value proposition
                            update_industry_patterns(
                                industry,
                                "successful_phrases",
                                "value_proposition",
                                bot_message,
                                True
                            )
                    
                    # Check for successful objection handling
                    objection_indicators = {
                        "not interested": "objection:not interested",
                        "too busy": "objection:too busy",
                        "already have": "objection:already have",
                        "using another": "objection:using another",
                        "too expensive": "objection:too expensive"
                    }
                    
                    for indicator, objection_type in objection_indicators.items():
                        if indicator in lead_response:
                            # If the next bot message led to a positive response
                            if i + 2 < len(conversation):
                                next_bot_message = conversation[i+2]["content"]
                                next_lead_response = conversation[i+2]["content"].lower()
                                if "yes" in next_lead_response or "interested" in next_lead_response:
                                    # This was a successful objection handling
                                    update_industry_patterns(
                                        industry,
                                        "objection_responses",
                                        objection_type,
                                        next_bot_message,
                                        True
                                    )
    
    return jsonify({"status": "success", "message": "Successfully analyzed conversations"})

@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files generated by ElevenLabs"""
    audio_dir = os.path.join(os.path.dirname(__file__), 'audio_files')
    return send_file(os.path.join(audio_dir, filename), mimetype='audio/mpeg')

@app.route('/api/voice_check', methods=['GET'])
def check_voice_settings():
    """Check if ElevenLabs voice is properly configured and test it"""
    config = get_config()
    elevenlabs_api_key = config.get('ELEVENLABS_API_KEY')
    elevenlabs_voice_id = config.get('ELEVENLABS_VOICE_ID')
    
    result = {
        "voice_configured": bool(elevenlabs_api_key and elevenlabs_voice_id),
        "voice_id": elevenlabs_voice_id,
        "voice_model": "eleven_turbo_v2",
        "status": "unconfigured"
    }
    
    if not elevenlabs_api_key or not elevenlabs_voice_id:
        result["message"] = "ElevenLabs API key or Voice ID not configured"
        return jsonify(result)
    
    try:
        # Check if the voice ID exists by querying the ElevenLabs API
        headers = {
            "xi-api-key": elevenlabs_api_key,
            "Content-Type": "application/json"
        }
        response = requests.get(
            f"https://api.elevenlabs.io/v1/voices/{elevenlabs_voice_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            voice_data = response.json()
            result["voice_name"] = voice_data.get("name", "Unknown")
            result["status"] = "working"
            result["message"] = f"Voice '{voice_data.get('name', 'Unknown')}' is properly configured"
            
            # Get the voice settings from config
            voice_settings = config.get("VOICE_SETTINGS", {})
            result["voice_settings"] = {
                "stability": voice_settings.get("stability", 0.6),
                "similarity_boost": voice_settings.get("similarity_boost", 0.8),
                "style": voice_settings.get("style", 0.4),
                "use_speaker_boost": voice_settings.get("use_speaker_boost", True)
            }
            
            # Try generating a test audio file
            test_text = "Hello, this is a test of the voice system."
            try:
                audio_file = elevenlabs_tts(test_text)
                if audio_file and os.path.exists(audio_file):
                    result["test_audio_url"] = f"/audio/{os.path.basename(audio_file)}"
                    result["test_successful"] = True
                else:
                    result["test_successful"] = False
                    result["test_error"] = "Failed to generate audio file"
            except Exception as e:
                result["test_successful"] = False
                result["test_error"] = str(e)
                
        else:
            result["status"] = "error"
            result["message"] = f"Voice ID {elevenlabs_voice_id} not found. Status: {response.status_code}"
            result["api_response"] = response.text
    
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Error testing ElevenLabs API: {str(e)}"
    
    return jsonify(result)

if __name__ == '__main__':
    import sys
    port = 5000
    if len(sys.argv) > 1 and sys.argv[1].startswith('--port'):
        try:
            port = int(sys.argv[1].split('=')[1])
        except Exception:
            port = 5001
    else:
        port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)

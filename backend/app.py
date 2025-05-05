import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import get_db, init_db
from scraper import scrape_business_leads
from voice import place_call, get_llm_response, get_voice_response, process_lead_response
from config import get_config, save_config
import requests
import json
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# --- INIT DB (moved to first request handler) ---
@app.before_request
def setup():
    if not hasattr(app, 'db_initialized'):
        init_db()
        app.db_initialized = True

@app.route('/')
def index():
    return {'status': 'Mobile Solutions API running'}

# --- Twilio Webhook Routes ---
@app.route('/webhook/voice', methods=['POST'])
def webhook_voice():
    """Handle incoming voice call from Twilio"""
    # Get initial script from query params or use default
    script = request.args.get('script', "Hello, this is Ava with Mobile Solutions. I'll be brief.")
    
    # Get lead data if a lead_id is provided
    lead_data = None
    lead_id = request.args.get('lead_id')
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

@app.route('/webhook/response', methods=['POST'])
def webhook_response():
    """Handle speech recognition results from Twilio"""
    # Get speech recognition result from Twilio
    speech_result = request.values.get('SpeechResult')
    lead_id = request.args.get('lead_id')
    
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
    ai_response, updated_history, result = process_lead_response(
        speech_result, 
        lead_data, 
        conversation_history
    )
    
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
            if result["status"] == "complete":
                if result["appointment_set"]:
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
                                result.get("uses_mobile", "Yes"),
                                result.get("employee_count", 10),
                                result.get("appointment_date", ""),
                                result.get("appointment_time", ""),
                                lead_id))
                    
                    # Create appointment if date and time were extracted
                    if result.get("appointment_date") and result.get("appointment_time"):
                        conn.execute('''INSERT INTO appointments 
                                      (lead_id, date, time, status, medium) 
                                      VALUES (?, ?, ?, ?, ?)''',
                                   (lead_id, 
                                    result["appointment_date"], 
                                    result["appointment_time"],
                                    'Scheduled',
                                    'Phone'))
                else:
                    # Update lead status based on qualification
                    qual_status = 'Qualified' if result.get("qualified", False) else 'Not Qualified'
                    conn.execute('''UPDATE leads SET 
                                  status = ?, 
                                  qualification_status = ?,
                                  uses_mobile_devices = ?,
                                  employee_count = ?
                                  WHERE id = ?''',
                               ('Completed', qual_status, 
                                result.get("uses_mobile", "Unknown"),
                                result.get("employee_count", 0),
                                lead_id))
            
            conn.commit()
    
    return str(response)

@app.route('/webhook/status', methods=['POST'])
def webhook_status():
    """Handle call status callbacks from Twilio"""
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

# --- Leads CRUD ---
@app.route('/api/leads', methods=['GET'])
def get_leads():
    with get_db() as conn:
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
    data = request.json
    with get_db() as conn:
        fields = []
        values = []
        for k in ['name', 'phone', 'category', 'address', 'website', 'status', 
                 'employee_count', 'uses_mobile_devices', 'industry', 'city', 'state',
                 'qualification_status', 'appointment_date', 'appointment_time', 'notes']:
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            return {'error': 'No fields to update'}, 400
        values.append(lead_id)
        conn.execute(f"UPDATE leads SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        return {'status': 'updated'}

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
    
    # Get lead info to generate script if not provided
    with get_db() as conn:
        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return {'error': 'Lead not found'}, 404
        
        # Generate script based on lead data if not provided
        if not script:
            contact_name = lead['name'].split()[0] if lead['name'] else "there"
            company_name = lead['name']
            industry = lead.get('industry', lead.get('category', 'business'))
            city = lead.get('city', 'your area')
            
            # Steve Schiffman-style script
            script = f"Hello, is this {contact_name}? This is Ava with Mobile Solutions. I'll be brief. I understand your company provides {industry} services in {city}. Quick question: do your field crews use mobile phones or tablets for work?"
    
    # Dummy mode
    if not config['TWILIO_ACCOUNT_SID'] or not config['ELEVENLABS_API_KEY'] or not config['LLM_API_KEY']:
        with get_db() as conn:
            conn.execute('UPDATE leads SET status = ? WHERE id = ?', ("Calling", lead_id))
            conn.commit()
        return {'call_sid': 'dummy-call', 'dummy': True}
    
    # Real mode
    try:
        call_sid = place_call(lead['phone'], script)
        with get_db() as conn:
            conn.execute('UPDATE leads SET status = ? WHERE id = ?', ("Calling", lead_id))
            conn.commit()
        return {'call_sid': call_sid}
    except Exception as e:
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
        print(f"Error getting Zoho access token: {str(e)}")
    
    return None

def sync_leads_to_zoho(lead_ids):
    """Sync leads to Zoho CRM"""
    access_token = get_zoho_access_token()
    if not access_token:
        return False
    
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
                    "Description": f"Employee Count: {lead['employee_count']}",
                    "Lead_Source": "AI Assistant"
                }]
            }
            
            # Create lead in Zoho
            url = "https://www.zohoapis.com/crm/v2/Leads"
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.post(url, headers=headers, json=lead_data)
                if response.status_code == 201:
                    zoho_id = response.json()['data'][0]['details']['id']
                    # Store Zoho ID in local DB for future reference
                    conn.execute('UPDATE leads SET notes = ? WHERE id = ?', 
                               (f"Zoho Lead ID: {zoho_id}", lead_id))
                    conn.commit()
            except Exception as e:
                print(f"Error creating lead in Zoho: {str(e)}")
    
    return True

def create_zoho_appointment(lead_id, date, time, medium):
    """Create an appointment in Zoho Calendar"""
    access_token = get_zoho_access_token()
    if not access_token:
        return False
    
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
        
        event_data = {
            "data": [{
                "Subject": f"Meeting with {lead['name']}",
                "Start_DateTime": start_datetime,
                "End_DateTime": end_datetime,
                "Event_Title": f"Mobile Solutions Consultation with {lead['name']}",
                "Location": "Phone Call" if medium == "Phone" else "Zoom Meeting"
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
            print(f"Error creating event in Zoho: {str(e)}")
    
    return False

def update_zoho_appointment(lead_id, date, time, medium):
    """Update an existing appointment in Zoho"""
    access_token = get_zoho_access_token()
    if not access_token:
        return False
    
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
            print(f"Error updating event in Zoho: {str(e)}")
            return False

def update_zoho_lead_qualification(lead_id, qualification_status, uses_mobile, employee_count, notes):
    """Update lead qualification status in Zoho CRM"""
    access_token = get_zoho_access_token()
    if not access_token:
        return False
    
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
        
        try:
            response = requests.put(url, headers=headers, json=lead_data)
            return response.status_code in (200, 201, 204)
        except Exception as e:
            print(f"Error updating lead in Zoho: {str(e)}")
            return False

def get_zoho_availability(date):
    """Get available time slots from Zoho Calendar"""
    access_token = get_zoho_access_token()
    if not access_token:
        return []
    
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
            print(f"Error parsing Zoho freebusy response: {str(e)}")
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
        print(f"Error getting Zoho availability: {str(e)}")
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

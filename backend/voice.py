import os
import requests
import json
import time
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
import logging
from config import get_config
from datetime import datetime, timedelta
import re
import urllib.parse
import openai

logger = logging.getLogger(__name__)

# Get LLM response for conversation handling
def get_llm_response(prompt, conversation_history=None, stage="introduction", industry=None):
    """
    Get AI response using GPT-4 or other LLM
    Stage options:
    - introduction: Initial greeting and qualifying question
    - qualification: Determine if they meet criteria (mobile devices, employee count)
    - value_proposition: Present the value of our service
    - objection_handling: Address concerns
    - appointment_setting: Book the appointment
    - closing: End the call politely
    """
    config = get_config()
    api_key = config.get('LLM_API_KEY')
    test_mode = config.get('TEST_MODE', False)
    logger.info(f"Using OpenAI API key: {api_key[:10]}...")  # Log first 10 chars for safety
    
    # Test mode responses
    test_responses = {
        "introduction": "Hi, I'm Steve. I help companies save money on their mobile device management. Do you currently use mobile devices in your business?",
        "qualification": "Great! And how many employees do you have?",
        "value_proposition": f"I've helped similar {industry} companies save up to 20% on their mobile costs through telecom expense management. Would you be interested in a 15-minute meeting to discuss how we could help your business?",
        "objection_handling": "I understand. Many of our clients felt the same way initially, but they were surprised by the savings we found. Would you be open to a quick 15-minute meeting to explore the possibilities?",
        "appointment_setting": "Perfect! Would tomorrow at 10 AM work for you?",
        "closing": "Thank you for your time. I look forward to our meeting. Have a great day!"
    }
    
    try:
        client = openai.OpenAI(api_key=api_key)
        logger.info("Successfully initialized OpenAI client")
        
        # Build the system prompt with Steve Schiffman-style instructions
        system_prompt = f"""
        You are an AI sales assistant named Steve following the Steve Schiffman method of appointment setting. 
        Your goal is to set an appointment, not to sell on this call.
        
        Current conversation stage: {stage}
        
        Follow these principles:
        1. Be direct, polite, and straight to the point
        2. Focus on qualifying the prospect (do they use mobile devices, do they have 10+ employees)
        3. Present brief value (example: "We've helped similar {industry} companies save 20% on mobile costs through telecom expense management and mobile device management")
        4. Ask directly for a short appointment (15 minutes)
        5. Handle objections with the Ledge technique (acknowledge, pivot back to appointment)
        6. Maintain a professional, confident tone
        
        For objection handling:
        - If "not interested": Respond with a benefit example and restate meeting request
        - If "too busy": Suggest a short meeting later, "even 10 minutes can find savings"
        - If "using another provider": Acknowledge and mention "we often find savings even with current providers"
        
        Keep your responses brief, natural and conversational.
        """
        
        # Get learned patterns for this industry if available
        if industry and 'get_industry_specific_patterns' in globals():
            learned_patterns = get_industry_specific_patterns(industry)
            if learned_patterns:
                # Add successful phrases to the prompt if we're in the right stage
                if stage == "value_proposition" and "successful_phrases" in learned_patterns:
                    top_phrases = sorted(learned_patterns["successful_phrases"].items(), 
                                        key=lambda x: x[1], reverse=True)[:3]
                    if top_phrases:
                        phrases_text = "\n".join([f"- {phrase}" for phrase, _ in top_phrases])
                        system_prompt += f"\n\nThese value statements have been particularly effective for {industry} companies:\n{phrases_text}"
                
                # Add objection handling patterns if we're dealing with objections
                if stage == "objection_handling" and "objection_responses" in learned_patterns:
                    # Try to determine what type of objection we're facing
                    objection_type = "general"
                    if prompt:
                        prompt_lower = prompt.lower()
                        objection_indicators = {
                            "not interested": "objection:not interested",
                            "too busy": "objection:too busy",
                            "already have": "objection:already have",
                            "using another": "objection:using another", 
                            "too expensive": "objection:too expensive"
                        }
                        for indicator, key in objection_indicators.items():
                            if indicator in prompt_lower and key in learned_patterns["objection_responses"]:
                                objection_type = key
                                break
                    
                    # Add successful objection handling examples
                    if objection_type in learned_patterns["objection_responses"]:
                        successful_responses = learned_patterns["objection_responses"][objection_type][:2]
                        if successful_responses:
                            responses_text = "\n".join([f"- {resp}" for resp in successful_responses])
                            system_prompt += f"\n\nThese responses have worked well for this type of objection:\n{responses_text}"
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if available
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add the current user input
        messages.append({"role": "user", "content": prompt})
        
        # Try gpt-4 first
        try:
            logger.info("Attempting to use gpt-4 model")
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7
            )
            logger.info("Successfully received response from OpenAI API using gpt-4")
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Failed to use gpt-4: {str(e)}")
            if test_mode:
                logger.info("Using test mode fallback response")
                return test_responses.get(stage, "I understand. Would you be interested in scheduling a 15-minute meeting to discuss this further?")
            logger.info("Falling back to gpt-3.5-turbo")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7
            )
            logger.info("Successfully received response from OpenAI API using gpt-3.5-turbo")
            return response.choices[0].message.content
            
    except Exception as e:
        logger.error(f"Error in get_llm_response: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"API Response: {e.response.text if hasattr(e.response, 'text') else 'No response text'}")
        if test_mode:
            logger.info("Using test mode fallback response after error")
            return test_responses.get(stage, "I understand. Would you be interested in scheduling a 15-minute meeting to discuss this further?")
        raise

# Generate voice using ElevenLabs TTS
def elevenlabs_tts(text):
    """Generate audio for voice agent using ElevenLabs"""
    config = get_config()
    elevenlabs_api_key = config.get('ELEVENLABS_API_KEY')
    elevenlabs_voice_id = config.get('ELEVENLABS_VOICE_ID')
    
    if not elevenlabs_api_key or not elevenlabs_voice_id:
        logger.error("ElevenLabs API key or Voice ID not configured")
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice_id}"
    headers = {
        "xi-api-key": elevenlabs_api_key,
        "Content-Type": "application/json"
    }
    
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.75
        }
    }
    
    try:
        r = requests.post(url, headers=headers, json=data)
        r.raise_for_status()  # Raise exception for bad status codes
        
        # Create audio directory if it doesn't exist
        audio_dir = "audio_files"
        os.makedirs(audio_dir, exist_ok=True)
        
        # Save audio file with timestamp
        timestamp = int(time.time())
        audio_file = os.path.join(audio_dir, f"audio_{timestamp}.mp3")
        
        with open(audio_file, "wb") as f:
            f.write(r.content)
            
        logger.info(f"Successfully generated audio file: {audio_file}")
        return audio_file
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling ElevenLabs API: {str(e)}")
        if hasattr(e.response, 'text'):
            logger.error(f"Response: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error generating audio: {str(e)}")
        return None

# Place a call using Twilio
def place_call(phone_number, script):
    """Place a call using Twilio"""
    config = get_config()
    
    # TEMPORARY FIX: Force using the correct phone number
    target_phone = "3036426337"  # Hardcoded for testing
    
    logger.info("Configuration details:")
    logger.info(f"TWILIO_ACCOUNT_SID: {config.get('TWILIO_ACCOUNT_SID', 'Not found')}")
    logger.info(f"TWILIO_AUTH_TOKEN: {'Present' if config.get('TWILIO_AUTH_TOKEN') else 'Not found'}")
    logger.info(f"TWILIO_PHONE_NUMBER: {config.get('TWILIO_PHONE_NUMBER', 'Not found')}")
    logger.info(f"ELEVENLABS_API_KEY: {'Present' if config.get('ELEVENLABS_API_KEY') else 'Not found'}")
    logger.info(f"ELEVENLABS_VOICE_ID: {config.get('ELEVENLABS_VOICE_ID', 'Not found')}")
    logger.info(f"CALLBACK_URL: {config.get('CALLBACK_URL', 'Not found')}")
    logger.info(f"Full config: {json.dumps(config, indent=2)}")
    
    # Initialize Twilio client with credentials from config
    client = Client(config['TWILIO_ACCOUNT_SID'], config['TWILIO_AUTH_TOKEN'])
    
    # Get webhook URL from config and ensure it doesn't end with /webhook
    webhook_url = config.get('CALLBACK_URL', 'http://localhost:5001').rstrip('/webhook')
    logger.info(f"Using webhook URL: {webhook_url}")
    
    # Get lead_id from phone number if possible (used for continuation)
    from models import get_db
    lead_id = None
    with get_db() as conn:
        result = conn.execute('SELECT id FROM leads WHERE phone = ?', (phone_number,)).fetchone()
        if result:
            lead_id = result['id']
            logger.info(f"Found lead_id: {lead_id}")
    
    # Check if recording is enabled
    recording_enabled = config.get('RECORDING_ENABLED', False)
    logger.info(f"Recording enabled: {recording_enabled}")
    
    try:
        # Place the call
        logger.info(f"Original phone_number: {phone_number}")
        logger.info(f"Using target phone number: {target_phone}")
        logger.info(f"Using Twilio phone number: {config['TWILIO_PHONE_NUMBER']}")
        
        # URL encode the script parameter
        encoded_script = urllib.parse.quote(script)
        voice_url = f"{webhook_url}/webhook/voice?script={encoded_script}&lead_id={lead_id}"
        status_url = f"{webhook_url}/webhook/status?lead_id={lead_id}"
        recording_url = f"{webhook_url}/webhook/recording?lead_id={lead_id}" if recording_enabled else None
        
        logger.info(f"Voice URL: {voice_url}")
        logger.info(f"Status URL: {status_url}")
        if recording_url:
            logger.info(f"Recording URL: {recording_url}")
        
        call = client.calls.create(
            to=target_phone,  # Use the hardcoded number
            from_=config['TWILIO_PHONE_NUMBER'],
            url=voice_url,
            status_callback=status_url,
            status_callback_event=['completed', 'answered', 'busy', 'no-answer', 'failed'],
            record=recording_enabled,
            recording_status_callback=recording_url,
            recording_channels="dual" if recording_enabled else None
        )
        logger.info(f"Call placed successfully with SID: {call.sid}")
        return call.sid
    except Exception as e:
        logger.error(f"Error placing call: {str(e)}")
        raise

# For Twilio webhook to handle voice conversation
def get_voice_response(text, lead_data=None, history=None):
    """Generate voice response for Twilio"""
    # Create TwiML response
    response = VoiceResponse()
    
    # Check if we should use ElevenLabs or standard Twilio TTS
    config = get_config()
    use_elevenlabs = config.get('ELEVENLABS_API_KEY') and config.get('ELEVENLABS_VOICE_ID')
    
    if use_elevenlabs:
        try:
            # Generate audio file
            audio_file = elevenlabs_tts(text)
            if audio_file and os.path.exists(audio_file):
                # Get the full URL for the audio file
                webhook_url = config.get('CALLBACK_URL', '').rstrip('/webhook')
                audio_url = f"{webhook_url}/audio/{os.path.basename(audio_file)}"
                response.play(audio_url)
                logger.info(f"Using ElevenLabs audio: {audio_url}")
            else:
                logger.warning("Failed to generate ElevenLabs audio, falling back to Twilio TTS")
                response.say(text)
        except Exception as e:
            logger.error(f"Error in voice response generation: {str(e)}")
            response.say(text)
    else:
        # Use standard Twilio TTS
        response.say(text)
    
    # Gather speech input
    gather = Gather(
        input='speech',
        action='/webhook/response',
        method='POST',
        speechTimeout='auto',
        enhanced='true'
    )
    response.append(gather)
    
    return str(response)

def recommend_follow_up(lead_data, conversation_history, result):
    """
    Analyze conversation and determine if a follow-up is needed and when
    
    Args:
        lead_data: Dictionary with lead information
        conversation_history: List of conversation messages
        result: Result dictionary from check_conversation_result
        
    Returns:
        Dictionary with recommendation details:
        - recommended (boolean): Whether a follow-up is recommended
        - scheduled_time (datetime): When the follow-up should be scheduled
        - priority (int 1-10): Priority level, higher = more important
        - reason (str): Why follow-up is recommended and notes
    """
    recommendation = {
        "recommended": False,
        "scheduled_time": None,
        "priority": 5,
        "reason": ""
    }
    
    # If conversation is still ongoing, don't recommend a follow-up yet
    if result["status"] == "ongoing":
        return recommendation
    
    # If appointment was set, no follow-up needed
    if result["appointment_set"]:
        return recommendation
    
    # Check if lead is qualified but no appointment set
    if result.get("qualified") == True:
        recommendation["recommended"] = True
        recommendation["priority"] = 8
        recommendation["reason"] = "Lead is qualified but did not set an appointment. High priority follow-up."
        recommendation["scheduled_time"] = calculate_follow_up_time(1)  # Follow up in 1 day
    
    # Check message content for specific cues
    call_back_indicators = analyze_callback_indicators(conversation_history)
    if call_back_indicators["has_callback"]:
        recommendation["recommended"] = True
        recommendation["scheduled_time"] = call_back_indicators["callback_time"]
        recommendation["priority"] = call_back_indicators["priority"]
        recommendation["reason"] = call_back_indicators["reason"]
        return recommendation
    
    # Default follow-up strategy based on lead status
    if lead_data and lead_data.get("uses_mobile_devices") == "Yes":
        # Use mobile devices but didn't qualify or set appointment
        if result.get("employee_count", 0) > 0:
            employee_count = result.get("employee_count", 0)
            
            # Priority based on employee count
            if employee_count >= 20:
                recommendation["recommended"] = True
                recommendation["priority"] = 7
                recommendation["reason"] = f"Potential high-value lead with {employee_count} employees. Uses mobile devices."
                recommendation["scheduled_time"] = calculate_follow_up_time(2)  # Follow up in 2 days
            elif employee_count >= 10:
                recommendation["recommended"] = True
                recommendation["priority"] = 6
                recommendation["reason"] = f"Qualified lead with {employee_count} employees. Uses mobile devices."
                recommendation["scheduled_time"] = calculate_follow_up_time(3)  # Follow up in 3 days
            else:
                recommendation["recommended"] = True
                recommendation["priority"] = 4
                recommendation["reason"] = f"Smaller lead with {employee_count} employees. May still be valuable."
                recommendation["scheduled_time"] = calculate_follow_up_time(5)  # Follow up in 5 days
    
    # If no specific reason to follow up detected, but call ended without appointment
    if not recommendation["recommended"] and result["status"] == "complete":
        recommendation["recommended"] = True
        recommendation["priority"] = 3
        recommendation["reason"] = "Call completed without appointment. Low priority follow-up."
        recommendation["scheduled_time"] = calculate_follow_up_time(7)  # Follow up in a week
    
    return recommendation

def analyze_callback_indicators(conversation_history):
    """Analyze conversation for explicit callback requests or times"""
    result = {
        "has_callback": False,
        "callback_time": None,
        "priority": 5,
        "reason": ""
    }
    
    # If no conversation, return default
    if not conversation_history:
        return result
    
    # Get the last few messages (most recent interaction)
    recent_messages = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
    
    # Extract text from recent messages
    full_text = " ".join([msg["content"].lower() for msg in recent_messages])
    
    # Check for explicit callback requests
    callback_phrases = [
        "call me back",
        "call back",
        "call later",
        "try again",
        "try me again",
        "call again",
        "another time",
        "busy right now",
        "not a good time"
    ]
    
    has_callback_phrase = any(phrase in full_text for phrase in callback_phrases)
    
    # Check for time indicators
    tomorrow_indicators = ["tomorrow", "next day"]
    next_week_indicators = ["next week"]
    specific_day_indicators = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    morning_indicators = ["morning"]
    afternoon_indicators = ["afternoon"]
    
    # Time pattern matching (e.g., "call at 3pm" or "call at 3:00")
    time_patterns = [
        r"(\d{1,2})\s*(am|pm)",
        r"(\d{1,2}):(\d{2})\s*(am|pm)?",
        r"(\d{1,2})\s*o'clock"
    ]
    
    extracted_time = None
    for pattern in time_patterns:
        matches = re.findall(pattern, full_text)
        if matches:
            # Simple extraction, would need more sophistication in production
            extracted_time = matches[0]
            break
    
    # Determine when to call back based on indicators
    if has_callback_phrase:
        result["has_callback"] = True
        result["priority"] = 6  # Higher priority because lead asked for callback
        
        # Calculate callback time
        if any(day in full_text for day in specific_day_indicators):
            # Calculate days until the specified day
            today = datetime.now().weekday()  # 0 = Monday, 6 = Sunday
            target_day = next((i for i, day in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]) if day in full_text), None)
            
            if target_day is not None:
                days_ahead = (target_day - today) % 7
                if days_ahead == 0:  # Same day means next week
                    days_ahead = 7
                
                callback_date = datetime.now() + timedelta(days=days_ahead)
                # Set to 10 AM by default or use extracted time
                callback_date = callback_date.replace(hour=10, minute=0, second=0, microsecond=0)
                result["callback_time"] = callback_date
                result["reason"] = f"Lead requested callback on {callback_date.strftime('%A')}."
        
        elif any(indicator in full_text for indicator in tomorrow_indicators):
            callback_date = datetime.now() + timedelta(days=1)
            # Set to 10 AM by default
            callback_date = callback_date.replace(hour=10, minute=0, second=0, microsecond=0)
            result["callback_time"] = callback_date
            result["reason"] = "Lead requested callback tomorrow."
            
        elif any(indicator in full_text for indicator in next_week_indicators):
            # Calculate next Monday
            today = datetime.now().weekday()
            days_to_monday = 7 - today
            callback_date = datetime.now() + timedelta(days=days_to_monday)
            # Set to 10 AM by default
            callback_date = callback_date.replace(hour=10, minute=0, second=0, microsecond=0)
            result["callback_time"] = callback_date
            result["reason"] = "Lead requested callback next week."
            
        elif extracted_time:
            # Parse the extracted time
            try:
                hour = int(extracted_time[0]) if isinstance(extracted_time, tuple) else 10
                # Adjust for PM
                if isinstance(extracted_time, tuple) and len(extracted_time) > 1 and extracted_time[1].lower() == 'pm' and hour < 12:
                    hour += 12
                    
                callback_date = datetime.now()
                # If it's already past that time today, schedule for tomorrow
                if callback_date.hour >= hour:
                    callback_date = callback_date + timedelta(days=1)
                    
                callback_date = callback_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                result["callback_time"] = callback_date
                result["reason"] = f"Lead requested callback at specific time: {hour}:00."
            except:
                # Default to tomorrow at 10 AM if time parsing fails
                callback_date = datetime.now() + timedelta(days=1)
                callback_date = callback_date.replace(hour=10, minute=0, second=0, microsecond=0)
                result["callback_time"] = callback_date
                result["reason"] = "Lead requested callback, scheduling for tomorrow morning."
        
        else:
            # Default to tomorrow at 10 AM
            callback_date = datetime.now() + timedelta(days=1)
            callback_date = callback_date.replace(hour=10, minute=0, second=0, microsecond=0)
            result["callback_time"] = callback_date
            result["reason"] = "Lead requested callback, scheduling for tomorrow morning."
    
    return result

def calculate_follow_up_time(days=1, hour=10):
    """Calculate a follow-up time N days from now at specified hour"""
    follow_up_time = datetime.now() + timedelta(days=days)
    # Set to specified hour (default 10 AM)
    follow_up_time = follow_up_time.replace(hour=hour, minute=0, second=0, microsecond=0)
    return follow_up_time

# Modify the existing process_lead_response function to include follow-up recommendation
def process_lead_response(speech_result, lead_data, conversation_history):
    """Process the lead's response and determine next steps"""
    # Determine which stage of the conversation we're in
    current_stage = determine_conversation_stage(conversation_history)
    
    # Get industry if available from lead data
    industry = lead_data.get('industry') or lead_data.get('category') if lead_data else None
    
    # Get AI response for this stage
    ai_response = get_llm_response(speech_result, conversation_history, current_stage, industry)
    
    # Update conversation history
    conversation_history.append({"role": "user", "content": speech_result})
    conversation_history.append({"role": "assistant", "content": ai_response})
    
    # Check if we've reached a conclusion (appointment set or not qualified)
    result = check_conversation_result(conversation_history)
    
    # If conversation is complete, generate follow-up recommendation
    follow_up = None
    if result["status"] == "complete":
        follow_up = recommend_follow_up(lead_data, conversation_history, result)
    
    return ai_response, conversation_history, result, follow_up

def determine_conversation_stage(history):
    """Determine which stage of the conversation we're in based on the history"""
    if not history or len(history) < 2:
        return "introduction"
    
    # Count the number of exchanges
    exchange_count = len(history) // 2
    
    # Simple state machine based on exchange count
    if exchange_count == 1:
        return "qualification"
    elif exchange_count == 2:
        return "value_proposition"
    elif exchange_count == 3:
        return "appointment_setting"
    elif exchange_count >= 4:
        return "objection_handling"
    
    return "closing"

def check_conversation_result(history):
    """Check if we've reached a conclusion in the conversation"""
    # This is a simple implementation - in a real system, you would use more
    # sophisticated NLP to determine if an appointment was set
    
    result = {
        "status": "ongoing",
        "appointment_set": False,
        "qualified": None,
        "uses_mobile": None,
        "employee_count": None,
        "appointment_date": None,
        "appointment_time": None
    }
    
    # Analyze last assistant message
    if history and len(history) > 1:
        last_message = history[-1]["content"].lower()
        
        # Check for appointment confirmation
        if ("confirmed" in last_message or "scheduled" in last_message) and ("appointment" in last_message or "meeting" in last_message):
            result["status"] = "complete"
            result["appointment_set"] = True
            
            # Try to extract date and time - this would need more sophisticated parsing in production
            if "on" in last_message and "at" in last_message:
                try:
                    date_part = last_message.split("on")[1].split("at")[0].strip()
                    time_part = last_message.split("at")[1].split(".")[0].strip()
                    result["appointment_date"] = date_part
                    result["appointment_time"] = time_part
                except:
                    pass
        
        # Check for disqualification
        elif "not a good fit" in last_message or "doesn't seem like" in last_message:
            result["status"] = "complete"
            result["qualified"] = False
        
        # Check for completion without appointment
        elif "thank you for your time" in last_message and "goodbye" in last_message:
            result["status"] = "complete"
    
    return result

def get_industry_specific_patterns(industry):
    """Get learned patterns for a specific industry"""
    from models import get_db
    
    patterns = {
        "successful_phrases": {},
        "objection_responses": {
            "objection:not interested": [],
            "objection:too busy": [],
            "objection:already have": [],
            "objection:using another": [],
            "objection:too expensive": []
        }
    }
    
    with get_db() as conn:
        # Get successful phrases
        phrases = conn.execute('''
            SELECT pattern_key, pattern_value, success_count
            FROM industry_patterns
            WHERE industry = ? AND pattern_type = 'successful_phrases'
            ORDER BY success_count DESC
        ''', (industry,)).fetchall()
        
        for phrase in phrases:
            patterns["successful_phrases"][phrase['pattern_value']] = phrase['success_count']
        
        # Get objection responses
        responses = conn.execute('''
            SELECT pattern_key, pattern_value, success_count
            FROM industry_patterns
            WHERE industry = ? AND pattern_type = 'objection_responses'
            ORDER BY success_count DESC
        ''', (industry,)).fetchall()
        
        for response in responses:
            objection_type = response['pattern_key']
            if objection_type in patterns["objection_responses"]:
                patterns["objection_responses"][objection_type].append(response['pattern_value'])
    
    return patterns

def update_industry_patterns(industry, pattern_type, pattern_key, pattern_value, success=True):
    """Update or create an industry pattern"""
    from models import get_db
    
    with get_db() as conn:
        # Try to update existing pattern
        result = conn.execute('''
            UPDATE industry_patterns
            SET pattern_value = ?,
                success_count = success_count + ?,
                last_used = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE industry = ? AND pattern_type = ? AND pattern_key = ?
        ''', (pattern_value, 1 if success else 0, industry, pattern_type, pattern_key))
        
        # If no pattern was updated, create a new one
        if result.rowcount == 0:
            conn.execute('''
                INSERT INTO industry_patterns
                (industry, pattern_type, pattern_key, pattern_value, success_count, last_used)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (industry, pattern_type, pattern_key, pattern_value, 1 if success else 0))
        
        conn.commit()

import os
import requests
import json
import time
from twilio.rest import Client

twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
elevenlabs_agent_id = os.getenv('ELEVENLABS_AGENT_ID')
llm_api_key = os.getenv('LLM_API_KEY')

# Get LLM response for conversation handling
def get_llm_response(prompt, conversation_history=None, stage="introduction"):
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
    import openai
    openai.api_key = llm_api_key
    
    # Build the system prompt with Steve Schiffman-style instructions
    system_prompt = f"""
    You are an AI sales assistant named Ava following the Steve Schiffman method of appointment setting. 
    Your goal is to set an appointment, not to sell on this call.
    
    Current conversation stage: {stage}
    
    Follow these principles:
    1. Be direct, polite, and straight to the point
    2. Focus on qualifying the prospect (do they use mobile devices, do they have 10+ employees)
    3. Present brief value (example: "We've helped similar {industry} companies save 20% on mobile costs")
    4. Ask directly for a short appointment (15 minutes)
    5. Handle objections with the Ledge technique (acknowledge, pivot back to appointment)
    6. Maintain a professional, confident tone
    
    For objection handling:
    - If "not interested": Respond with a benefit example and restate meeting request
    - If "too busy": Suggest a short meeting later, "even 10 minutes can find savings"
    - If "using another provider": Acknowledge and mention "we often find savings even with current providers"
    
    Keep your responses brief, natural and conversational.
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history if available
    if conversation_history:
        messages.extend(conversation_history)
    
    # Add the current user input
    messages.append({"role": "user", "content": prompt})
    
    # Get response from LLM
    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7
    )
    
    return resp['choices'][0]['message']['content']

# Generate voice using ElevenLabs TTS
def elevenlabs_tts(text):
    """Generate audio for voice agent using ElevenLabs"""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_agent_id}"
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
    
    r = requests.post(url, headers=headers, json=data)
    if r.ok:
        # Save audio file
        timestamp = int(time.time())
        audio_file = f"audio_{timestamp}.mp3"
        with open(audio_file, "wb") as f:
            f.write(r.content)
        return audio_file
    return None

# Place a call using Twilio
def place_call(to_number, script, lead_data=None):
    """Place a call to the lead"""
    client = Client(twilio_sid, twilio_token)
    
    # Set up callback URLs for Twilio
    callback_url = os.getenv('CALLBACK_URL', 'http://your-server.com/webhook')
    
    # Initiate call with Twilio
    call = client.calls.create(
        to=to_number,
        from_=twilio_number,
        url=f"{callback_url}/voice?script={script}",
        status_callback=f"{callback_url}/status",
        status_callback_event=['initiated', 'answered', 'completed']
    )
    
    return call.sid

# For Twilio webhook to handle voice conversation
def get_voice_response(script, lead_data=None, conversation_history=None):
    """
    Generate TwiML response for Twilio webhook
    """
    from twilio.twiml.voice_response import VoiceResponse
    
    response = VoiceResponse()
    
    # Default greeting if no script is provided
    if not script:
        script = "Hello, this is Ava with Mobile Solutions. I'll be brief."
    
    # Generate voice audio for the script
    audio_url = elevenlabs_tts(script)
    
    if audio_url:
        # Play the audio file
        response.play(audio_url)
        
        # Set up recording and gather speech input
        gather = response.gather(
            input='speech',
            action='/webhook/response',
            speech_timeout='auto',
            speech_model='phone_call'
        )
    else:
        # Fall back to Twilio's built-in TTS if ElevenLabs fails
        response.say(script, voice='alice')
        
        # Set up recording and gather speech input
        gather = response.gather(
            input='speech',
            action='/webhook/response',
            speech_timeout='auto',
            speech_model='phone_call'
        )
    
    # Handle no response
    response.say("I didn't hear you. I'll call back later. Thank you.")
    response.hangup()
    
    return response

# Process the lead's response in the conversation
def process_lead_response(speech_result, lead_data, conversation_history):
    """Process the lead's response and determine next steps"""
    # Determine which stage of the conversation we're in
    current_stage = determine_conversation_stage(conversation_history)
    
    # Get AI response for this stage
    ai_response = get_llm_response(speech_result, conversation_history, current_stage)
    
    # Update conversation history
    conversation_history.append({"role": "user", "content": speech_result})
    conversation_history.append({"role": "assistant", "content": ai_response})
    
    # Check if we've reached a conclusion (appointment set or not qualified)
    result = check_conversation_result(conversation_history)
    
    return ai_response, conversation_history, result

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

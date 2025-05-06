import json
import os
import sys
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

def load_config():
    config_path = 'backend/config.json'
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config

def check_call_status(call_sid):
    config = load_config()
    if not config:
        return
    
    account_sid = config.get('TWILIO_ACCOUNT_SID')
    auth_token = config.get('TWILIO_AUTH_TOKEN')
    
    if not account_sid or not auth_token:
        print("Missing Twilio credentials in config.json")
        return
    
    try:
        client = Client(account_sid, auth_token)
        
        # Fetch the call details
        call = client.calls(call_sid).fetch()
        
        print(f"Call SID: {call.sid}")
        print(f"From: {call.from_formatted}")
        print(f"To: {call.to_formatted}")
        print(f"Status: {call.status}")
        print(f"Start Time: {call.start_time}")
        print(f"End Time: {call.end_time}")
        print(f"Duration: {call.duration} seconds")
        print(f"Price: ${call.price}")
        
        # Get additional properties safely using dictionary access
        for key in dir(call):
            if not key.startswith('_') and key not in ['from_formatted', 'to_formatted', 'sid', 'status', 'start_time', 'end_time', 'duration', 'price']:
                try:
                    value = getattr(call, key)
                    if value is not None and not callable(value):
                        print(f"{key}: {value}")
                except:
                    pass
        
        return call.status
    except TwilioRestException as e:
        print(f"Twilio error: {e.msg}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

def main():
    if len(sys.argv) < 2:
        # Check both recent call SIDs
        check_call_status("CA6d4c47adad398cc8670b54db0c815d4d")  # From our direct test
        print("\n")
        check_call_status("CAe681f853ca302fb08cf50650e2049d55")  # From the API call
    else:
        call_sid = sys.argv[1]
        check_call_status(call_sid)

if __name__ == "__main__":
    main() 
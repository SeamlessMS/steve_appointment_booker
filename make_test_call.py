import json
import os
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

def test_twilio_credentials(config):
    account_sid = config.get('TWILIO_ACCOUNT_SID')
    auth_token = config.get('TWILIO_AUTH_TOKEN')
    phone_number = config.get('TWILIO_PHONE_NUMBER')
    
    print(f"Testing Twilio credentials...")
    print(f"Account SID: {account_sid}")
    print(f"Auth Token: {auth_token[:5]}...{auth_token[-5:]} (hidden)")
    print(f"Phone Number: {phone_number}")
    
    if not account_sid or not auth_token or not phone_number:
        print("Missing Twilio credentials in config.json")
        return False
    
    try:
        client = Client(account_sid, auth_token)
        
        # Test if we can fetch account info
        account = client.api.accounts(account_sid).fetch()
        print(f"Successfully authenticated with Twilio account: {account.friendly_name}")
        
        # Check if the phone number exists
        try:
            numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
            if numbers:
                print(f"Phone number {phone_number} is valid and belongs to this account")
            else:
                print(f"WARNING: Phone number {phone_number} not found in this account!")
                print("Available phone numbers:")
                for number in client.incoming_phone_numbers.list():
                    print(f" - {number.phone_number}")
        except Exception as e:
            print(f"Error checking phone number: {str(e)}")
        
        # Check account balance
        balance = client.api.accounts(account_sid).balance.fetch()
        print(f"Account balance: ${balance.balance}")
        
        return True
    except TwilioRestException as e:
        print(f"Twilio authentication error: {e.msg}")
        return False
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False

def make_test_call(config, to_number):
    account_sid = config.get('TWILIO_ACCOUNT_SID')
    auth_token = config.get('TWILIO_AUTH_TOKEN')
    from_number = config.get('TWILIO_PHONE_NUMBER')
    
    if not account_sid or not auth_token or not from_number:
        print("Missing Twilio credentials in config.json")
        return False
    
    try:
        client = Client(account_sid, auth_token)
        
        # Make a test call
        print(f"Attempting to make a test call from {from_number} to {to_number}...")
        
        # Use TwiML to have Twilio say a simple message
        twiml = "<Response><Say>This is a test call from the Steve appointment booker system.</Say></Response>"
        
        call = client.calls.create(
            to=to_number,
            from_=from_number,
            twiml=twiml
        )
        
        print(f"Call initiated with SID: {call.sid}")
        print(f"Call status: {call.status}")
        return True
    except TwilioRestException as e:
        print(f"Twilio error making call: {e.msg}")
        return False
    except Exception as e:
        print(f"Unexpected error making call: {str(e)}")
        return False

def main():
    config = load_config()
    if not config:
        return
    
    # Check if TEST_MODE is enabled
    if config.get('TEST_MODE', False):
        print("TEST_MODE is enabled in config.json!")
        print("This will prevent real calls from being made")
        print("Set TEST_MODE to false to enable real calls")
    
    # Test Twilio credentials
    if test_twilio_credentials(config):
        print("\nTwilio credentials are valid")
        
        # Ask if user wants to make a test call
        to_number = "3036426337"  # The number to call
        print(f"\nWould you like to make a direct test call to {to_number}? (y/n)")
        response = input().strip().lower()
        
        if response == 'y':
            make_test_call(config, to_number)
        else:
            print("Test call skipped")
    else:
        print("\nTwilio credentials are invalid or there was an error")

if __name__ == "__main__":
    main() 
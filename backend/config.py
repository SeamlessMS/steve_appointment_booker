import os
import json
from pathlib import Path

# Default config
DEFAULT_CONFIG = {
    'TWILIO_ACCOUNT_SID': '',
    'TWILIO_AUTH_TOKEN': '',
    'TWILIO_PHONE_NUMBER': '',
    'ELEVENLABS_API_KEY': '',
    'ELEVENLABS_VOICE_ID': '',
    'LLM_API_KEY': '',
    'BRIGHTDATA_API_TOKEN': '',
    'BRIGHTDATA_WEB_UNLOCKER_ZONE': '',
    'CALLBACK_URL': 'http://localhost:5001/webhook',
    'ZOHO_ORG_ID': '',
    'ZOHO_CLIENT_ID': '',
    'ZOHO_CLIENT_SECRET': '',
    'ZOHO_REFRESH_TOKEN': '',
    'ZOHO_DEPARTMENT_ID': '',
    # Add business hours configuration
    'BUSINESS_HOURS': {
        'timezone': 'US/Mountain',
        'weekday_start': '09:30',
        'weekday_end': '16:00',
        'weekend_enabled': False,
        'weekend_start': '10:00',
        'weekend_end': '14:00'
    },
    # API authentication
    'API_KEY': '',
    # Call recording settings
    'RECORDING_ENABLED': False,
    # Test mode toggle
    'TEST_MODE': False,
    # Confirmation dialog settings
    'CONFIRM_DELETIONS': 'true'
}

CONFIG_FILE = 'config.json'

def get_config():
    """Get configuration from environment variables or config file"""
    # First, load from config file if it exists
    config = DEFAULT_CONFIG.copy()
    
    print("\nLoading configuration...")
    
    # Try to load from .env file first
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✓ Loaded .env file")
    except ImportError:
        print("× python-dotenv not installed, skipping .env file")
    
    # Then load from environment variables (which now include any .env values)
    env_loaded = []
    for key in config.keys():
        if key in os.environ:
            # Handle complex objects like BUSINESS_HOURS
            if key == 'BUSINESS_HOURS' and isinstance(config[key], dict):
                try:
                    config[key].update(json.loads(os.environ[key]))
                except:
                    pass
            else:
                config[key] = os.environ[key]
            env_loaded.append(key)
    
    if env_loaded:
        print(f"✓ Loaded from environment: {', '.join(env_loaded)}")
    
    # Finally, load from config.json if it exists
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                file_config = json.load(f)
                print("✓ Loaded from config.json")
                config.update(file_config)
        except Exception as e:
            print(f"× Error loading config file: {e}")
    else:
        print(f"× Config file {CONFIG_FILE} not found")
    
    print("\nFinal configuration values:")
    for key in sorted(config.keys()):
        if key in ['TWILIO_AUTH_TOKEN', 'ELEVENLABS_API_KEY', 'LLM_API_KEY', 'ZOHO_CLIENT_SECRET', 'ZOHO_REFRESH_TOKEN']:
            print(f"{key}: [HIDDEN]")
        else:
            print(f"{key}: {config[key]}")
    
    print("\nConfiguration loaded successfully.")
    return config

def save_config(new_config):
    """Save configuration to config file"""
    config = get_config()
    config.update(new_config)
    
    # Create directory if it doesn't exist
    Path(os.path.dirname(CONFIG_FILE)).mkdir(exist_ok=True)
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    
    return config

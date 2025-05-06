import requests
import json
from config import get_config
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def make_test_call():
    # Print configuration details
    config = get_config()
    logger.info("\nConfiguration Status:")
    logger.info(f"TEST_MODE: {config.get('TEST_MODE')}")
    logger.info(f"TWILIO_ACCOUNT_SID present: {bool(config.get('TWILIO_ACCOUNT_SID'))}")
    logger.info(f"TWILIO_AUTH_TOKEN present: {bool(config.get('TWILIO_AUTH_TOKEN'))}")
    logger.info(f"ELEVENLABS_API_KEY present: {bool(config.get('ELEVENLABS_API_KEY'))}")
    logger.info(f"ELEVENLABS_VOICE_ID present: {bool(config.get('ELEVENLABS_VOICE_ID'))}")
    logger.info(f"CALLBACK_URL: {config.get('CALLBACK_URL')}\n")

    url = "http://localhost:5001/api/call"
    headers = {"Content-Type": "application/json"}
    data = {
        "lead_id": 1,
        "is_manual": True,  # Add manual flag to bypass time restrictions
        "script": "Hello, this is a test call from the automated system."
    }
    
    try:
        logger.info("Making API call to: %s", url)
        logger.info("Request data: %s", json.dumps(data, indent=2))
        
        response = requests.post(url, headers=headers, json=data)
        logger.info("Response Status Code: %d", response.status_code)
        logger.info("Response Headers: %s", dict(response.headers))
        logger.info("Response Body: %s", response.text)
        
        if response.status_code != 200:
            logger.error("Error response from server: %s", response.text)
            
    except requests.exceptions.RequestException as e:
        logger.error("Request failed: %s", str(e))
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))

if __name__ == "__main__":
    make_test_call() 
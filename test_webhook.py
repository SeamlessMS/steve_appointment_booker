#!/usr/bin/env python3
import requests
import json
import time
import sys

def test_webhook_connectivity():
    """Test if the webhook URL is accessible"""
    with open('backend/config.json', 'r') as f:
        config = json.load(f)
    
    webhook_url = config.get('CALLBACK_URL', '')
    if not webhook_url:
        print("ERROR: No webhook URL found in config.json")
        return False
    
    print(f"Testing webhook URL: {webhook_url}")
    
    # Test if ngrok is accessible externally
    try:
        response = requests.get(webhook_url, timeout=5)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text[:100]}...")
        return response.status_code < 400
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to connect to webhook URL: {e}")
        return False

def test_webhook_voice_endpoint():
    """Test if the webhook voice endpoint is working"""
    with open('backend/config.json', 'r') as f:
        config = json.load(f)
    
    webhook_base = config.get('CALLBACK_URL', '').rstrip('/webhook')
    webhook_voice_url = f"{webhook_base}/webhook/voice"
    
    print(f"Testing webhook voice endpoint: {webhook_voice_url}")
    
    # Sample Twilio voice callback data
    data = {
        'AccountSid': config.get('TWILIO_ACCOUNT_SID'),
        'CallSid': 'test_call_sid',
        'From': config.get('TWILIO_PHONE_NUMBER'),
        'To': '+13036426337',
        'Direction': 'outbound-api'
    }
    
    try:
        response = requests.post(webhook_voice_url, data=data, timeout=5)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text[:100]}...")
        return response.status_code < 400
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to connect to webhook voice endpoint: {e}")
        return False

def test_local_backend_url():
    """Test if the local backend URL is working"""
    local_url = "http://localhost:5001/webhook/voice"
    
    print(f"Testing local backend URL: {local_url}")
    
    try:
        response = requests.get(local_url, timeout=5)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text[:100]}...")
        return response.status_code < 400
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to connect to local backend URL: {e}")
        return False

def main():
    print("========== WEBHOOK CONNECTIVITY TEST ==========")
    webhook_accessible = test_webhook_connectivity()
    if not webhook_accessible:
        print("\nERROR: Webhook URL is not accessible. Possible causes:")
        print("1. ngrok tunnel is not running or has expired")
        print("2. The backend server is not running")
        print("3. The ngrok URL in config.json is outdated")
        
    print("\n========== LOCAL BACKEND TEST ==========")
    local_backend_working = test_local_backend_url()
    if not local_backend_working:
        print("\nERROR: Local backend is not responding. Possible causes:")
        print("1. The backend Flask server is not running")
        print("2. There's an error in the webhook route handling")
    
    print("\n========== WEBHOOK VOICE ENDPOINT TEST ==========")
    if webhook_accessible:
        webhook_voice_working = test_webhook_voice_endpoint()
        if not webhook_voice_working:
            print("\nERROR: Webhook voice endpoint is not working. Possible causes:")
            print("1. The webhook route is not properly implemented")
            print("2. There's an authentication issue with the webhook")
            print("3. The backend server is encountering errors when processing the webhook")
    
    print("\n========== SUMMARY ==========")
    if webhook_accessible and local_backend_working:
        print("✅ Basic connectivity tests passed")
    else:
        print("❌ Connectivity tests failed")
    
    print("\nRecommendations:")
    print("1. Check if ngrok tunnel is active and matches the URL in config.json")
    print("2. Make sure both backend and frontend are running")
    print("3. Check backend logs for any errors related to webhook processing")
    print("4. Verify Twilio phone number and account are properly configured")
    
if __name__ == "__main__":
    main() 
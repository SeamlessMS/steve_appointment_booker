# Steve Appointment Booker - Test Suite

This directory contains all the test scripts for the Steve Appointment Booker system. The main test script is `test_system.py`, which provides comprehensive testing of all system components.

## Main Test Script

### test_system.py

A comprehensive test script that checks all aspects of the system:
- Configuration validation
- Database structure and connectivity
- Twilio credentials and account status
- OpenAI API connectivity
- ElevenLabs API connectivity
- Backend server status
- Test call functionality

Usage:
```bash
# Run all tests
python -m tests.test_system

# Run with a test phone number to validate call functionality
python -m tests.test_system --phone YOUR_PHONE_NUMBER

# Run a specific test
python -m tests.test_system --test config
python -m tests.test_system --test database
python -m tests.test_system --test twilio
python -m tests.test_system --test openai
python -m tests.test_system --test elevenlabs
python -m tests.test_system --test backend
python -m tests.test_system --test call
```

## Individual Test Scripts

### test_call.py
Tests the call functionality by making a direct call using Twilio.

### test_conversation.py
Tests the conversation flow with a test lead, simulating a complete call flow.

### test_conversation_flow.py
Tests the AI conversation logic and response generation.

### test_api.py
Tests the API endpoints of the backend server.

### add_test_lead.py
Adds a test lead to the database for testing purposes.

## Utility Scripts

### make_test_call.py
A utility script to directly make a test call using Twilio without going through the backend.

### check_logs.py
Checks the log files for errors or important information.

### check_call_status.py
Checks the status of a specific call using its SID.

### check_db.py
Checks the database structure and contents.

### check_learning_db.py
Examines the learning database for AI training data.

## Running Tests

For most testing needs, use the main test script:

```bash
python -m tests.test_system
```

For development and debugging, you may want to use individual test scripts as needed. 
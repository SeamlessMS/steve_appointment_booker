# Steve - Automated Appointment Booking System

Steve is an AI-powered automated phone calling system designed to set appointments for businesses. It uses voice AI to make outbound calls, qualify leads, and book appointments with customers.

## Features

- **Automated Outbound Calling**: Make automated phone calls to lead lists
- **AI Conversation**: Natural language conversations powered by OpenAI GPT models
- **Voice Synthesis**: High-quality voice using ElevenLabs TTS
- **Voicemail Detection**: Automatically detects when a call reaches voicemail
- **Lead Management**: Track and manage leads through a web interface
- **Appointment Scheduling**: Book and manage appointments
- **Follow-up System**: Intelligent follow-up scheduling
- **Time Restrictions**: Respects business hours for calls

## Tech Stack

- **Backend**: Python with Flask
- **Frontend**: React with TailwindCSS
- **AI**: OpenAI GPT-4/3.5 for conversation handling
- **Voice**: ElevenLabs for text-to-speech
- **Calling**: Twilio for phone capabilities
- **Database**: SQLite (can be replaced with other databases)

## Setup

### Prerequisites

- Python 3.7+
- Node.js 14+
- Twilio account
- ElevenLabs account
- OpenAI API key

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment:
   ```
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure your environment:
   Create a `.env` file in the backend directory with:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ELEVENLABS_VOICE_ID=your_elevenlabs_voice_id
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_PHONE_NUMBER=your_twilio_phone_number
   CALLBACK_URL=your_ngrok_or_public_url
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Configure the frontend:
   Create a `.env` file in the frontend directory with:
   ```
   REACT_APP_API_URL=http://localhost:5001
   ```

## Running the Application

### Start the Backend

```
cd backend
python app.py
```

The backend server will start on port 5001.

### Start the Frontend

```
cd frontend
npm start
```

The frontend will be available at http://localhost:3000.

## Using the Application

1. **Import Leads**: Upload a CSV file with lead information or use the scraper feature
2. **Set Up Calling Hours**: Configure business hours in the settings
3. **Make Calls**: Select leads and initiate calls
4. **Monitor Conversations**: View call logs and transcripts
5. **Manage Appointments**: See and manage scheduled appointments

## Testing the System

For testing without using actual API calls, set `TEST_MODE=True` in your backend config.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For support or inquiries, please reach out to [your contact information].

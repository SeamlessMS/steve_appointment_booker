# Steve Appointment Booker

An AI-powered appointment booking system that uses voice calls to qualify leads and schedule appointments.

## Quick Start

1. **Setup Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
python app.py
```

2. **Setup Frontend**
```bash
cd frontend
npm install
npm start
```

## Required API Keys

Add these in the Settings panel after starting the app:

- OpenAI API Key (for conversation intelligence)
- ElevenLabs API Key (for voice synthesis)
- Zoho API Key (optional, for CRM integration)

## Features

- 🤖 AI-powered voice calls
- 📊 Real-time call analytics
- 📝 Automatic call transcription
- 📅 Appointment scheduling
- 🔄 Zoho CRM integration
- 📱 Mobile device management focus
- 🎓 Self-learning capabilities

## Environment Variables

Backend (.env):
```
OPENAI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
ZOHO_API_KEY=your_key_here
TEST_MODE=true
```

Frontend (.env):
```
REACT_APP_API_BASE=http://localhost:5001/api
```

## Common Issues

1. **App Won't Start**
   - Ensure Python 3.8+ is installed
   - Check if all requirements are installed
   - Verify database is initialized
   - Confirm ports 5001 (backend) and 3000 (frontend) are available

2. **Voice Not Working**
   - Verify ElevenLabs API key is set
   - Check selected voice ID exists
   - Ensure internet connection is stable

3. **CRM Sync Issues**
   - Verify Zoho API key
   - Enable Zoho integration in settings
   - Check appointment format matches Zoho requirements

## Architecture

- Frontend: React with Tailwind CSS
- Backend: Python Flask API
- Database: SQLite
- Voice: ElevenLabs API
- AI: OpenAI API
- CRM: Zoho API

## Development

To run in development mode with hot reloading:

1. Backend:
```bash
cd backend
python app.py --port=5001
```

2. Frontend:
```bash
cd frontend
npm run dev
```

## Testing

```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
npm test
```

## Production Deployment

1. Build frontend:
```bash
cd frontend
npm run build
```

2. Serve backend:
```bash
cd backend
gunicorn app:app
```

## Support

For issues or questions:
1. Check common issues above
2. Review error logs in `backend/logs`
3. Ensure all API keys are valid
4. Verify database is properly initialized

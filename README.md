# Seamless Mobile Services Appointment Booker for Mobile Service Businesses

An AI-powered appointment setting system adapted for mobile service businesses in Denver/Colorado Springs. This system follows Steve Schiffman's appointment-setting methodology to qualify leads and set appointments for companies with 10+ employees using mobile devices.

## Key Features

- **Automated Lead Generation**: Scrapes business leads from online sources focused on service industries
- **AI Voice Calls**: Uses Twilio for phone calls and ElevenLabs for natural voice synthesis
- **Steve Schiffman Methodology**: Follows proven appointment setting script structure
- **Business Hours Restriction**: Calls only allowed Monday-Friday 9:30AM-4:00PM Mountain Time 
- **Zoho CRM Integration**: Syncs leads, qualification data, and appointments with Zoho
- **Mobile Service Business Focus**: Targets companies with field service crews using mobile devices
- **Dual Service Offering**: Provides both telecom expense management and mobile device management

## Target Business Types

The system is optimized for the following types of businesses:

### Field Service Businesses (heavy mobile use)
- Plumbing companies
- HVAC & heating contractors
- Electrical contractors
- General construction firms
- Roofing companies
- Pest control companies
- Septic/waste removal services
- Landscaping companies

*These businesses equip techs with phones/tablets to track jobs, manage schedules, and communicate.*

### Fleet & Logistics Operations
- Delivery companies
- Trucking companies
- Courier services
- Towing companies
- Field inspection agencies
- Waste management contractors

*They often have dispatch systems that depend on smartphones or tablets, and need usage monitoring.*

### Labor-Heavy or Jobsite-Heavy Businesses
- Construction & excavation
- Concrete companies
- Drilling & boring contractors
- Utility contractors (fiber, power, water)

*Lots of crews in the field = lots of devices that need managing.*

### Technical Field Services
- Telecom installation companies
- Security system installers
- Solar panel installers
- Maintenance companies

*High tech reliance = great fit for MDM and app support.*

### Mobile Healthcare & Home Services
- In-home care agencies
- Mobile phlebotomy / lab testing
- Rehab or therapy on-site services

*HIPAA compliance and secure mobile communication matters — a strong pitch point.*

### Multi-location Small Chains
- Property management companies
- Car dealerships
- Franchise service businesses (cleaning, pest, etc.)
- Private security companies
- Independent schools or tutoring centers

*Often overlooked but often overspend on lines and have multiple devices across sites.*

### Qualification Filters
When generating leads, look for:
- 10–200 employees
- Keywords: "fleet", "dispatch", "technician", "field service", or "tablet" in job descriptions or websites

## Getting Started

### Prerequisites

- Python 3.8+ 
- Node.js 14+
- API keys for:
  - Twilio (phone calls)
  - ElevenLabs (voice synthesis)
  - OpenAI/GPT-4 (conversation AI)
  - Bright Data (lead scraping)
  - Zoho CRM (optional)

### Installation

1. Clone the repository
2. Set up a virtual environment for Python
3. Install backend dependencies:
   ```
   cd backend
   pip install -r requirements.txt
   ```
4. Install frontend dependencies:
   ```
   cd frontend
   npm install
   ```

### Configuration

Create a `.env` file in the `backend` directory with the following keys:
```
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_phone
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_AGENT_ID=your_voice_id_or_leave_default
LLM_API_KEY=your_openai_key
BRIGHTDATA_API_TOKEN=your_brightdata_token
BRIGHTDATA_WEB_UNLOCKER_ZONE=your_zone_name
CALLBACK_URL=your_webhook_url_or_localhost
ZOHO_ORG_ID=your_zoho_org_id
ZOHO_CLIENT_ID=your_zoho_client_id
ZOHO_CLIENT_SECRET=your_zoho_client_secret
ZOHO_REFRESH_TOKEN=your_zoho_refresh_token
ZOHO_DEPARTMENT_ID=your_zoho_department_id
```

Alternatively, you can enter these values in the Settings UI after starting the application.

### Running the Application

For the easiest startup, use one of the restart scripts:

**Windows Batch File**:
```
restart.bat
```

**PowerShell Script**:
```
.\restart.ps1
```

These scripts will:
1. Kill any processes using ports 5003 and 3000
2. Clean up any lingering Node.js or Python processes
3. Start the backend on port 5003
4. Start the frontend on port 3000

Access the application at: http://localhost:3000

### Manual Startup

If you prefer to start servers manually:

**Backend**:
```
cd backend
python app.py --port=5003
```

**Frontend**:
```
cd frontend
npm start
```

## Using the Application

### Adding Leads

1. **Scrape Leads**:
   - Select location, industry, and number of leads to find
   - Click "Find New Leads"

2. **Add Leads Manually**:
   - Click "Add Lead"
   - Fill out the business information
   - Click "Add Lead"

### Making Calls

1. Click the "Call" button next to a lead
2. The system will check if it's during business hours
3. The AI will follow the Schiffman method:
   - Introduction
   - Qualifying questions (mobile devices, employee count)
   - Brief value statement
   - Appointment setting
   - Objection handling
   - Close

### Viewing Call Results

1. Click the "Transcript" button to view call history
2. Use the "Qualify" button to update lead qualification 
3. Book appointments for qualified leads

## Business Hours

Calls can only be made:
- Monday through Friday
- 9:30 AM to 4:00 PM Mountain Time

Calls already in progress will be allowed to complete even if they extend past business hours.

## Integrations

### Zoho CRM 

When properly configured, the system:
1. Creates new leads in Zoho
2. Updates qualification status
3. Creates calendar events for appointments

## Customization

Modify the Steve Schiffman script prompts in `voice.py` to adjust the conversation approach if needed.

## Support

For questions or issues, contact Ato and Matt at Trout Mobile.

## Troubleshooting and Fixes

### Call Destination Issue
We identified and fixed an issue where despite having the correct phone number in the database (3036426337), the system was actually calling a different number (720-488-7700).

The fix involved modifying the `place_call` function in `backend/voice.py` to correctly use the intended phone number when making calls via Twilio.

### Diagnostic Scripts

Several diagnostic and testing scripts were created:

1. **check_logs.py** - Checks the database records for a specific lead
2. **make_call.py** - Initial script to test making calls via the API
3. **make_test_call.py** - Tests Twilio credentials directly 
4. **check_call_status.py** - Verifies call destinations using Twilio API
5. **fix_and_call.py** - Updates the database with the correct phone number and tests making calls

## System Configuration

- Twilio account has a balance of $19.60 and valid credentials
- The system is configured to call using the phone number: +17207800827
- The callback URL is configured to use ngrok for webhook handling

## Usage

To start the system:
1. Run the backend server
2. Set up ngrok for handling callbacks if testing locally
3. Use the frontend to manage leads and initiate calls

The system now correctly calls the intended phone number (3036426337) for appointment scheduling.

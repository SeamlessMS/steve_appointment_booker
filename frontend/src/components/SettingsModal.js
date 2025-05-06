import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5003/api';

export default function SettingsModal({ open, onClose, onSave }) {
  const [config, setConfig] = useState({
    TWILIO_ACCOUNT_SID: '',
    TWILIO_AUTH_TOKEN: '',
    TWILIO_PHONE_NUMBER: '',
    ELEVENLABS_API_KEY: '',
    ELEVENLABS_VOICE_ID: '',
    LLM_API_KEY: '',
    BRIGHTDATA_API_TOKEN: '',
    BRIGHTDATA_WEB_UNLOCKER_ZONE: '',
    ZOHO_ORG_ID: '',
    ZOHO_CLIENT_ID: '',
    ZOHO_CLIENT_SECRET: '',
    ZOHO_REFRESH_TOKEN: '',
    ZOHO_DEPARTMENT_ID: '',
    CALLBACK_URL: '',
    TEST_MODE: true
  });
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [learningDays, setLearningDays] = useState(30);
  const [learningStatus, setLearningStatus] = useState({ message: '', visible: false });
  const [voiceStatus, setVoiceStatus] = useState({ status: 'unknown', message: '', testing: false });
  const [testAudio, setTestAudio] = useState(null);

  useEffect(() => {
    if (open) {
      axios.get(`${API_BASE}/config`).then(r => setConfig(r.data));
    }
  }, [open]);

  const handleChange = (e) => {
    setConfig({ ...config, [e.target.name]: e.target.value });
  };
  
  const handleToggleChange = (e) => {
    setConfig({ ...config, [e.target.name]: e.target.checked });
  };

  const handleSave = async () => {
    setLoading(true);
    await axios.post(`${API_BASE}/config`, config);
    setLoading(false);
    setSaved(true);
    if (onSave) onSave(config);
    setTimeout(() => setSaved(false), 1500);
  };
  
  const testVoiceSettings = async () => {
    setVoiceStatus({ status: 'testing', message: 'Testing ElevenLabs voice...', testing: true });
    try {
      const response = await axios.get(`${API_BASE}/voice_check`);
      const data = response.data;
      
      if (data.status === 'working' && data.test_successful) {
        setVoiceStatus({ 
          status: 'success', 
          message: `Voice "${data.voice_name}" is working correctly.`, 
          testing: false 
        });
        
        // If there's a test audio URL, set it for playback
        if (data.test_audio_url) {
          setTestAudio(`${API_BASE.replace('/api', '')}${data.test_audio_url}`);
        }
      } else if (data.status === 'working' && !data.test_successful) {
        setVoiceStatus({ 
          status: 'warning', 
          message: `Voice "${data.voice_name}" is configured but test failed: ${data.test_error}`, 
          testing: false 
        });
      } else if (data.status === 'unconfigured') {
        setVoiceStatus({ 
          status: 'error', 
          message: 'ElevenLabs voice is not configured. Please add API key and Voice ID.', 
          testing: false 
        });
      } else {
        setVoiceStatus({ 
          status: 'error', 
          message: `Error: ${data.message}`, 
          testing: false 
        });
      }
    } catch (error) {
      setVoiceStatus({ 
        status: 'error', 
        message: `Error connecting to voice service: ${error.message}`, 
        testing: false 
      });
    }
  };
  
  const triggerLearning = async () => {
    setLearningStatus({ message: 'Analyzing successful conversations...', visible: true });
    try {
      const response = await axios.post(`${API_BASE}/analytics/learn`, { days: learningDays });
      setLearningStatus({ 
        message: `Success! ${response.data.message || 'Learning process completed successfully.'}`, 
        visible: true,
        isError: false
      });
    } catch (error) {
      setLearningStatus({ 
        message: `Error: ${error.response?.data?.message || 'Could not complete learning process.'}`, 
        visible: true,
        isError: true
      });
    }
    
    // Hide message after 5 seconds
    setTimeout(() => {
      setLearningStatus(prev => ({ ...prev, visible: false }));
    }, 5000);
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white p-6 rounded shadow max-w-lg w-full relative overflow-y-auto max-h-screen">
        <button className="absolute top-2 right-2 text-xl" onClick={onClose}>&times;</button>
        <h2 className="text-lg font-bold mb-4">API Key Settings</h2>
        
        <div className="space-y-4">
          <div className="border-b pb-4">
            <h3 className="font-medium mb-2">System Mode</h3>
            <div className="flex items-center space-x-2">
              <input 
                type="checkbox" 
                id="test_mode_toggle"
                name="TEST_MODE"
                checked={config.TEST_MODE}
                onChange={handleToggleChange}
                className="h-5 w-5"
              />
              <label htmlFor="test_mode_toggle" className="font-medium">
                Test Mode {config.TEST_MODE ? '(Enabled)' : '(Disabled)'}
              </label>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              When enabled, calls will be simulated without using external APIs or making real phone calls.
            </p>
          </div>
          
          <div className="border-b pb-4">
            <h3 className="font-medium mb-2">System Learning</h3>
            <p className="text-sm text-gray-600 mb-2">
              Steve can learn from successful conversations to improve future calls.
            </p>
            <div className="flex items-center space-x-2 mb-2">
              <label className="text-sm">Analyze last</label>
              <input 
                type="number" 
                min="7"
                max="365"
                value={learningDays}
                onChange={(e) => setLearningDays(parseInt(e.target.value))}
                className="w-16 border p-1 rounded"
              />
              <label className="text-sm">days of successful calls</label>
            </div>
            <button
              className="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 text-sm"
              onClick={triggerLearning}
            >
              Start Learning Process
            </button>
            {learningStatus.visible && (
              <div className={`mt-2 text-sm p-2 rounded ${learningStatus.isError ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                {learningStatus.message}
              </div>
            )}
          </div>
          
          <div>
            <h3 className="font-medium mb-2">Twilio Voice Settings</h3>
            <div className="space-y-2">
              <input name="TWILIO_ACCOUNT_SID" value={config.TWILIO_ACCOUNT_SID} onChange={handleChange} placeholder="Twilio Account SID" className="w-full border p-2 rounded" />
              <input name="TWILIO_AUTH_TOKEN" value={config.TWILIO_AUTH_TOKEN} onChange={handleChange} placeholder="Twilio Auth Token" className="w-full border p-2 rounded" />
              <input name="TWILIO_PHONE_NUMBER" value={config.TWILIO_PHONE_NUMBER} onChange={handleChange} placeholder="Twilio Phone Number" className="w-full border p-2 rounded" />
              <input name="CALLBACK_URL" value={config.CALLBACK_URL} onChange={handleChange} placeholder="Webhook Callback URL" className="w-full border p-2 rounded" />
            </div>
          </div>
          
          <div>
            <h3 className="font-medium mb-2">AI Voice & Intelligence</h3>
            <div className="space-y-2">
              <input name="ELEVENLABS_API_KEY" value={config.ELEVENLABS_API_KEY} onChange={handleChange} placeholder="ElevenLabs API Key" className="w-full border p-2 rounded" />
              <input name="ELEVENLABS_VOICE_ID" value={config.ELEVENLABS_VOICE_ID} onChange={handleChange} placeholder="ElevenLabs Voice ID" className="w-full border p-2 rounded" />
              <input name="LLM_API_KEY" value={config.LLM_API_KEY} onChange={handleChange} placeholder="OpenAI API Key" className="w-full border p-2 rounded" />
              
              <div className="mt-2">
                <button
                  className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 text-sm disabled:opacity-50"
                  onClick={testVoiceSettings}
                  disabled={voiceStatus.testing || !config.ELEVENLABS_API_KEY || !config.ELEVENLABS_VOICE_ID}
                >
                  {voiceStatus.testing ? 'Testing...' : 'Test Voice Settings'}
                </button>
                
                {voiceStatus.status !== 'unknown' && (
                  <div className={`mt-2 text-sm p-2 rounded ${
                    voiceStatus.status === 'success' ? 'bg-green-100 text-green-800' : 
                    voiceStatus.status === 'warning' ? 'bg-yellow-100 text-yellow-800' : 
                    'bg-red-100 text-red-800'
                  }`}>
                    {voiceStatus.message}
                    {testAudio && (
                      <div className="mt-2">
                        <p className="mb-1 font-medium">Test Audio:</p>
                        <audio controls src={testAudio} className="w-full mt-1" />
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
          
          <div>
            <h3 className="font-medium mb-2">Lead Scraping</h3>
            <div className="space-y-2">
              <input name="BRIGHTDATA_API_TOKEN" value={config.BRIGHTDATA_API_TOKEN} onChange={handleChange} placeholder="Bright Data API Token" className="w-full border p-2 rounded" />
              <input name="BRIGHTDATA_WEB_UNLOCKER_ZONE" value={config.BRIGHTDATA_WEB_UNLOCKER_ZONE} onChange={handleChange} placeholder="Bright Data Zone Name" className="w-full border p-2 rounded" />
            </div>
          </div>
          
          <div>
            <h3 className="font-medium mb-2">Zoho CRM Integration</h3>
            <div className="space-y-2">
              <input name="ZOHO_ORG_ID" value={config.ZOHO_ORG_ID} onChange={handleChange} placeholder="Zoho Organization ID" className="w-full border p-2 rounded" />
              <input name="ZOHO_CLIENT_ID" value={config.ZOHO_CLIENT_ID} onChange={handleChange} placeholder="Zoho Client ID" className="w-full border p-2 rounded" />
              <input name="ZOHO_CLIENT_SECRET" value={config.ZOHO_CLIENT_SECRET} onChange={handleChange} placeholder="Zoho Client Secret" className="w-full border p-2 rounded" />
              <input name="ZOHO_REFRESH_TOKEN" value={config.ZOHO_REFRESH_TOKEN} onChange={handleChange} placeholder="Zoho Refresh Token" className="w-full border p-2 rounded" />
              <input name="ZOHO_DEPARTMENT_ID" value={config.ZOHO_DEPARTMENT_ID} onChange={handleChange} placeholder="Zoho Department ID" className="w-full border p-2 rounded" />
            </div>
          </div>
        </div>
        
        <button onClick={handleSave} className="mt-6 bg-indigo-600 text-white px-6 py-2 rounded hover:bg-indigo-700 disabled:opacity-50" disabled={loading}>
          {loading ? 'Saving...' : 'Save Settings'}
        </button>
        {saved && <div className="text-green-600 mt-2">Saved!</div>}
      </div>
    </div>
  );
}

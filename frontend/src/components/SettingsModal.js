import React, { useState, useEffect } from 'react';
import axios from 'axios';
import VoiceSelector from './VoiceSelector';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5003/api';

export default function SettingsModal({ open, onClose, onSave }) {
  const [settings, setSettings] = useState({
    OPENAI_API_KEY: '',
    ELEVENLABS_API_KEY: '',
    TEST_MODE: false,
    AUTO_QUALIFICATION: true,
    APPOINTMENT_LINK: '',
    ZOHO_API_KEY: '',
    ZOHO_ENABLED: false,
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [activeTab, setActiveTab] = useState('general'); // 'general', 'voice', 'zoho'
  
  useEffect(() => {
    if (open) {
      axios.get(`${API_BASE}/config`).then(r => setSettings(r.data));
    }
  }, [open]);

  const handleChange = (e) => {
    setSettings({ ...settings, [e.target.name]: e.target.value });
  };
  
  const handleToggleChange = (e) => {
    setSettings({ ...settings, [e.target.name]: e.target.checked });
  };

  const handleSave = async () => {
    setLoading(true);
    await axios.post(`${API_BASE}/config`, settings);
    setLoading(false);
    setSuccess(true);
    if (onSave) onSave(settings);
    setTimeout(() => setSuccess(false), 1500);
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

  // Add a handler for Zoho CRM sync
  const handleZohoSync = async () => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);
      
      const response = await axios.post(`${API_BASE}/zoho/sync`);
      setSuccess(`Successfully synced ${response.data.syncedCount} appointments to Zoho CRM`);
    } catch (err) {
      console.error('Error syncing to Zoho:', err);
      setError(err.response?.data?.error || 'Failed to sync with Zoho CRM');
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold">Application Settings</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="flex border-b mb-6">
            <button 
              className={`px-4 py-2 font-medium ${activeTab === 'general' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500'}`}
              onClick={() => setActiveTab('general')}
            >
              General
            </button>
            <button 
              className={`px-4 py-2 font-medium ${activeTab === 'voice' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500'}`}
              onClick={() => setActiveTab('voice')}
            >
              Voice
            </button>
            <button 
              className={`px-4 py-2 font-medium ${activeTab === 'zoho' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500'}`}
              onClick={() => setActiveTab('zoho')}
            >
              Zoho CRM
            </button>
          </div>
          
          {error && (
            <div className="mb-4 p-3 bg-red-100 text-red-800 rounded">
              {error}
            </div>
          )}
          
          {success && (
            <div className="mb-4 p-3 bg-green-100 text-green-800 rounded">
              {success}
            </div>
          )}
          
          {activeTab === 'general' && (
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">OpenAI API Key</label>
                <input 
                  type="password" 
                  name="OPENAI_API_KEY"
                  value={settings.OPENAI_API_KEY}
                  onChange={handleChange}
                  className="w-full p-2 border rounded"
                  placeholder="sk-..."
                />
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">ElevenLabs API Key</label>
                <input 
                  type="password" 
                  name="ELEVENLABS_API_KEY"
                  value={settings.ELEVENLABS_API_KEY}
                  onChange={handleChange}
                  className="w-full p-2 border rounded"
                />
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Appointment Link</label>
                <input 
                  type="text" 
                  name="APPOINTMENT_LINK"
                  value={settings.APPOINTMENT_LINK}
                  onChange={handleChange}
                  className="w-full p-2 border rounded"
                  placeholder="https://calendly.com/your-link"
                />
                <p className="text-xs text-gray-500 mt-1">Link where customers can book appointments</p>
              </div>
              
              <div className="mb-4 flex items-center">
                <input 
                  type="checkbox" 
                  id="TEST_MODE"
                  name="TEST_MODE"
                  checked={settings.TEST_MODE}
                  onChange={handleChange}
                  className="mr-2"
                />
                <label htmlFor="TEST_MODE" className="text-sm font-medium">Test Mode</label>
              </div>
              
              <div className="mb-6 flex items-center">
                <input 
                  type="checkbox" 
                  id="AUTO_QUALIFICATION"
                  name="AUTO_QUALIFICATION"
                  checked={settings.AUTO_QUALIFICATION}
                  onChange={handleChange}
                  className="mr-2"
                />
                <label htmlFor="AUTO_QUALIFICATION" className="text-sm font-medium">Auto-Qualification</label>
              </div>
              
              <div className="flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 border rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  disabled={loading}
                >
                  {loading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          )}
          
          {activeTab === 'voice' && (
            <VoiceSelector onSave={() => {
              setSuccess('Voice settings saved successfully');
              fetchSettings();
            }} />
          )}
          
          {activeTab === 'zoho' && (
            <div>
              <div className="mb-6">
                <h3 className="font-semibold mb-4">Zoho CRM Integration</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Configure integration with Zoho CRM to automatically sync appointments.
                </p>
                
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-1">Zoho API Key</label>
                  <input 
                    type="password" 
                    name="ZOHO_API_KEY"
                    value={settings.ZOHO_API_KEY}
                    onChange={handleChange}
                    className="w-full p-2 border rounded"
                  />
                </div>
                
                <div className="mb-6 flex items-center">
                  <input 
                    type="checkbox" 
                    id="ZOHO_ENABLED"
                    name="ZOHO_ENABLED"
                    checked={settings.ZOHO_ENABLED}
                    onChange={handleChange}
                    className="mr-2"
                  />
                  <label htmlFor="ZOHO_ENABLED" className="text-sm font-medium">Enable Zoho Integration</label>
                </div>
                
                <div className="bg-gray-50 p-4 rounded border mb-6">
                  <h4 className="font-medium mb-2">Manual Sync</h4>
                  <p className="text-sm text-gray-600 mb-3">
                    Sync pending appointments to Zoho CRM manually.
                  </p>
                  <button
                    type="button"
                    onClick={handleZohoSync}
                    className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                    disabled={loading || !settings.ZOHO_ENABLED || !settings.ZOHO_API_KEY}
                  >
                    {loading ? 'Syncing...' : 'Sync to Zoho CRM'}
                  </button>
                </div>
              </div>
              
              <div className="flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 border rounded"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  disabled={loading}
                >
                  {loading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

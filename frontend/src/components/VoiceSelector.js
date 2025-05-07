import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5001/api';

export default function VoiceSelector({ onSave }) {
  const [voices, setVoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [voiceSettings, setVoiceSettings] = useState({
    pitch: 1.0,
    speed: 1.0,
    stability: 0.5
  });
  const [testingVoice, setTestingVoice] = useState(false);
  
  const fetchVoices = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/voices`);
      setVoices(response.data || []);
      
      // Try to get the current default voice
      const settingsResponse = await axios.get(`${API_BASE}/settings`);
      const defaultVoiceId = settingsResponse.data.DEFAULT_VOICE_ID || 'voice1';
      
      // Set the selected voice
      const defaultVoice = response.data.find(voice => voice.id === defaultVoiceId) || response.data[0];
      if (defaultVoice) {
        setSelectedVoice(defaultVoice);
      }
      
      setError(null);
    } catch (err) {
      console.error('Error fetching voices:', err);
      setError('Failed to load voices');
    } finally {
      setLoading(false);
    }
  };
  
  const handleVoiceSelect = (voice) => {
    setSelectedVoice(voice);
  };
  
  const handleSettingChange = (e) => {
    const { name, value } = e.target;
    setVoiceSettings({
      ...voiceSettings,
      [name]: parseFloat(value)
    });
  };
  
  const testVoice = async () => {
    if (!selectedVoice) return;
    
    try {
      setTestingVoice(true);
      
      // Test text - in a real app this would generate audio using ElevenLabs API
      const testText = "Hello, this is Steve from Seamless Mobile Services. I'm calling to see if you'd be interested in learning about our field service management solutions.";
      
      // Simulate audio playback
      // In a real app, this would call ElevenLabs API and play the resulting audio
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Simulate successful playback
      console.log(`Testing voice: ${selectedVoice.name} with text: ${testText}`);
      console.log(`Voice settings: Pitch=${voiceSettings.pitch}, Speed=${voiceSettings.speed}, Stability=${voiceSettings.stability}`);
      
    } catch (err) {
      console.error('Error testing voice:', err);
    } finally {
      setTestingVoice(false);
    }
  };
  
  const saveVoiceSettings = async () => {
    if (!selectedVoice) return;
    
    try {
      // Save the selected voice and settings
      await axios.post(`${API_BASE}/settings/update`, {
        settings: {
          DEFAULT_VOICE_ID: selectedVoice.id
        }
      });
      
      // Also save the voice settings
      await axios.post(`${API_BASE}/voice/settings`, {
        voice_id: selectedVoice.id,
        voice_name: selectedVoice.name,
        pitch: voiceSettings.pitch,
        speed: voiceSettings.speed,
        stability: voiceSettings.stability,
        is_default: 1
      });
      
      // Call onSave callback if provided
      if (onSave) {
        onSave({
          voice: selectedVoice,
          settings: voiceSettings
        });
      }
      
    } catch (err) {
      console.error('Error saving voice settings:', err);
      setError('Failed to save voice settings');
    }
  };
  
  useEffect(() => {
    fetchVoices();
  }, []);
  
  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h2 className="text-xl font-bold mb-6">Voice Selection</h2>
      
      {error && (
        <div className="bg-red-100 border border-red-300 text-red-800 px-4 py-2 rounded mb-4">
          {error}
        </div>
      )}
      
      {loading ? (
        <div className="text-center py-8">
          <svg className="w-10 h-10 mx-auto animate-spin text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <p className="mt-2">Loading voices...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Voice selection panel */}
          <div>
            <h3 className="font-semibold mb-4">Select Steve's Voice</h3>
            <div className="grid grid-cols-1 gap-3 max-h-96 overflow-y-auto pr-2">
              {voices.map((voice) => (
                <div 
                  key={voice.id}
                  className={`p-3 border rounded cursor-pointer transition-colors ${
                    selectedVoice?.id === voice.id 
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                  onClick={() => handleVoiceSelect(voice)}
                >
                  <div className="font-medium">{voice.name}</div>
                  <div className="text-sm text-gray-600 mt-1">{voice.description}</div>
                  {voice.preview_url && (
                    <button 
                      className="mt-2 text-xs text-blue-600 flex items-center"
                      onClick={(e) => {
                        e.stopPropagation();
                        // Play sample
                      }}
                    >
                      <svg className="w-4 h-4 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Listen to sample
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
          
          {/* Voice customization panel */}
          <div>
            <h3 className="font-semibold mb-4">Voice Settings</h3>
            
            {selectedVoice ? (
              <>
                <div className="space-y-4 mb-6">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Pitch <span className="text-xs text-gray-500 ml-1">({voiceSettings.pitch.toFixed(1)})</span>
                    </label>
                    <input
                      type="range"
                      name="pitch"
                      min="0.5"
                      max="1.5"
                      step="0.1"
                      value={voiceSettings.pitch}
                      onChange={handleSettingChange}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>Lower</span>
                      <span>Higher</span>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Speed <span className="text-xs text-gray-500 ml-1">({voiceSettings.speed.toFixed(1)})</span>
                    </label>
                    <input
                      type="range"
                      name="speed"
                      min="0.5"
                      max="1.5"
                      step="0.1"
                      value={voiceSettings.speed}
                      onChange={handleSettingChange}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>Slower</span>
                      <span>Faster</span>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Stability <span className="text-xs text-gray-500 ml-1">({voiceSettings.stability.toFixed(1)})</span>
                    </label>
                    <input
                      type="range"
                      name="stability"
                      min="0"
                      max="1"
                      step="0.1"
                      value={voiceSettings.stability}
                      onChange={handleSettingChange}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>More variation</span>
                      <span>More stable</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex flex-col space-y-3">
                  <button
                    className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 flex items-center justify-center disabled:opacity-50"
                    onClick={testVoice}
                    disabled={testingVoice}
                  >
                    {testingVoice ? (
                      <>
                        <svg className="w-5 h-5 mr-2 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Testing Voice...
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Test Voice
                      </>
                    )}
                  </button>
                  
                  <button
                    className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 flex items-center justify-center"
                    onClick={saveVoiceSettings}
                  >
                    <svg className="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Save Voice Settings
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-gray-500">
                Select a voice to customize settings
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
} 
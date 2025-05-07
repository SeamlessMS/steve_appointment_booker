import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { getCallLogs } from '../api';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5001/api';

export default function SteveDashboard() {
  const [steveStatus, setSteveStatus] = useState('Idle');
  const [activeCalls, setActiveCalls] = useState([]);
  const [selectedCall, setSelectedCall] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const fetchStatus = async () => {
    try {
      setLoading(true);
      // Get all leads with 'Calling' status
      const response = await axios.get(`${API_BASE}/leads?status=Calling`);
      
      if (response.data && response.data.length > 0) {
        setSteveStatus('On Call');
        setActiveCalls(response.data);
        
        // If we have a selected call, make sure it's still active
        if (selectedCall) {
          const stillActive = response.data.find(call => call.id === selectedCall.id);
          if (!stillActive) {
            setSelectedCall(null);
            setTranscript([]);
          } else {
            // Refresh transcript for selected call
            fetchTranscript(selectedCall.id);
          }
        }
      } else {
        setSteveStatus('Idle');
        setActiveCalls([]);
        setSelectedCall(null);
        setTranscript([]);
      }
      
      setError(null);
    } catch (err) {
      console.error('Error fetching Steve status:', err);
      setError('Failed to load status');
    } finally {
      setLoading(false);
    }
  };
  
  const fetchTranscript = async (leadId) => {
    try {
      const logs = await getCallLogs(leadId);
      if (logs && logs.length > 0) {
        // Format transcript from call logs
        const formattedTranscript = logs
          .filter(log => log.transcript && 
                 (log.transcript.startsWith('Bot:') || 
                  log.transcript.startsWith('Lead:')))
          .map(log => ({
            type: log.transcript.startsWith('Bot:') ? 'bot' : 'lead',
            text: log.transcript.replace(/^(Bot:|Lead:)\s/, ''),
            timestamp: log.created_at
          }));
        
        setTranscript(formattedTranscript);
      } else {
        setTranscript([]);
      }
    } catch (err) {
      console.error('Error fetching transcript:', err);
    }
  };
  
  const handleSelectCall = (call) => {
    setSelectedCall(call);
    fetchTranscript(call.id);
  };
  
  useEffect(() => {
    // Initial fetch
    fetchStatus();
    
    // Set up polling every 5 seconds
    const intervalId = setInterval(fetchStatus, 5000);
    
    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, []);
  
  const getStatusColor = (status) => {
    switch(status) {
      case 'On Call':
        return 'bg-blue-100 border-blue-300 text-blue-800';
      case 'Idle':
        return 'bg-gray-100 border-gray-300 text-gray-800';
      default:
        return 'bg-gray-100 border-gray-300 text-gray-800';
    }
  };
  
  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Steve Status</h2>
        <button
          onClick={fetchStatus}
          className="px-3 py-1 bg-gray-100 rounded hover:bg-gray-200 flex items-center"
          disabled={loading}
        >
          <svg className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>
      
      {error && (
        <div className="bg-red-100 border border-red-300 text-red-800 px-4 py-2 rounded mb-4">
          {error}
        </div>
      )}
      
      <div className={`border px-4 py-3 rounded mb-4 ${getStatusColor(steveStatus)}`}>
        <div className="flex items-center">
          <div className={`w-3 h-3 rounded-full mr-2 ${steveStatus === 'On Call' ? 'bg-blue-500 animate-pulse' : 'bg-gray-500'}`}></div>
          <span className="font-medium">Steve is currently: {steveStatus}</span>
        </div>
      </div>
      
      {activeCalls.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3 className="text-lg font-medium mb-2">Active Calls ({activeCalls.length})</h3>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {activeCalls.map(call => (
                <div 
                  key={call.id} 
                  className={`border rounded p-3 cursor-pointer transition-colors duration-150 
                    ${selectedCall && selectedCall.id === call.id 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 bg-white hover:bg-gray-50'}`}
                  onClick={() => handleSelectCall(call)}
                >
                  <div className="font-medium">{call.name}</div>
                  <div className="text-sm text-gray-600">
                    <span>Phone: {call.phone}</span>
                    <span className="mx-2">•</span>
                    <span>Status: {call.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          <div>
            <h3 className="text-lg font-medium mb-2">Live Transcript</h3>
            {selectedCall ? (
              <div className="border rounded p-3 h-80 overflow-y-auto bg-gray-50">
                {transcript.length > 0 ? (
                  <div className="space-y-2">
                    {transcript.map((msg, index) => (
                      <div key={index} className={`p-2 rounded ${
                        msg.type === 'bot' 
                          ? 'bg-blue-100 ml-4' 
                          : 'bg-gray-200 mr-4'
                      }`}>
                        <div className="font-semibold text-xs text-gray-600">
                          {msg.type === 'bot' ? 'Steve' : 'Lead'}
                        </div>
                        <div>{msg.text}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-gray-500 italic text-center mt-10">
                    No transcript available yet
                  </div>
                )}
              </div>
            ) : (
              <div className="border rounded p-3 h-80 flex items-center justify-center bg-gray-50">
                <span className="text-gray-500 italic">Select a call to view live transcript</span>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="text-gray-500 italic">No active calls</div>
      )}
    </div>
  );
} 
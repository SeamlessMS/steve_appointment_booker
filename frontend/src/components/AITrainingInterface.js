import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5001/api';

export default function AITrainingInterface() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successfulCalls, setSuccessfulCalls] = useState([]);
  const [selectedCallId, setSelectedCallId] = useState(null);
  const [callTranscript, setCallTranscript] = useState([]);
  const [learningSummary, setLearningSummary] = useState(null);
  const [learningInProgress, setLearningInProgress] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [successfulPatterns, setSuccessfulPatterns] = useState({
    objectionHandling: [],
    valuePropositions: [],
    qualificationQuestions: [],
    closingTechniques: []
  });

  // Fetch successful calls (calls that led to appointments or qualified leads)
  const fetchSuccessfulCalls = async () => {
    try {
      setLoading(true);
      
      // Get all appointments
      const appointmentsResponse = await axios.get(`${API_BASE}/appointments`);
      const appointments = appointmentsResponse.data || [];
      
      // Get all qualified leads
      const leadsResponse = await axios.get(`${API_BASE}/leads`);
      const qualifiedLeads = leadsResponse.data.filter(lead => 
        lead.qualification_status === 'Qualified' ||
        lead.status === 'Appointment Set'
      ) || [];
      
      // Combine into a list of successful conversations
      const successful = [];
      
      // Add appointments
      for (const appt of appointments) {
        successful.push({
          id: `appt-${appt.id}`,
          leadId: appt.lead_id,
          leadName: appt.lead_name,
          date: appt.date,
          type: 'Appointment',
          details: `${appt.medium} appointment on ${appt.date} at ${appt.time}`
        });
      }
      
      // Add qualified leads that don't have appointments
      for (const lead of qualifiedLeads) {
        // Skip if we already added an appointment for this lead
        if (!successful.some(s => s.leadId === lead.id)) {
          successful.push({
            id: `lead-${lead.id}`,
            leadId: lead.id,
            leadName: lead.name,
            date: lead.updated_at,
            type: 'Qualified Lead',
            details: `${lead.industry || lead.category || 'Unknown'} / ${lead.employee_count || '?'} employees`
          });
        }
      }
      
      // Sort by date (most recent first)
      successful.sort((a, b) => new Date(b.date) - new Date(a.date));
      
      setSuccessfulCalls(successful);
      setError(null);
    } catch (err) {
      console.error('Error fetching successful calls:', err);
      setError('Failed to load successful calls');
    } finally {
      setLoading(false);
    }
  };
  
  // Fetch transcript for a specific call
  const fetchCallTranscript = async (leadId) => {
    try {
      setLoading(true);
      
      // Get call logs for this lead
      const logsResponse = await axios.get(`${API_BASE}/call_logs/${leadId}`);
      const logs = logsResponse.data || [];
      
      // Format into a conversation transcript
      const transcript = [];
      for (const log of logs) {
        if (log.transcript) {
          if (log.transcript.startsWith('Bot:')) {
            transcript.push({
              speaker: 'steve',
              text: log.transcript.substring(4).trim(),
              timestamp: log.created_at
            });
          } else if (log.transcript.startsWith('Lead:')) {
            transcript.push({
              speaker: 'lead',
              text: log.transcript.substring(5).trim(),
              timestamp: log.created_at
            });
          }
        }
      }
      
      // Sort by timestamp
      transcript.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
      
      setCallTranscript(transcript);
      setSelectedCallId(leadId);
      setError(null);
    } catch (err) {
      console.error('Error fetching call transcript:', err);
      setError('Failed to load call transcript');
    } finally {
      setLoading(false);
    }
  };
  
  // Fetch successful patterns
  const fetchSuccessfulPatterns = async () => {
    try {
      const response = await axios.get(`${API_BASE}/ai/patterns`);
      if (response.data) {
        setSuccessfulPatterns(response.data);
      }
    } catch (err) {
      console.error('Error fetching successful patterns:', err);
    }
  };
  
  // Run learning based on successful calls
  const runLearning = async () => {
    try {
      setLearningInProgress(true);
      
      const response = await axios.post(`${API_BASE}/analytics/learn`, {
        feedback: feedback
      });
      
      setLearningSummary({
        message: 'Learning process completed successfully',
        callsAnalyzed: response.data?.callsAnalyzed || 0,
        patternsIdentified: response.data?.patternsIdentified || 0,
        timestamp: new Date().toLocaleString()
      });
      
      // Refresh patterns
      await fetchSuccessfulPatterns();
      
    } catch (err) {
      console.error('Error running learning process:', err);
      setLearningSummary({
        message: `Error: ${err.response?.data?.error || 'Failed to run learning process'}`,
        timestamp: new Date().toLocaleString()
      });
    } finally {
      setLearningInProgress(false);
    }
  };
  
  useEffect(() => {
    fetchSuccessfulCalls();
    fetchSuccessfulPatterns();
  }, []);
  
  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">AI Training Interface</h2>
        <button
          onClick={fetchSuccessfulCalls}
          className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center"
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
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left panel: Successful calls list */}
        <div className="col-span-1">
          <div className="bg-gray-50 rounded-lg p-4 h-full">
            <h3 className="text-lg font-semibold mb-4">Successful Conversations</h3>
            
            {loading && successfulCalls.length === 0 ? (
              <div className="text-center py-8">
                <svg className="w-8 h-8 mx-auto animate-spin text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <p className="mt-2">Loading successful calls...</p>
              </div>
            ) : successfulCalls.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No successful calls found.
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {successfulCalls.map((call) => (
                  <div 
                    key={call.id}
                    className={`p-3 rounded border cursor-pointer hover:bg-blue-50 transition-colors ${
                      selectedCallId === call.leadId ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                    onClick={() => fetchCallTranscript(call.leadId)}
                  >
                    <div className="font-medium">{call.leadName}</div>
                    <div className="text-sm text-gray-500 flex justify-between">
                      <span>{call.type}</span>
                      <span>{new Date(call.date).toLocaleDateString()}</span>
                    </div>
                    <div className="text-xs text-gray-600 mt-1">{call.details}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        
        {/* Center panel: Conversation transcript */}
        <div className="col-span-1">
          <div className="bg-gray-50 rounded-lg p-4 h-full">
            <h3 className="text-lg font-semibold mb-4">Conversation Transcript</h3>
            
            {selectedCallId ? (
              loading ? (
                <div className="text-center py-8">
                  <svg className="w-8 h-8 mx-auto animate-spin text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <p className="mt-2">Loading transcript...</p>
                </div>
              ) : callTranscript.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No transcript available for this call.
                </div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {callTranscript.map((entry, index) => (
                    <div 
                      key={index}
                      className={`p-3 rounded ${
                        entry.speaker === 'steve' 
                          ? 'bg-blue-100 ml-4' 
                          : 'bg-gray-200 mr-4'
                      }`}
                    >
                      <div className="font-semibold text-xs text-gray-600">
                        {entry.speaker === 'steve' ? 'Steve' : 'Lead'}
                      </div>
                      <div>{entry.text}</div>
                      <div className="text-xs text-gray-500 mt-1 text-right">
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : (
              <div className="text-center py-8 text-gray-500">
                Select a conversation to view the transcript.
              </div>
            )}
          </div>
        </div>
        
        {/* Right panel: Learning controls and patterns */}
        <div className="col-span-1">
          <div className="bg-gray-50 rounded-lg p-4 h-full">
            <h3 className="text-lg font-semibold mb-4">AI Learning</h3>
            
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">
                Training Feedback <span className="text-xs text-gray-500">(optional)</span>
              </label>
              <textarea
                className="w-full border rounded p-2"
                rows={3}
                placeholder="Add additional feedback for Steve's learning algorithm..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
              ></textarea>
            </div>
            
            <button
              className="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 mb-4 flex justify-center items-center disabled:opacity-50"
              onClick={runLearning}
              disabled={learningInProgress}
            >
              {learningInProgress ? (
                <>
                  <svg className="w-5 h-5 mr-2 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Learning in Progress...
                </>
              ) : (
                'Start Learning Process'
              )}
            </button>
            
            {learningSummary && (
              <div className={`p-3 rounded mb-4 ${
                learningSummary.message.startsWith('Error') 
                  ? 'bg-red-100 text-red-800' 
                  : 'bg-green-100 text-green-800'
              }`}>
                <div className="font-medium">{learningSummary.message}</div>
                {learningSummary.callsAnalyzed && (
                  <div className="text-sm">Calls analyzed: {learningSummary.callsAnalyzed}</div>
                )}
                {learningSummary.patternsIdentified && (
                  <div className="text-sm">Patterns identified: {learningSummary.patternsIdentified}</div>
                )}
                <div className="text-xs mt-1">{learningSummary.timestamp}</div>
              </div>
            )}
            
            <div className="mt-4">
              <h4 className="font-medium mb-2">Learned Patterns</h4>
              
              <div className="space-y-3 max-h-56 overflow-y-auto">
                {/* Objection Handling */}
                <div className="bg-white rounded p-3 border">
                  <div className="font-medium text-sm">Objection Handling</div>
                  {successfulPatterns.objectionHandling.length === 0 ? (
                    <div className="text-xs text-gray-500 mt-1">No patterns learned yet</div>
                  ) : (
                    <ul className="text-xs mt-1 list-disc pl-4">
                      {successfulPatterns.objectionHandling.map((pattern, index) => (
                        <li key={index}>{pattern}</li>
                      ))}
                    </ul>
                  )}
                </div>
                
                {/* Value Propositions */}
                <div className="bg-white rounded p-3 border">
                  <div className="font-medium text-sm">Value Propositions</div>
                  {successfulPatterns.valuePropositions.length === 0 ? (
                    <div className="text-xs text-gray-500 mt-1">No patterns learned yet</div>
                  ) : (
                    <ul className="text-xs mt-1 list-disc pl-4">
                      {successfulPatterns.valuePropositions.map((pattern, index) => (
                        <li key={index}>{pattern}</li>
                      ))}
                    </ul>
                  )}
                </div>
                
                {/* Qualification Questions */}
                <div className="bg-white rounded p-3 border">
                  <div className="font-medium text-sm">Qualification Questions</div>
                  {successfulPatterns.qualificationQuestions.length === 0 ? (
                    <div className="text-xs text-gray-500 mt-1">No patterns learned yet</div>
                  ) : (
                    <ul className="text-xs mt-1 list-disc pl-4">
                      {successfulPatterns.qualificationQuestions.map((pattern, index) => (
                        <li key={index}>{pattern}</li>
                      ))}
                    </ul>
                  )}
                </div>
                
                {/* Closing Techniques */}
                <div className="bg-white rounded p-3 border">
                  <div className="font-medium text-sm">Closing Techniques</div>
                  {successfulPatterns.closingTechniques.length === 0 ? (
                    <div className="text-xs text-gray-500 mt-1">No patterns learned yet</div>
                  ) : (
                    <ul className="text-xs mt-1 list-disc pl-4">
                      {successfulPatterns.closingTechniques.map((pattern, index) => (
                        <li key={index}>{pattern}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 
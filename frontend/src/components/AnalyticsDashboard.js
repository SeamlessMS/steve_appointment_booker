import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5001/api';

export default function AnalyticsDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    totalCalls: 0,
    successfulCalls: 0,
    appointmentsSet: 0,
    callCompletionRate: 0,
    averageCallDuration: 0,
    conversionRate: 0,
    callsByDay: [],
    callsByStatus: [],
    qualificationRate: 0
  });
  
  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      
      // Get all leads
      const leadsResponse = await axios.get(`${API_BASE}/leads`);
      const leads = leadsResponse.data || [];
      
      // Get all appointments
      const appointmentsResponse = await axios.get(`${API_BASE}/appointments`);
      const appointments = appointmentsResponse.data || [];
      
      // Get call logs (we might need to create a dedicated endpoint for this)
      const callLogsResponse = await axios.get(`${API_BASE}/call_logs/summary`);
      const callLogs = callLogsResponse.data || { 
        // Fallback if endpoint doesn't exist yet
        totalCalls: 0, 
        averageDuration: 0,
        callsByDay: [],
        callsByStatus: []
      };
      
      // Calculate metrics
      const totalLeads = leads.length;
      const calledLeads = leads.filter(lead => lead.status !== 'Not Called').length;
      const qualifiedLeads = leads.filter(lead => lead.qualification_status === 'Qualified').length;
      const appointmentsCount = appointments.length;
      
      // Update stats
      setStats({
        totalLeads,
        totalCalls: callLogs.totalCalls || calledLeads,
        successfulCalls: calledLeads,
        appointmentsSet: appointmentsCount,
        callCompletionRate: totalLeads > 0 ? (calledLeads / totalLeads) * 100 : 0,
        averageCallDuration: callLogs.averageDuration || 0,
        conversionRate: calledLeads > 0 ? (appointmentsCount / calledLeads) * 100 : 0,
        callsByDay: callLogs.callsByDay || [],
        callsByStatus: callLogs.callsByStatus || [],
        qualificationRate: calledLeads > 0 ? (qualifiedLeads / calledLeads) * 100 : 0
      });
      
      setError(null);
    } catch (err) {
      console.error('Error fetching analytics data:', err);
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchAnalytics();
  }, []);
  
  // Render a single stat card
  const StatCard = ({ title, value, description, color }) => (
    <div className={`bg-white rounded-lg shadow p-4 border-l-4 ${color}`}>
      <div className="font-bold text-xl mb-2">{title}</div>
      <div className="text-3xl font-bold mb-2">{value}</div>
      <div className="text-gray-600 text-sm">{description}</div>
    </div>
  );
  
  return (
    <div className="bg-gray-50 rounded-lg shadow p-6 mb-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">Call Analytics Dashboard</h2>
        <button
          onClick={fetchAnalytics}
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
      
      {loading ? (
        <div className="text-center py-8">
          <svg className="w-10 h-10 mx-auto animate-spin text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <p className="mt-2">Loading analytics data...</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <StatCard 
              title="Completion Rate" 
              value={`${stats.callCompletionRate.toFixed(1)}%`}
              description="Percentage of leads that have been called" 
              color="border-blue-500"
            />
            <StatCard 
              title="Conversion Rate" 
              value={`${stats.conversionRate.toFixed(1)}%`}
              description="Percentage of calls that resulted in appointments" 
              color="border-green-500"
            />
            <StatCard 
              title="Qualification Rate" 
              value={`${stats.qualificationRate.toFixed(1)}%`}
              description="Percentage of leads qualified" 
              color="border-purple-500"
            />
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <StatCard 
              title="Total Leads" 
              value={stats.totalLeads}
              description="Total number of leads in the system" 
              color="border-gray-500"
            />
            <StatCard 
              title="Total Calls" 
              value={stats.totalCalls}
              description="Total number of calls made" 
              color="border-blue-500"
            />
            <StatCard 
              title="Appointments" 
              value={stats.appointmentsSet}
              description="Total appointments set" 
              color="border-green-500"
            />
            <StatCard 
              title="Avg. Call Duration" 
              value={`${stats.averageCallDuration} sec`}
              description="Average call duration" 
              color="border-yellow-500"
            />
          </div>
          
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <h3 className="text-lg font-semibold mb-4">Call Status Distribution</h3>
            <div className="flex items-center h-8">
              {stats.callsByStatus.length > 0 ? (
                stats.callsByStatus.map((status, index) => (
                  <div 
                    key={index}
                    className="h-full relative group"
                    style={{
                      width: `${status.percentage}%`,
                      backgroundColor: getStatusColor(status.status),
                    }}
                  >
                    <div className="opacity-0 group-hover:opacity-100 absolute bottom-full left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs rounded px-2 py-1 mb-1 whitespace-nowrap transition-opacity">
                      {status.status}: {status.count} ({status.percentage.toFixed(1)}%)
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-gray-500 text-sm">No call status data available</div>
              )}
            </div>
            <div className="flex flex-wrap mt-4">
              {stats.callsByStatus.map((status, index) => (
                <div key={index} className="flex items-center mr-4 mb-2">
                  <div 
                    className="w-3 h-3 mr-1"
                    style={{ backgroundColor: getStatusColor(status.status) }}
                  ></div>
                  <span className="text-xs">{status.status}</span>
                </div>
              ))}
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-semibold mb-4">Calls by Day</h3>
            {stats.callsByDay.length > 0 ? (
              <div className="h-40 flex items-end space-x-1">
                {stats.callsByDay.map((day, index) => {
                  const maxCalls = Math.max(...stats.callsByDay.map(d => d.count));
                  const height = (day.count / maxCalls) * 100;
                  
                  return (
                    <div key={index} className="flex-1 flex flex-col items-center group">
                      <div className="text-xs text-gray-500 mb-1">{day.count}</div>
                      <div 
                        className="w-full bg-blue-500 rounded-t group-hover:bg-blue-600 transition-colors relative"
                        style={{ height: `${height}%` }}
                      ></div>
                      <div className="text-xs mt-1">{day.date}</div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-gray-500 text-sm">No call history data available</div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// Helper function to get colors for different call statuses
function getStatusColor(status) {
  const colors = {
    'Not Called': '#e5e7eb', // gray-200
    'Calling': '#93c5fd', // blue-300
    'Completed': '#86efac', // green-300
    'Interested': '#fcd34d', // yellow-300
    'Declined': '#fca5a5', // red-300
    'Appointment Set': '#c4b5fd', // purple-300
    'Disqualified': '#fca5a5', // red-300
    'Qualified': '#86efac', // green-300
    'Not Qualified': '#e5e7eb', // gray-200
  };
  
  return colors[status] || '#e5e7eb';
} 
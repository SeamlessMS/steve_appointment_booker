import React, { useState, useEffect } from 'react';
import { getFollowUps, updateFollowUp, runAutoFollowUp } from '../api';

const STATUS_COLORS = {
  'Pending': 'bg-yellow-200 text-yellow-700',
  'In Progress': 'bg-blue-200 text-blue-700',
  'Completed': 'bg-green-200 text-green-700',
  'Cancelled': 'bg-red-200 text-red-700',
};

const PRIORITY_LABELS = {
  1: 'Very Low',
  2: 'Low',
  3: 'Low',
  4: 'Low-Medium',
  5: 'Medium',
  6: 'Medium',
  7: 'Medium-High',
  8: 'High',
  9: 'High',
  10: 'Very High',
};

const PRIORITY_COLORS = {
  1: 'bg-green-100 text-green-800',
  2: 'bg-green-100 text-green-800',
  3: 'bg-green-100 text-green-800',
  4: 'bg-green-200 text-green-800',
  5: 'bg-yellow-100 text-yellow-800',
  6: 'bg-yellow-100 text-yellow-800',
  7: 'bg-yellow-200 text-yellow-800',
  8: 'bg-orange-100 text-orange-800',
  9: 'bg-red-100 text-red-800',
  10: 'bg-red-200 text-red-800',
};

export default function FollowUpList() {
  const [followUps, setFollowUps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('Pending');
  const [autoLoading, setAutoLoading] = useState(false);
  const [notification, setNotification] = useState({ show: false, message: '', type: '' });
  
  // Load follow-ups
  const loadFollowUps = async () => {
    setLoading(true);
    try {
      const filters = {};
      if (filter !== 'All') {
        filters.status = filter;
      }
      
      const data = await getFollowUps(filters);
      setFollowUps(data);
      setError(null);
    } catch (err) {
      console.error('Error loading follow-ups:', err);
      setError('Failed to load follow-ups. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  // Initial load
  useEffect(() => {
    loadFollowUps();
  }, [filter]);
  
  // Format the date/time
  const formatDateTime = (datetimeStr) => {
    try {
      // Parse the datetime string (expected format: "YYYY-MM-DD HH:MM:SS")
      const dt = new Date(datetimeStr.replace(' ', 'T'));
      return dt.toLocaleString();
    } catch (e) {
      return datetimeStr;
    }
  };
  
  // Handle status update
  const handleStatusChange = async (followUpId, newStatus) => {
    try {
      await updateFollowUp(followUpId, { status: newStatus });
      
      // Show notification
      setNotification({
        show: true,
        message: `Follow-up marked as ${newStatus}`,
        type: 'success'
      });
      
      // Reload the data
      loadFollowUps();
    } catch (err) {
      console.error('Error updating follow-up:', err);
      setNotification({
        show: true,
        message: 'Error updating follow-up status',
        type: 'error'
      });
    }
    
    // Hide notification after 3 seconds
    setTimeout(() => {
      setNotification({ show: false, message: '', type: '' });
    }, 3000);
  };
  
  // Handle auto follow-up
  const handleAutoFollowUp = async () => {
    setAutoLoading(true);
    try {
      const result = await runAutoFollowUp();
      
      if (result.data.count > 0) {
        setNotification({
          show: true,
          message: `Started ${result.data.count} follow-up calls`,
          type: 'success'
        });
      } else {
        setNotification({
          show: true,
          message: 'No follow-ups are currently due',
          type: 'info'
        });
      }
      
      // Reload the data
      loadFollowUps();
    } catch (err) {
      console.error('Error running auto follow-up:', err);
      
      // Check if it's an outside business hours error
      if (err.response && err.response.data && err.response.data.error === 'Outside of calling hours') {
        setNotification({
          show: true,
          message: 'Auto follow-up can only be run during business hours',
          type: 'error'
        });
      } else {
        setNotification({
          show: true,
          message: 'Error running auto follow-up',
          type: 'error'
        });
      }
    } finally {
      setAutoLoading(false);
    }
    
    // Hide notification after 3 seconds
    setTimeout(() => {
      setNotification({ show: false, message: '', type: '' });
    }, 3000);
  };
  
  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">Follow-Ups</h1>
        
        <div className="flex space-x-2">
          <select
            className="border p-2 rounded"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="All">All Follow-ups</option>
            <option value="Pending">Pending</option>
            <option value="In Progress">In Progress</option>
            <option value="Completed">Completed</option>
            <option value="Cancelled">Cancelled</option>
          </select>
          
          <button
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
            onClick={handleAutoFollowUp}
            disabled={autoLoading}
          >
            {autoLoading ? 'Processing...' : 'Run Auto Follow-up'}
          </button>
          
          <button
            className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
            onClick={loadFollowUps}
          >
            Refresh
          </button>
        </div>
      </div>
      
      {loading ? (
        <div className="flex justify-center py-6">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      ) : error ? (
        <div className="bg-red-100 border border-red-200 text-red-800 p-3 rounded">
          {error}
        </div>
      ) : followUps.length === 0 ? (
        <div className="bg-gray-100 p-4 rounded text-center">
          No follow-ups found for the selected filter.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-2 text-left">Lead</th>
                <th className="px-4 py-2 text-left">Scheduled Time</th>
                <th className="px-4 py-2 text-left">Priority</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Reason</th>
                <th className="px-4 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {followUps.map((followUp) => (
                <tr key={followUp.id} className="border-t">
                  <td className="px-4 py-2">
                    <div className="font-medium">{followUp.lead_name}</div>
                    <div className="text-sm text-gray-500">{followUp.lead_phone}</div>
                  </td>
                  <td className="px-4 py-2">{formatDateTime(followUp.scheduled_time)}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 rounded text-sm ${PRIORITY_COLORS[followUp.priority] || 'bg-gray-200'}`}>
                      {PRIORITY_LABELS[followUp.priority] || followUp.priority}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 rounded ${STATUS_COLORS[followUp.status] || 'bg-gray-200'}`}>
                      {followUp.status}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <div className="max-w-xs truncate" title={followUp.reason}>
                      {followUp.reason}
                    </div>
                  </td>
                  <td className="px-4 py-2 space-x-1">
                    {followUp.status !== 'Completed' && (
                      <button
                        className="bg-green-500 text-white px-2 py-1 rounded text-sm hover:bg-green-600"
                        onClick={() => handleStatusChange(followUp.id, 'Completed')}
                      >
                        Mark Complete
                      </button>
                    )}
                    {followUp.status !== 'Cancelled' && followUp.status !== 'Completed' && (
                      <button
                        className="bg-red-500 text-white px-2 py-1 rounded text-sm hover:bg-red-600"
                        onClick={() => handleStatusChange(followUp.id, 'Cancelled')}
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      {notification.show && (
        <div className={`fixed bottom-4 right-4 z-50 p-4 rounded shadow-lg ${
          notification.type === 'success' ? 'bg-green-100 text-green-800 border border-green-300' :
          notification.type === 'error' ? 'bg-red-100 text-red-800 border border-red-300' :
          'bg-blue-100 text-blue-800 border border-blue-300'
        }`}>
          {notification.message}
        </div>
      )}
    </div>
  );
} 
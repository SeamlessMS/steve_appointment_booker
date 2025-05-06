import React, { useState, useEffect } from 'react';
import { getLeadHistory } from '../api';

export default function LeadHistoryModal({ lead, open, onClose }) {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open && lead) {
      setLoading(true);
      getLeadHistory(lead.id)
        .then(data => {
          setHistory(data);
          setLoading(false);
        })
        .catch(err => {
          console.error("Error fetching lead history:", err);
          setError("Failed to load lead history");
          setLoading(false);
        });
    }
  }, [open, lead]);

  if (!open) return null;

  // Priority color coding for follow-ups
  const getPriorityColor = (priority) => {
    if (priority >= 8) return 'bg-red-100 text-red-800'; // High priority
    if (priority >= 5) return 'bg-orange-100 text-orange-800'; // Medium priority
    return 'bg-green-100 text-green-800'; // Low priority
  };
  
  // Status badge styling
  const getStatusBadge = (status) => {
    switch (status) {
      case 'Pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'Completed':
        return 'bg-green-100 text-green-800';
      case 'In Progress':
        return 'bg-blue-100 text-blue-800';
      case 'Cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white p-6 rounded shadow max-w-3xl w-full relative overflow-y-auto max-h-[90vh]">
        <button className="absolute top-2 right-2 text-xl" onClick={onClose}>&times;</button>
        <h2 className="text-lg font-bold mb-4">Lead History: {lead.name}</h2>
        
        {loading ? (
          <div className="flex justify-center py-6">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : error ? (
          <div className="bg-red-100 border border-red-200 text-red-800 p-3 rounded">
            {error}
          </div>
        ) : (
          <>
            <div className="flex justify-between mb-4">
              <div className="text-sm">
                <div><span className="font-bold">Phone:</span> {lead.phone}</div>
                <div><span className="font-bold">Industry:</span> {lead.industry || lead.category}</div>
              </div>
              <div className="text-sm">
                <div><span className="font-bold">Status:</span> {lead.status}</div>
                <div><span className="font-bold">Qualification:</span> {lead.qualification_status}</div>
              </div>
            </div>
            
            <h3 className="font-bold mb-2">Timeline</h3>
            
            {history && history.timeline.length > 0 ? (
              <div className="space-y-4">
                {history.timeline.map((item, index) => (
                  <div key={index} className="border-l-4 pl-4 py-2 relative">
                    <div className={`absolute w-3 h-3 rounded-full -left-[6.5px] top-4 ${
                      item.type === 'call_log' 
                        ? 'bg-blue-500' 
                        : item.type === 'appointment' 
                          ? 'bg-purple-500' 
                          : item.type === 'follow_up'
                            ? 'bg-orange-500'
                            : 'bg-yellow-500'
                    }`}></div>
                    
                    <div className="flex justify-between mb-1">
                      <span className="font-bold">
                        {item.type === 'call_log' 
                          ? `Call ${item.status}` 
                          : item.type === 'appointment' 
                            ? `Appointment (${item.medium})` 
                            : item.type === 'follow_up'
                              ? `Follow-up (Priority: ${item.priority})`
                              : `Qualification: ${item.status}`}
                      </span>
                      <span className="text-gray-500 text-sm">{item.timestamp}</span>
                    </div>
                    
                    {item.type === 'call_log' && item.transcript && (
                      <div className="text-sm mt-1 whitespace-pre-wrap bg-gray-50 p-2 rounded">
                        {item.transcript}
                      </div>
                    )}
                    
                    {item.type === 'appointment' && (
                      <div className="text-sm mt-1">
                        <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded">
                          {item.data.date} at {item.data.time}
                        </span>
                        <span className="ml-2">{item.status}</span>
                      </div>
                    )}
                    
                    {item.type === 'follow_up' && (
                      <div className="text-sm mt-1">
                        <span className={`${getStatusBadge(item.status)} px-2 py-1 rounded mr-2`}>
                          {item.status}
                        </span>
                        <span className={`${getPriorityColor(item.priority)} px-2 py-1 rounded`}>
                          Priority: {item.priority}
                        </span>
                        {item.reason && (
                          <div className="mt-1 bg-gray-50 p-2 rounded">
                            {item.reason}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {item.type === 'qualification' && (
                      <div className="text-sm mt-1">
                        <div><span className="font-semibold">Employees:</span> {item.data.employee_count}</div>
                        <div><span className="font-semibold">Uses Mobile:</span> {item.data.uses_mobile_devices}</div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-500 py-4 text-center">No history available for this lead</div>
            )}
            
          </>
        )}
      </div>
    </div>
  );
} 
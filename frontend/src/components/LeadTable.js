import React, { useState } from 'react';
import { callLead, updateLead, getCallLogs } from '../api';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5002/api';

const STATUS_COLORS = {
  'Not Called': 'bg-gray-200 text-gray-700',
  'Calling': 'bg-blue-200 text-blue-700',
  'Completed': 'bg-green-200 text-green-700',
  'Interested': 'bg-yellow-200 text-yellow-700',
  'Declined': 'bg-red-200 text-red-700',
  'Appointment Set': 'bg-purple-200 text-purple-700',
  'Disqualified': 'bg-red-200 text-red-700',
  'Qualified': 'bg-green-200 text-green-700',
  'Not Qualified': 'bg-gray-200 text-gray-700',
};

export default function LeadTable({ leads, onStatusChange }) {
  const [loadingId, setLoadingId] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [showQualifyModal, setShowQualifyModal] = useState(false);
  const [showAppointmentModal, setShowAppointmentModal] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [qualificationData, setQualificationData] = useState({
    qualified: false,
    uses_mobile_devices: 'Unknown',
    employee_count: 0,
    notes: ''
  });
  const [appointmentData, setAppointmentData] = useState({
    date: '',
    time: '',
    medium: 'Phone'
  });
  const [availableTimes, setAvailableTimes] = useState([]);

  const handleCall = async (lead) => {
    setLoadingId(lead.id);
    await callLead(lead.id);
    onStatusChange();
    setLoadingId(null);
  };

  const handleClose = async (lead) => {
    setLoadingId(lead.id);
    await updateLead(lead.id, { status: 'Completed' });
    onStatusChange();
    setLoadingId(null);
  };

  const handleTranscript = async (lead) => {
    const logs = await getCallLogs(lead.id);
    if (logs.length > 0) setTranscript(logs[0].transcript);
    else setTranscript('No transcript found.');
  };

  const openQualifyModal = (lead) => {
    setSelectedLead(lead);
    setQualificationData({
      qualified: lead.qualification_status === 'Qualified',
      uses_mobile_devices: lead.uses_mobile_devices || 'Unknown',
      employee_count: lead.employee_count || 0,
      notes: lead.notes || ''
    });
    setShowQualifyModal(true);
  };

  const closeQualifyModal = () => {
    setShowQualifyModal(false);
    setSelectedLead(null);
  };

  const saveQualification = async () => {
    if (!selectedLead) return;
    
    setLoadingId(selectedLead.id);
    
    try {
      await axios.post(`${API_BASE}/qualify/${selectedLead.id}`, qualificationData);
      onStatusChange();
      closeQualifyModal();
    } catch (error) {
      console.error("Error saving qualification:", error);
    } finally {
      setLoadingId(null);
    }
  };

  const openAppointmentModal = async (lead) => {
    setSelectedLead(lead);
    
    // Default to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const formattedDate = tomorrow.toISOString().split('T')[0];
    
    setAppointmentData({
      date: formattedDate,
      time: '10:00',
      medium: 'Phone'
    });
    
    // Load available times
    try {
      const response = await axios.get(`${API_BASE}/availability?date=${formattedDate}`);
      setAvailableTimes(response.data);
    } catch (error) {
      console.error("Error fetching available times:", error);
      setAvailableTimes(['09:00', '10:00', '11:00', '13:00', '14:00', '15:00', '16:00']);
    }
    
    setShowAppointmentModal(true);
  };

  const closeAppointmentModal = () => {
    setShowAppointmentModal(false);
    setSelectedLead(null);
  };

  const handleDateChange = async (e) => {
    const newDate = e.target.value;
    setAppointmentData({...appointmentData, date: newDate});
    
    // Update available times for selected date
    try {
      const response = await axios.get(`${API_BASE}/availability?date=${newDate}`);
      setAvailableTimes(response.data);
    } catch (error) {
      console.error("Error fetching available times:", error);
    }
  };

  const saveAppointment = async () => {
    if (!selectedLead) return;
    
    setLoadingId(selectedLead.id);
    
    try {
      await axios.post(`${API_BASE}/appointments`, {
        lead_id: selectedLead.id,
        ...appointmentData
      });
      onStatusChange();
      closeAppointmentModal();
    } catch (error) {
      console.error("Error saving appointment:", error);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div>
      <table className="min-w-full bg-white rounded shadow overflow-hidden">
        <thead>
          <tr>
            <th className="px-4 py-2">Business Name</th>
            <th className="px-4 py-2">Phone</th>
            <th className="px-4 py-2">Industry</th>
            <th className="px-4 py-2">Employees</th>
            <th className="px-4 py-2">Mobile</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2">Qualification</th>
            <th className="px-4 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr key={lead.id} className="border-t">
              <td className="px-4 py-2">{lead.name}</td>
              <td className="px-4 py-2">{lead.phone}</td>
              <td className="px-4 py-2">{lead.industry || lead.category}</td>
              <td className="px-4 py-2">{lead.employee_count || 'Unknown'}</td>
              <td className="px-4 py-2">{lead.uses_mobile_devices || 'Unknown'}</td>
              <td className="px-4 py-2">
                <span className={`px-2 py-1 rounded text-xs font-semibold ${STATUS_COLORS[lead.status] || ''}`}>{lead.status}</span>
              </td>
              <td className="px-4 py-2">
                <span className={`px-2 py-1 rounded text-xs font-semibold ${STATUS_COLORS[lead.qualification_status] || ''}`}>{lead.qualification_status}</span>
              </td>
              <td className="px-4 py-2 space-x-2 flex flex-wrap">
                <button
                  className="bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600 disabled:opacity-50"
                  disabled={loadingId === lead.id || lead.status === 'Calling'}
                  onClick={() => handleCall(lead)}
                >
                  Call
                </button>
                <button
                  className="bg-yellow-500 text-white px-3 py-1 rounded hover:bg-yellow-600 disabled:opacity-50"
                  disabled={loadingId === lead.id}
                  onClick={() => openQualifyModal(lead)}
                >
                  Qualify
                </button>
                <button
                  className="bg-purple-500 text-white px-3 py-1 rounded hover:bg-purple-600 disabled:opacity-50"
                  disabled={loadingId === lead.id || lead.qualification_status !== 'Qualified'}
                  onClick={() => openAppointmentModal(lead)}
                >
                  Book
                </button>
                <button
                  className="bg-green-500 text-white px-3 py-1 rounded hover:bg-green-600"
                  onClick={() => handleTranscript(lead)}
                >
                  Transcript
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Transcript Modal */}
      {transcript && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
          <div className="bg-white p-6 rounded shadow max-w-lg w-full relative">
            <button className="absolute top-2 right-2 text-xl" onClick={() => setTranscript(null)}>&times;</button>
            <h2 className="text-lg font-bold mb-2">Call Transcript</h2>
            <pre className="whitespace-pre-wrap text-sm">{transcript}</pre>
          </div>
        </div>
      )}

      {/* Qualify Lead Modal */}
      {showQualifyModal && selectedLead && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
          <div className="bg-white p-6 rounded shadow max-w-lg w-full relative">
            <button className="absolute top-2 right-2 text-xl" onClick={closeQualifyModal}>&times;</button>
            <h2 className="text-lg font-bold mb-4">Qualify Lead: {selectedLead.name}</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Qualification Status</label>
                <select 
                  className="w-full border p-2 rounded"
                  value={qualificationData.qualified ? "qualified" : "not_qualified"}
                  onChange={(e) => setQualificationData({...qualificationData, qualified: e.target.value === "qualified"})}
                >
                  <option value="not_qualified">Not Qualified</option>
                  <option value="qualified">Qualified</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Uses Mobile Devices</label>
                <select 
                  className="w-full border p-2 rounded"
                  value={qualificationData.uses_mobile_devices}
                  onChange={(e) => setQualificationData({...qualificationData, uses_mobile_devices: e.target.value})}
                >
                  <option value="Unknown">Unknown</option>
                  <option value="Yes">Yes</option>
                  <option value="No">No</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Employee Count</label>
                <input 
                  type="number" 
                  className="w-full border p-2 rounded"
                  value={qualificationData.employee_count}
                  onChange={(e) => setQualificationData({...qualificationData, employee_count: parseInt(e.target.value) || 0})}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Notes</label>
                <textarea 
                  className="w-full border p-2 rounded"
                  value={qualificationData.notes}
                  onChange={(e) => setQualificationData({...qualificationData, notes: e.target.value})}
                  rows={3}
                />
              </div>
            </div>
            
            <div className="mt-4 flex justify-end space-x-3">
              <button 
                className="px-4 py-2 border rounded hover:bg-gray-100"
                onClick={closeQualifyModal}
              >
                Cancel
              </button>
              <button 
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                onClick={saveQualification}
                disabled={loadingId === selectedLead.id}
              >
                {loadingId === selectedLead.id ? 'Saving...' : 'Save Qualification'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Book Appointment Modal */}
      {showAppointmentModal && selectedLead && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
          <div className="bg-white p-6 rounded shadow max-w-lg w-full relative">
            <button className="absolute top-2 right-2 text-xl" onClick={closeAppointmentModal}>&times;</button>
            <h2 className="text-lg font-bold mb-4">Book Appointment: {selectedLead.name}</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Date</label>
                <input 
                  type="date" 
                  className="w-full border p-2 rounded"
                  value={appointmentData.date}
                  onChange={handleDateChange}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Time</label>
                <select 
                  className="w-full border p-2 rounded"
                  value={appointmentData.time}
                  onChange={(e) => setAppointmentData({...appointmentData, time: e.target.value})}
                >
                  {availableTimes.map(time => (
                    <option key={time} value={time}>{time}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Medium</label>
                <select 
                  className="w-full border p-2 rounded"
                  value={appointmentData.medium}
                  onChange={(e) => setAppointmentData({...appointmentData, medium: e.target.value})}
                >
                  <option value="Phone">Phone Call</option>
                  <option value="Zoom">Zoom Meeting</option>
                  <option value="In-Person">In-Person</option>
                </select>
              </div>
            </div>
            
            <div className="mt-4 flex justify-end space-x-3">
              <button 
                className="px-4 py-2 border rounded hover:bg-gray-100"
                onClick={closeAppointmentModal}
              >
                Cancel
              </button>
              <button 
                className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50"
                onClick={saveAppointment}
                disabled={loadingId === selectedLead.id}
              >
                {loadingId === selectedLead.id ? 'Booking...' : 'Book Appointment'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

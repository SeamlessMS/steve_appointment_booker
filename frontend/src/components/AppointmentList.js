import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5002/api';

const STATUS_COLORS = {
  'Scheduled': 'bg-blue-200 text-blue-700',
  'Completed': 'bg-green-200 text-green-700',
  'Canceled': 'bg-red-200 text-red-700',
  'Rescheduled': 'bg-yellow-200 text-yellow-700',
};

export default function AppointmentList() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingAppointment, setEditingAppointment] = useState(null);
  const [appointmentData, setAppointmentData] = useState({
    date: '',
    time: '',
    status: '',
    medium: ''
  });
  const [availableTimes, setAvailableTimes] = useState([]);

  // Fetch appointments on component mount
  useEffect(() => {
    fetchAppointments();
  }, []);

  // Fetch appointments from API
  const fetchAppointments = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/appointments`);
      setAppointments(response.data);
    } catch (error) {
      console.error("Error fetching appointments:", error);
    } finally {
      setLoading(false);
    }
  };

  // Handle editing an appointment
  const handleEdit = async (appointment) => {
    setEditingAppointment(appointment);
    setAppointmentData({
      date: appointment.date,
      time: appointment.time,
      status: appointment.status,
      medium: appointment.medium
    });
    
    // Fetch available times for this date
    try {
      const response = await axios.get(`${API_BASE}/availability?date=${appointment.date}`);
      // Include the current time in the available times
      if (!response.data.includes(appointment.time)) {
        response.data.push(appointment.time);
        response.data.sort();
      }
      setAvailableTimes(response.data);
    } catch (error) {
      console.error("Error fetching available times:", error);
      setAvailableTimes([appointment.time, '09:00', '10:00', '11:00', '13:00', '14:00', '15:00']);
    }
  };

  // Handle date change when editing
  const handleDateChange = async (e) => {
    const newDate = e.target.value;
    setAppointmentData({...appointmentData, date: newDate});
    
    // Update available times for the new date
    try {
      const response = await axios.get(`${API_BASE}/availability?date=${newDate}`);
      setAvailableTimes(response.data);
    } catch (error) {
      console.error("Error fetching available times:", error);
    }
  };

  // Save edited appointment
  const saveAppointment = async () => {
    if (!editingAppointment) return;
    
    try {
      await axios.patch(`${API_BASE}/appointments/${editingAppointment.id}`, appointmentData);
      setEditingAppointment(null);
      fetchAppointments();
    } catch (error) {
      console.error("Error updating appointment:", error);
    }
  };

  // Cancel editing
  const cancelEdit = () => {
    setEditingAppointment(null);
  };

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString();
    } catch (e) {
      return dateStr;
    }
  };

  if (loading) {
    return <div className="text-center py-4">Loading appointments...</div>;
  }

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Scheduled Appointments</h2>
      
      {appointments.length === 0 ? (
        <div className="text-center py-8 bg-gray-50 rounded">
          No appointments scheduled yet.
        </div>
      ) : (
        <table className="min-w-full bg-white rounded shadow overflow-hidden">
          <thead>
            <tr>
              <th className="px-4 py-2">Business</th>
              <th className="px-4 py-2">Phone</th>
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2">Time</th>
              <th className="px-4 py-2">Medium</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {appointments.map((appointment) => (
              <tr key={appointment.id} className="border-t">
                <td className="px-4 py-2">{appointment.lead_name}</td>
                <td className="px-4 py-2">{appointment.lead_phone}</td>
                <td className="px-4 py-2">{formatDate(appointment.date)}</td>
                <td className="px-4 py-2">{appointment.time}</td>
                <td className="px-4 py-2">{appointment.medium}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${STATUS_COLORS[appointment.status] || ''}`}>
                    {appointment.status}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <button
                    className="bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600"
                    onClick={() => handleEdit(appointment)}
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      
      {/* Edit Appointment Modal */}
      {editingAppointment && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
          <div className="bg-white p-6 rounded shadow max-w-lg w-full relative">
            <button className="absolute top-2 right-2 text-xl" onClick={cancelEdit}>&times;</button>
            <h2 className="text-lg font-bold mb-4">Edit Appointment</h2>
            
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
              
              <div>
                <label className="block text-sm font-medium mb-1">Status</label>
                <select 
                  className="w-full border p-2 rounded"
                  value={appointmentData.status}
                  onChange={(e) => setAppointmentData({...appointmentData, status: e.target.value})}
                >
                  <option value="Scheduled">Scheduled</option>
                  <option value="Completed">Completed</option>
                  <option value="Canceled">Canceled</option>
                  <option value="Rescheduled">Rescheduled</option>
                </select>
              </div>
            </div>
            
            <div className="mt-4 flex justify-end space-x-3">
              <button 
                className="px-4 py-2 border rounded hover:bg-gray-100"
                onClick={cancelEdit}
              >
                Cancel
              </button>
              <button 
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                onClick={saveAppointment}
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 
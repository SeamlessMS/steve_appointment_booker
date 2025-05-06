import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5002/api';

const STATUS_COLORS = {
  'Scheduled': 'bg-blue-200 text-blue-700',
  'Completed': 'bg-green-200 text-green-700',
  'Canceled': 'bg-red-200 text-red-700',
  'Rescheduled': 'bg-yellow-200 text-yellow-700',
  'Confirmed': 'bg-indigo-200 text-indigo-700',
};

export default function AppointmentList() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingAppointment, setEditingAppointment] = useState(null);
  const [viewingPrepScript, setViewingPrepScript] = useState(null);
  const [appointmentData, setAppointmentData] = useState({
    date: '',
    time: '',
    status: '',
    medium: '',
    notes: ''
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
      medium: appointment.medium,
      notes: appointment.notes || ''
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

  // Generate a preparation script based on the Schiffman methodology
  const generatePrepScript = (appointment) => {
    const leadName = appointment.lead_name;
    const appointmentDate = formatDate(appointment.date);
    const appointmentTime = appointment.time;
    const medium = appointment.medium;
    const phone = appointment.lead_phone;
    
    return {
      title: `Schiffman Prep for ${leadName}`,
      sections: [
        {
          title: "Pre-Appointment Preparation",
          content: [
            `Call scheduled for ${appointmentDate} at ${appointmentTime} via ${medium}`,
            `Client business: ${leadName}`,
            `Contact number: ${phone}`
          ]
        },
        {
          title: "Schiffman Opening (30 Seconds)",
          content: [
            "Thank you for taking time to meet with me today.",
            "As I mentioned in our previous conversation, I help businesses improve their mobile device management and reduce costs.",
            "In our time today, I'd like to understand your current mobile setup, share how we've helped similar businesses, and determine if there's a fit."
          ]
        },
        {
          title: "Questioning Strategy (10 Minutes)",
          content: [
            "How many mobile devices does your company currently manage?",
            "What's your current process for procurement and management?",
            "What are your biggest challenges with your mobile devices?",
            "How much time does your team spend managing these devices?",
            "What are your current mobile-related costs?"
          ]
        },
        {
          title: "Present Value (5 Minutes)",
          content: [
            "Based on what you've shared, I believe we can help in three specific ways:",
            "1. Reduce your mobile costs by approximately 20%",
            "2. Improve security and compliance across all devices",
            "3. Streamline management to save IT staff time"
          ]
        },
        {
          title: "Closing Strategy (5 Minutes)",
          content: [
            "Would it make sense to proceed with a detailed analysis of your current mobile infrastructure?",
            "Our next step would be a 30-minute technical assessment with one of our solution architects.",
            "We can schedule that now if you're interested in exploring this further."
          ]
        }
      ]
    };
  };

  // Handle viewing preparation script
  const handleViewPrepScript = (appointment) => {
    const script = generatePrepScript(appointment);
    setViewingPrepScript({
      appointment: appointment,
      script: script
    });
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

  // Mark appointment as confirmed
  const confirmAppointment = async (appointment) => {
    try {
      await axios.patch(`${API_BASE}/appointments/${appointment.id}`, {
        status: 'Confirmed'
      });
      fetchAppointments();
    } catch (error) {
      console.error("Error confirming appointment:", error);
    }
  };

  // Cancel editing
  const cancelEdit = () => {
    setEditingAppointment(null);
  };

  // Close prep script modal
  const closePrepScript = () => {
    setViewingPrepScript(null);
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

  // Get days until appointment
  const getDaysUntil = (dateStr) => {
    if (!dateStr) return '';
    try {
      const appointmentDate = new Date(dateStr);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      const diffTime = appointmentDate - today;
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDays === 0) return 'Today';
      if (diffDays === 1) return 'Tomorrow';
      if (diffDays < 0) return `${Math.abs(diffDays)} days ago`;
      return `In ${diffDays} days`;
    } catch (e) {
      return '';
    }
  };

  if (loading) {
    return <div className="text-center py-4">Loading appointments...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Scheduled Appointments</h2>
        <div className="text-sm text-gray-500">
          Using the Schiffman Method for appointment success
        </div>
      </div>
      
      {appointments.length === 0 ? (
        <div className="text-center py-8 bg-gray-50 rounded">
          No appointments scheduled yet.
        </div>
      ) : (
        <div className="bg-white rounded shadow overflow-hidden">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">Business</th>
                <th className="px-4 py-2 text-left">Date</th>
                <th className="px-4 py-2 text-left">Time</th>
                <th className="px-4 py-2 text-left">Timeline</th>
                <th className="px-4 py-2 text-left">Medium</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {appointments.map((appointment) => (
                <tr key={appointment.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium">{appointment.lead_name}</div>
                    <div className="text-xs text-gray-500">{appointment.lead_phone}</div>
                  </td>
                  <td className="px-4 py-3">{formatDate(appointment.date)}</td>
                  <td className="px-4 py-3">{appointment.time}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      getDaysUntil(appointment.date) === 'Today' ? 'bg-green-100 text-green-800' : 
                      getDaysUntil(appointment.date) === 'Tomorrow' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {getDaysUntil(appointment.date)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex items-center">
                      {appointment.medium === 'Phone' && (
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01" />
                        </svg>
                      )}
                      {appointment.medium === 'Zoom' && (
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      )}
                      {appointment.medium === 'In-Person' && (
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                        </svg>
                      )}
                      {appointment.medium}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${STATUS_COLORS[appointment.status] || ''}`}>
                      {appointment.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex space-x-2">
                      <button
                        className="bg-purple-500 text-white px-2 py-1 rounded text-xs hover:bg-purple-600"
                        onClick={() => handleViewPrepScript(appointment)}
                        title="View Meeting Prep"
                      >
                        Prep
                      </button>
                      
                      {appointment.status !== 'Confirmed' && appointment.status !== 'Completed' && (
                        <button
                          className="bg-indigo-500 text-white px-2 py-1 rounded text-xs hover:bg-indigo-600"
                          onClick={() => confirmAppointment(appointment)}
                          title="Mark as Confirmed"
                        >
                          Confirm
                        </button>
                      )}
                      
                      <button
                        className="bg-blue-500 text-white px-2 py-1 rounded text-xs hover:bg-blue-600"
                        onClick={() => handleEdit(appointment)}
                        title="Edit Appointment"
                      >
                        Edit
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
                  <option value="Confirmed">Confirmed</option>
                  <option value="Completed">Completed</option>
                  <option value="Canceled">Canceled</option>
                  <option value="Rescheduled">Rescheduled</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Notes</label>
                <textarea
                  className="w-full border p-2 rounded"
                  value={appointmentData.notes}
                  onChange={(e) => setAppointmentData({...appointmentData, notes: e.target.value})}
                  rows="3"
                  placeholder="Add any specific details about this appointment"
                ></textarea>
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
      
      {/* Preparation Script Modal */}
      {viewingPrepScript && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
          <div className="bg-white p-6 rounded shadow max-w-3xl w-full relative overflow-y-auto max-h-screen">
            <button className="absolute top-2 right-2 text-xl" onClick={closePrepScript}>&times;</button>
            <h2 className="text-xl font-bold mb-1">{viewingPrepScript.script.title}</h2>
            <p className="text-sm text-gray-500 mb-4">
              Appointment with {viewingPrepScript.appointment.lead_name} on {formatDate(viewingPrepScript.appointment.date)} at {viewingPrepScript.appointment.time}
            </p>
            
            <div className="space-y-6">
              {viewingPrepScript.script.sections.map((section, index) => (
                <div key={index} className="border-l-4 border-indigo-500 pl-4">
                  <h3 className="font-bold text-lg mb-2">{section.title}</h3>
                  <ul className="space-y-2">
                    {section.content.map((item, itemIndex) => (
                      <li key={itemIndex} className="flex items-start">
                        <span className="inline-block w-4 h-4 rounded-full bg-indigo-100 text-indigo-700 text-xs flex items-center justify-center mr-2 mt-1">
                          {itemIndex + 1}
                        </span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            
            <div className="mt-6 bg-blue-50 p-4 rounded border border-blue-200">
              <h3 className="font-bold text-blue-700 mb-2">Schiffman Appointment Tips</h3>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Always be on time - preferably 5 minutes early</li>
                <li>• Stick to your timing structure (30-second opening, 10-minute questioning, etc.)</li>
                <li>• Focus on discovering problems, not pushing solutions</li>
                <li>• Use the 3 Fs: Fact finding, Future, Fit determination</li>
                <li>• Book the next meeting before concluding this one</li>
              </ul>
            </div>
            
            <div className="mt-4 flex justify-end">
              <button 
                className="px-4 py-2 bg-indigo-500 text-white rounded hover:bg-indigo-600"
                onClick={closePrepScript}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 
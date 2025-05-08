import React, { useState, useEffect } from 'react';
import { callLead, manualCallLead, autoDialLeads, checkBusinessHours, updateLead, getCallLogs, addFollowUp, deleteLead, deleteLeads } from '../api';
import axios from 'axios';
import LeadHistoryModal from './LeadHistoryModal';

// Get API base from the imported functions (used in axios calls)
const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5001/api';

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
  const [showFollowUpModal, setShowFollowUpModal] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [withinBusinessHours, setWithinBusinessHours] = useState(true);
  const [businessHoursInfo, setBusinessHoursInfo] = useState({});
  const [selectedLeads, setSelectedLeads] = useState([]);
  const [notification, setNotification] = useState({ show: false, message: '', type: '' });
  const [appConfig, setAppConfig] = useState({ CONFIRM_DELETIONS: true });
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
  const [followUpData, setFollowUpData] = useState({
    scheduled_time: '',
    priority: 5,
    reason: '',
    notes: ''
  });
  const [availableTimes, setAvailableTimes] = useState([]);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [leadsPerPage, setLeadsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('All');
  const [sortField, setSortField] = useState('name');
  const [sortDirection, setSortDirection] = useState('asc');

  useEffect(() => {
    // Check business hours when component mounts
    checkBusinessHours()
      .then(data => {
        setWithinBusinessHours(data.within_business_hours);
        setBusinessHoursInfo(data.business_hours);
      })
      .catch(error => {
        console.error("Error checking business hours:", error);
        setWithinBusinessHours(false);
      });
      
    // Load app settings
    axios.get(`${API_BASE}/config`)
      .then(response => {
        setAppConfig(response.data);
      })
      .catch(error => {
        console.error("Error loading app settings:", error);
      });
  }, []);

  // Reset pagination when leads change
  useEffect(() => {
    setCurrentPage(1);
  }, [leads.length, searchTerm, filterStatus]);

  const handleCall = async (lead) => {
    setLoadingId(lead.id);
    try {
      await callLead(lead.id);
      onStatusChange();
    } catch (error) {
      // Show error notification if outside business hours
      if (error.response && error.response.status === 400) {
        setNotification({
          show: true,
          type: 'error',
          message: error.response.data.message || 'Cannot call outside business hours'
        });
        // Hide after 5 seconds
        setTimeout(() => setNotification({ show: false, message: '', type: '' }), 5000);
      }
    } finally {
      setLoadingId(null);
    }
  };

  const handleManualCall = async (lead) => {
    setLoadingId(lead.id);
    try {
      await manualCallLead(lead.id);
      onStatusChange();
    } catch (error) {
      console.error("Error making manual call:", error);
      setNotification({
        show: true,
        type: 'error',
        message: 'Error making manual call'
      });
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 5000);
    } finally {
      setLoadingId(null);
    }
  };

  const handleClose = async (lead) => {
    setLoadingId(lead.id);
    await updateLead(lead.id, { status: 'Completed' });
    onStatusChange();
    setLoadingId(null);
  };

  const handleAutoDialer = async () => {
    if (selectedLeads.length === 0) {
      setNotification({
        show: true,
        type: 'error',
        message: 'Please select at least one lead to auto-dial'
      });
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 5000);
      return;
    }

    try {
      const response = await autoDialLeads(selectedLeads);
      onStatusChange();
      setNotification({
        show: true,
        type: 'success',
        message: `Auto-dialer started for ${selectedLeads.length} leads`
      });
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 5000);
      setSelectedLeads([]);
    } catch (error) {
      // Show error message if outside business hours
      if (error.response && error.response.status === 400) {
        setNotification({
          show: true,
          type: 'error',
          message: error.response.data.message || 'Auto-dialer can only be used during business hours'
        });
      } else {
        setNotification({
          show: true,
          type: 'error',
          message: 'Error starting auto-dialer'
        });
      }
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 5000);
    }
  };

  const handleDeleteLeads = async () => {
    if (selectedLeads.length === 0) {
      setNotification({
        show: true,
        type: 'error',
        message: 'Please select at least one lead to delete'
      });
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 5000);
      return;
    }

    // Check if confirmations are enabled and if user confirms deletion
    const shouldDelete = !appConfig.CONFIRM_DELETIONS || 
      window.confirm(`Are you sure you want to delete ${selectedLeads.length} lead(s)? This action cannot be undone.`);
    
    if (!shouldDelete) {
      return;
    }

    try {
      await deleteLeads(selectedLeads);
      setNotification({
        show: true,
        type: 'success',
        message: `${selectedLeads.length} lead(s) deleted successfully`
      });
      setSelectedLeads([]);
      onStatusChange(); // Refresh the leads list
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 5000);
    } catch (error) {
      console.error("Error deleting leads:", error);
      setNotification({
        show: true,
        type: 'error',
        message: 'Error deleting leads: ' + (error.response?.data?.error || error.message)
      });
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 5000);
    }
  };

  const handleDeleteLead = async (leadId) => {
    // Check if confirmations are enabled and if user confirms deletion
    const shouldDelete = !appConfig.CONFIRM_DELETIONS || 
      window.confirm("Are you sure you want to delete this lead? This action cannot be undone.");
    
    if (!shouldDelete) {
      return;
    }

    try {
      setLoadingId(leadId);
      await deleteLead(leadId);
      setNotification({
        show: true,
        type: 'success',
        message: 'Lead deleted successfully'
      });
      onStatusChange(); // Refresh the leads list
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 5000);
    } catch (error) {
      console.error("Error deleting lead:", error);
      setNotification({
        show: true,
        type: 'error',
        message: 'Error deleting lead: ' + (error.response?.data?.error || error.message)
      });
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 5000);
    } finally {
      setLoadingId(null);
    }
  };
  
  const toggleSelectAll = () => {
    if (selectedLeads.length === leads.length) {
      // If all leads are selected, deselect all
      setSelectedLeads([]);
    } else {
      // Otherwise, select all leads
      setSelectedLeads(leads.map(lead => lead.id));
    }
  };

  const toggleLeadSelection = (leadId) => {
    if (selectedLeads.includes(leadId)) {
      setSelectedLeads(selectedLeads.filter(id => id !== leadId));
    } else {
      setSelectedLeads([...selectedLeads, leadId]);
    }
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

  const openFollowUpModal = (lead) => {
    setSelectedLead(lead);
    
    // Default to tomorrow at 10 AM
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(10, 0, 0, 0);
    const formattedDateTime = tomorrow.toISOString().slice(0, 16); // Format as YYYY-MM-DDTHH:MM
    
    setFollowUpData({
      scheduled_time: formattedDateTime,
      priority: 5,
      reason: `Follow-up with ${lead.name}`,
      notes: ''
    });
    
    setShowFollowUpModal(true);
  };

  const closeFollowUpModal = () => {
    setShowFollowUpModal(false);
    setSelectedLead(null);
  };

  const saveFollowUp = async () => {
    if (!selectedLead) return;
    
    setLoadingId(selectedLead.id);
    
    try {
      // Convert local datetime to SQLite format (YYYY-MM-DD HH:MM:SS)
      const scheduledDate = new Date(followUpData.scheduled_time);
      const formattedTime = scheduledDate.toISOString().replace('T', ' ').substring(0, 19);
      
      await addFollowUp({
        lead_id: selectedLead.id,
        scheduled_time: formattedTime,
        priority: followUpData.priority,
        reason: followUpData.reason,
        notes: followUpData.notes
      });
      
      onStatusChange();
      closeFollowUpModal();
      
      // Show success notification
      setNotification({
        show: true,
        message: `Follow-up scheduled for ${selectedLead.name}`,
        type: 'success'
      });
      
      // Hide notification after 3 seconds
      setTimeout(() => {
        setNotification({ show: false, message: '', type: '' });
      }, 3000);
      
    } catch (error) {
      console.error("Error scheduling follow-up:", error);
      setNotification({
        show: true,
        message: `Error scheduling follow-up: ${error.message}`,
        type: 'error'
      });
      
      // Hide notification after 5 seconds
      setTimeout(() => {
        setNotification({ show: false, message: '', type: '' });
      }, 5000);
    } finally {
      setLoadingId(null);
    }
  };

  const openHistoryModal = (lead) => {
    setSelectedLead(lead);
    setShowHistoryModal(true);
  };

  // Sorting and filtering logic
  const sortLeads = (leadsToSort) => {
    return [...leadsToSort].sort((a, b) => {
      let aValue = a[sortField];
      let bValue = b[sortField];
      
      // Handle special sort cases
      if (sortField === 'employee_count') {
        aValue = parseInt(aValue) || 0;
        bValue = parseInt(bValue) || 0;
      }
      
      if (sortDirection === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
  };

  const handleSort = (field) => {
    // If clicking on the current sort field, toggle direction
    if (field === sortField) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New field, default to ascending
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Filter leads by search term and status
  const filteredLeads = leads.filter(lead => {
    const matchesSearch = 
      (lead.name && lead.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (lead.phone && lead.phone.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (lead.industry && lead.industry.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (lead.category && lead.category.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesStatus = filterStatus === 'All' || lead.status === filterStatus;
    
    return matchesSearch && matchesStatus;
  });

  // Sort the filtered leads
  const sortedLeads = sortLeads(filteredLeads);
  
  // Get current leads for pagination
  const indexOfLastLead = currentPage * leadsPerPage;
  const indexOfFirstLead = indexOfLastLead - leadsPerPage;
  const currentLeads = sortedLeads.slice(indexOfFirstLead, indexOfLastLead);
  
  // Change page
  const paginate = (pageNumber) => setCurrentPage(pageNumber);

  return (
    <div>
      {notification.show && (
        <div className={`mb-4 p-3 rounded ${
          notification.type === 'success' ? 'bg-green-100 text-green-800 border border-green-200' 
          : 'bg-red-100 text-red-800 border border-red-200'
        }`}>
          {notification.message}
        </div>
      )}

      <div className="mb-4 flex flex-col md:flex-row justify-between items-start md:items-center space-y-4 md:space-y-0">
        <div className="flex flex-col md:flex-row space-y-2 md:space-y-0 md:space-x-2 w-full md:w-auto">
          <button
            className={`px-4 py-2 rounded ${
              withinBusinessHours 
                ? 'bg-green-500 text-white hover:bg-green-600' 
                : 'bg-gray-300 text-gray-700 cursor-not-allowed'
            } w-full md:w-auto`}
            onClick={handleAutoDialer}
            disabled={!withinBusinessHours || selectedLeads.length === 0}
          >
            Auto-Dial Selected ({selectedLeads.length})
          </button>
          
          <button
            className="px-4 py-2 rounded bg-red-500 text-white hover:bg-red-600 disabled:opacity-50 w-full md:w-auto"
            onClick={handleDeleteLeads}
            disabled={selectedLeads.length === 0}
          >
            Delete Selected
          </button>
        </div>
        
        <div className="flex flex-col md:flex-row space-y-2 md:space-y-0 md:space-x-2 w-full md:w-auto">
          <input
            type="text"
            placeholder="Search leads..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-4 py-2 border rounded w-full md:w-60"
          />
          
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 border rounded w-full md:w-40"
          >
            <option value="All">All Statuses</option>
            <option value="Not Called">Not Called</option>
            <option value="Calling">Calling</option>
            <option value="Completed">Completed</option>
            <option value="Interested">Interested</option>
            <option value="Declined">Declined</option>
            <option value="Appointment Set">Appointment Set</option>
          </select>
        </div>
      </div>
      
      <div className="text-sm text-gray-600 mb-2">
        {withinBusinessHours 
          ? '✅ Within business hours' 
          : `⚠️ Outside business hours (${businessHoursInfo.days || 'M-F'}, ${businessHoursInfo.start || '9:30 AM'}-${businessHoursInfo.end || '4:00 PM'} ${businessHoursInfo.timezone || 'MT'})`}
      </div>

      {/* Responsive table with horizontal scrolling for small screens */}
      <div className="overflow-x-auto bg-white rounded shadow">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 w-10">
                <input 
                  type="checkbox" 
                  onChange={toggleSelectAll}
                  checked={selectedLeads.length === filteredLeads.length && filteredLeads.length > 0}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('name')}
              >
                Business Name
                {sortField === 'name' && (
                  <span className="ml-1">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Phone</th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('industry')}
              >
                Industry
                {sortField === 'industry' && (
                  <span className="ml-1">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('employee_count')}
              >
                Employees
                {sortField === 'employee_count' && (
                  <span className="ml-1">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Mobile</th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('status')}
              >
                Status
                {sortField === 'status' && (
                  <span className="ml-1">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Qualification</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {currentLeads.map((lead) => (
              <tr key={lead.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 whitespace-nowrap">
                  <input 
                    type="checkbox" 
                    checked={selectedLeads.includes(lead.id)}
                    onChange={() => toggleLeadSelection(lead.id)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                </td>
                <td className="px-4 py-3 whitespace-nowrap font-medium text-gray-900">{lead.name}</td>
                <td className="px-4 py-3 whitespace-nowrap text-gray-600">{lead.phone}</td>
                <td className="px-4 py-3 whitespace-nowrap text-gray-600">{lead.industry || lead.category}</td>
                <td className="px-4 py-3 whitespace-nowrap text-gray-600">{lead.employee_count || 'Unknown'}</td>
                <td className="px-4 py-3 whitespace-nowrap text-gray-600">{lead.uses_mobile_devices || 'Unknown'}</td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${STATUS_COLORS[lead.status] || ''}`}>{lead.status}</span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${STATUS_COLORS[lead.qualification_status] || ''}`}>{lead.qualification_status}</span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex flex-wrap gap-1">
                    <button
                      className="bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600 disabled:opacity-50 text-xs"
                      disabled={loadingId === lead.id || lead.status === 'Calling'}
                      onClick={() => handleCall(lead)}
                      title={!withinBusinessHours ? "Outside business hours - use Manual Call" : ""}
                    >
                      Auto Call
                    </button>
                    <button
                      className="bg-orange-500 text-white px-3 py-1 rounded hover:bg-orange-600 disabled:opacity-50 text-xs"
                      disabled={loadingId === lead.id || lead.status === 'Calling'}
                      onClick={() => handleManualCall(lead)}
                    >
                      Manual
                    </button>
                    <div className="relative group">
                      <button
                        className="bg-gray-200 text-gray-700 px-3 py-1 rounded hover:bg-gray-300 disabled:opacity-50 text-xs"
                        disabled={loadingId === lead.id}
                      >
                        More ▾
                      </button>
                      <div className="absolute right-0 mt-1 hidden group-hover:block bg-white border rounded shadow-lg z-10 w-32">
                        <button
                          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                          onClick={() => openQualifyModal(lead)}
                        >
                          Qualify
                        </button>
                        <button
                          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                          onClick={() => openAppointmentModal(lead)}
                        >
                          Book
                        </button>
                        <button
                          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                          onClick={() => openFollowUpModal(lead)}
                        >
                          Follow-up
                        </button>
                        <button
                          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                          onClick={() => handleTranscript(lead)}
                        >
                          Transcript
                        </button>
                        <button
                          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                          onClick={() => openHistoryModal(lead)}
                        >
                          History
                        </button>
                        <button
                          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 text-red-600"
                          onClick={() => handleDeleteLead(lead.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            ))}

            {currentLeads.length === 0 && (
              <tr>
                <td colSpan="9" className="px-4 py-8 text-center text-gray-500">
                  {filteredLeads.length === 0 ? (
                    searchTerm || filterStatus !== 'All' ? (
                      <>
                        <p className="text-lg">No leads match your search criteria</p>
                        <p className="text-sm mt-1">Try adjusting your filters</p>
                      </>
                    ) : (
                      <>
                        <p className="text-lg">No leads found</p>
                        <p className="text-sm mt-1">Try adding new leads or using the lead scraper</p>
                      </>
                    )
                  ) : (
                    'Loading leads...'
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {filteredLeads.length > leadsPerPage && (
        <div className="mt-4 flex flex-col md:flex-row justify-between items-start md:items-center">
          <div className="flex items-center mb-2 md:mb-0">
            <span className="mr-2 text-sm text-gray-600">Leads per page:</span>
            <select 
              value={leadsPerPage} 
              onChange={(e) => {
                setLeadsPerPage(Number(e.target.value));
                setCurrentPage(1); // Reset to first page when changing items per page
              }}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
            
            <span className="ml-4 text-sm text-gray-600">
              Showing {indexOfFirstLead + 1}-{Math.min(indexOfLastLead, filteredLeads.length)} of {filteredLeads.length} leads
            </span>
          </div>
          
          <div className="pagination-container">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 border rounded hover:bg-gray-100 disabled:opacity-50"
            >
              &laquo;
            </button>
            
            {Array.from({ length: Math.ceil(filteredLeads.length / leadsPerPage) }, (_, i) => {
              // Only show a window of 5 pages centered around current page
              if (
                i === 0 || // First page
                i === Math.ceil(filteredLeads.length / leadsPerPage) - 1 || // Last page
                (i >= currentPage - 2 && i <= currentPage + 2) // Pages within window
              ) {
                return (
                  <button
                    key={i + 1}
                    onClick={() => paginate(i + 1)}
                    className={`px-3 py-1 border rounded ${
                      currentPage === i + 1 ? 'bg-indigo-600 text-white' : 'hover:bg-gray-100'
                    }`}
                  >
                    {i + 1}
                  </button>
                );
              }
              
              // Show ellipsis for breaks in sequence
              if (
                i === 1 && currentPage > 4 || // After first page
                i === Math.ceil(filteredLeads.length / leadsPerPage) - 2 && currentPage < Math.ceil(filteredLeads.length / leadsPerPage) - 3 // Before last page
              ) {
                return (
                  <span key={i} className="px-3 py-1">
                    ...
                  </span>
                );
              }
              
              return null;
            })}
            
            <button
              onClick={() => setCurrentPage(Math.min(Math.ceil(filteredLeads.length / leadsPerPage), currentPage + 1))}
              disabled={currentPage === Math.ceil(filteredLeads.length / leadsPerPage)}
              className="px-3 py-1 border rounded hover:bg-gray-100 disabled:opacity-50"
            >
              &raquo;
            </button>
          </div>
        </div>
      )}

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

      {/* Schedule Follow-up Modal */}
      {showFollowUpModal && selectedLead && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
          <div className="bg-white p-6 rounded shadow max-w-lg w-full relative">
            <button className="absolute top-2 right-2 text-xl" onClick={closeFollowUpModal}>&times;</button>
            <h2 className="text-lg font-bold mb-4">Schedule Follow-up: {selectedLead.name}</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Date & Time</label>
                <input 
                  type="datetime-local" 
                  className="w-full border p-2 rounded"
                  value={followUpData.scheduled_time}
                  onChange={(e) => setFollowUpData({...followUpData, scheduled_time: e.target.value})}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Priority (1-10)</label>
                <input 
                  type="range" 
                  min="1" 
                  max="10" 
                  className="w-full"
                  value={followUpData.priority}
                  onChange={(e) => setFollowUpData({...followUpData, priority: parseInt(e.target.value)})}
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Low (1)</span>
                  <span>Medium (5)</span>
                  <span>High (10)</span>
                </div>
                <div className="text-center font-bold mt-1">
                  {followUpData.priority}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Reason</label>
                <input 
                  type="text" 
                  className="w-full border p-2 rounded"
                  value={followUpData.reason}
                  onChange={(e) => setFollowUpData({...followUpData, reason: e.target.value})}
                  placeholder="Why are you following up?"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Notes</label>
                <textarea 
                  className="w-full border p-2 rounded"
                  value={followUpData.notes}
                  onChange={(e) => setFollowUpData({...followUpData, notes: e.target.value})}
                  rows={3}
                  placeholder="Additional details about the follow-up"
                />
              </div>
            </div>
            
            <div className="mt-4 flex justify-end space-x-3">
              <button 
                className="px-4 py-2 border rounded hover:bg-gray-100"
                onClick={closeFollowUpModal}
              >
                Cancel
              </button>
              <button 
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                onClick={saveFollowUp}
                disabled={loadingId === selectedLead.id}
              >
                {loadingId === selectedLead.id ? 'Saving...' : 'Schedule Follow-up'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Lead History Modal */}
      {showHistoryModal && selectedLead && (
        <LeadHistoryModal 
          lead={selectedLead} 
          open={showHistoryModal} 
          onClose={() => setShowHistoryModal(false)} 
        />
      )}
    </div>
  );
}

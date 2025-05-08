import React, { useEffect, useState } from 'react';
import { getLeads, scrapeLeads } from './api';
import LeadTable from './components/LeadTable';
import SettingsModal from './components/SettingsModal';
import AppointmentList from './components/AppointmentList';
import FollowUpList from './components/FollowUpList';
import AddLeadModal from './components/AddLeadModal';
import SteveDashboard from './components/SteveDashboard';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import AITrainingInterface from './components/AITrainingInterface';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5001/api';

function App() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [addLeadOpen, setAddLeadOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('leads');
  const [testMode, setTestMode] = useState(true);
  const [notification, setNotification] = useState({ show: false, message: '', type: '' });
  const [scrapeParams, setScrapeParams] = useState({
    location: 'Denver, CO',
    industry: 'Plumbing',
    limit: 30
  });

  const fetchLeads = async () => {
    setLoading(true);
    const data = await getLeads();
    setLeads(data);
    setLoading(false);
  };
  
  const fetchConfig = async () => {
    try {
      const response = await axios.get(`${API_BASE}/config`);
      setTestMode(response.data.TEST_MODE);
    } catch (error) {
      console.error("Error fetching config:", error);
    }
  };

  useEffect(() => {
    fetchLeads();
    fetchConfig();
  }, []);
  
  // Hide notification after a delay
  useEffect(() => {
    if (notification.show) {
      const timer = setTimeout(() => {
        setNotification({ ...notification, show: false });
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  const handleScrape = async () => {
    setScraping(true);
    
    try {
      const response = await axios.post(`${API_BASE}/scrape`, scrapeParams);
      console.log('Scraping response:', response.data);
      await fetchLeads();
      
      // Show success notification
      setNotification({
        show: true,
        type: 'success',
        message: `Successfully added ${response.data.count} new leads!`
      });
    } catch (error) {
      console.error("Error scraping leads:", error);
      setNotification({
        show: true,
        type: 'error',
        message: 'Error finding new leads. Please try again.'
      });
    } finally {
      setScraping(false);
    }
  };

  const handleScrapeParamChange = (e) => {
    const { name, value } = e.target;
    setScrapeParams(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Toast Notification */}
      {notification.show && (
        <div className="fixed top-4 right-4 z-50 max-w-md animate-fade-in-down">
          <div className={`px-6 py-4 rounded-lg shadow-lg ${
            notification.type === 'success' 
              ? 'bg-green-100 border-l-4 border-green-500 text-green-700' 
              : 'bg-red-100 border-l-4 border-red-500 text-red-700'
          }`}>
            <div className="flex items-center">
              {notification.type === 'success' ? (
                <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              )}
              <p>{notification.message}</p>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-between items-center mb-8">
        <div className="flex items-center">
          <h1 className="text-3xl font-bold">Seamless Mobile Services Appointment Booker</h1>
          {testMode && (
            <span className="ml-4 bg-yellow-100 text-yellow-800 text-xs font-medium px-3 py-1 rounded-full">
              Test Mode
            </span>
          )}
        </div>
        <div className="space-x-2">
          <button className="bg-gray-700 text-white px-4 py-2 rounded" onClick={() => setSettingsOpen(true)}>
            Settings
          </button>
        </div>
      </div>
      
      {/* Steve Dashboard */}
      <SteveDashboard />
      
      {/* Navigation Tabs */}
      <div className="flex border-b mb-6">
        <button 
          className={`px-4 py-2 font-medium ${activeTab === 'leads' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500'}`}
          onClick={() => setActiveTab('leads')}
        >
          Leads
        </button>
        <button 
          className={`px-4 py-2 font-medium ${activeTab === 'appointments' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500'}`}
          onClick={() => setActiveTab('appointments')}
        >
          Appointments
        </button>
        <button 
          className={`px-4 py-2 font-medium ${activeTab === 'followups' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500'}`}
          onClick={() => setActiveTab('followups')}
        >
          Follow-ups
        </button>
        <button 
          className={`px-4 py-2 font-medium ${activeTab === 'analytics' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500'}`}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics
        </button>
        <button 
          className={`px-4 py-2 font-medium ${activeTab === 'training' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500'}`}
          onClick={() => setActiveTab('training')}
        >
          AI Training
        </button>
      </div>
      
      {activeTab === 'leads' && (
        <>
          <div className="flex justify-between mb-4">
            <h2 className="text-lg font-semibold">Manage Leads</h2>
            <button 
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              onClick={() => setAddLeadOpen(true)}
            >
              Add Lead
            </button>
          </div>

          <div className="bg-white p-6 rounded shadow mb-6">
            <h2 className="text-lg font-semibold mb-4">Find New Business Leads</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">Location</label>
                <select
                  name="location"
                  value={scrapeParams.location}
                  onChange={handleScrapeParamChange}
                  className="w-full border p-2 rounded"
                  disabled={scraping}
                >
                  <option value="Denver, CO">Denver, CO</option>
                  <option value="Colorado Springs, CO">Colorado Springs, CO</option>
                  <option value="Boulder, CO">Boulder, CO</option>
                  <option value="Fort Collins, CO">Fort Collins, CO</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Industry</label>
                <select
                  name="industry"
                  value={scrapeParams.industry}
                  onChange={handleScrapeParamChange}
                  className="w-full border p-2 rounded"
                  disabled={scraping}
                >
                  <optgroup label="Field Service Businesses">
                    <option value="Plumbing">Plumbing Companies</option>
                    <option value="HVAC">HVAC & Heating Contractors</option>
                    <option value="Electrical">Electrical Contractors</option>
                    <option value="Construction">General Construction Firms</option>
                    <option value="Roofing">Roofing Companies</option>
                    <option value="Pest Control">Pest Control Companies</option>
                    <option value="Septic Services">Septic/Waste Removal Services</option>
                    <option value="Landscaping">Landscaping Companies</option>
                  </optgroup>
                  <optgroup label="Fleet & Logistics Operations">
                    <option value="Delivery">Delivery Companies</option>
                    <option value="Trucking">Trucking Companies</option>
                    <option value="Courier">Courier Services</option>
                    <option value="Towing">Towing Companies</option>
                    <option value="Field Inspection">Field Inspection Agencies</option>
                    <option value="Waste Management">Waste Management Contractors</option>
                  </optgroup>
                  <optgroup label="Labor/Jobsite-Heavy Businesses">
                    <option value="Excavation">Construction & Excavation</option>
                    <option value="Concrete">Concrete Companies</option>
                    <option value="Drilling">Drilling & Boring Contractors</option>
                    <option value="Utility">Utility Contractors</option>
                  </optgroup>
                  <optgroup label="Technical Field Services">
                    <option value="Telecom">Telecom Installation</option>
                    <option value="Security Systems">Security System Installers</option>
                    <option value="Solar">Solar Panel Installers</option>
                    <option value="Maintenance">Maintenance Companies</option>
                  </optgroup>
                  <optgroup label="Mobile Healthcare & Home Services">
                    <option value="Home Care">In-home Care Agencies</option>
                    <option value="Mobile Testing">Mobile Lab Testing</option>
                  </optgroup>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Number of Leads</label>
                <input
                  type="number"
                  name="limit"
                  value={scrapeParams.limit}
                  onChange={handleScrapeParamChange}
                  className="w-full border p-2 rounded"
                  min="1"
                  max="50"
                  disabled={scraping}
                />
              </div>
            </div>
            <button
              className={`px-4 py-2 rounded flex items-center justify-center w-full sm:w-auto
                ${scraping ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
              onClick={handleScrape}
              disabled={scraping}
            >
              {scraping ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span className="text-white">Searching for leads...</span>
                </>
              ) : (
                <span className="text-white">Find New Leads</span>
              )}
            </button>
            
            {scraping && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-100 rounded text-sm text-blue-800">
                <p className="font-medium">⚙️ Lead search in progress</p>
                <p className="mt-1">Searching for {scrapeParams.industry} businesses in {scrapeParams.location}. This may take up to 30 seconds.</p>
                <div className="mt-2 w-full bg-blue-200 rounded-full h-2.5">
                  <div className="bg-blue-600 h-2.5 rounded-full animate-pulse w-full"></div>
                </div>
              </div>
            )}
          </div>

          {loading ? (
            <div>Loading leads...</div>
          ) : (
            <LeadTable leads={leads} onStatusChange={fetchLeads} />
          )}
        </>
      )}
      
      {activeTab === 'appointments' && (
        <AppointmentList />
      )}

      {activeTab === 'followups' && (
        <FollowUpList />
      )}
      
      {activeTab === 'analytics' && (
        <AnalyticsDashboard />
      )}
      
      {activeTab === 'training' && (
        <AITrainingInterface />
      )}
      
      <SettingsModal 
        open={settingsOpen} 
        onClose={() => setSettingsOpen(false)} 
        onSave={(updatedConfig) => {
          if (updatedConfig) {
            setTestMode(updatedConfig.TEST_MODE);
          }
          fetchLeads();
        }} 
      />
      <AddLeadModal open={addLeadOpen} onClose={() => setAddLeadOpen(false)} onSave={fetchLeads} />
    </div>
  );
}

export default App;

import React, { useEffect, useState } from 'react';
import { getLeads, scrapeLeads } from './api';
import LeadTable from './components/LeadTable';
import SettingsModal from './components/SettingsModal';
import AppointmentList from './components/AppointmentList';
import FollowUpList from './components/FollowUpList';
import AddLeadModal from './components/AddLeadModal';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5003/api';

function App() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [addLeadOpen, setAddLeadOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('leads');
  const [testMode, setTestMode] = useState(true);
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

  const handleScrape = async () => {
    setScraping(true);
    
    try {
      await axios.post(`${API_BASE}/scrape`, scrapeParams);
      await fetchLeads();
    } catch (error) {
      console.error("Error scraping leads:", error);
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
                    <option value="Therapy">On-site Therapy Services</option>
                  </optgroup>
                  <optgroup label="Multi-location Small Chains">
                    <option value="Property Management">Property Management</option>
                    <option value="Car Dealership">Car Dealerships</option>
                    <option value="Franchise">Franchise Service Businesses</option>
                    <option value="Security">Private Security Companies</option>
                    <option value="Education">Schools & Tutoring Centers</option>
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
                  max="100"
                />
              </div>
            </div>
            <button
              className="bg-indigo-600 text-white px-6 py-2 rounded hover:bg-indigo-700 disabled:opacity-50"
              onClick={handleScrape}
              disabled={scraping}
            >
              {scraping ? 'Finding Leads...' : 'Find New Leads'}
            </button>
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

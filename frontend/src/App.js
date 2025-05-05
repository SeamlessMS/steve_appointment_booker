import React, { useEffect, useState } from 'react';
import { getLeads, scrapeLeads } from './api';
import LeadTable from './components/LeadTable';
import SettingsModal from './components/SettingsModal';
import AppointmentList from './components/AppointmentList';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5002/api';

function App() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('leads');
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

  useEffect(() => {
    fetchLeads();
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
        <h1 className="text-3xl font-bold">Mobile Solutions Appointment Booker</h1>
        <button className="bg-gray-700 text-white px-4 py-2 rounded" onClick={() => setSettingsOpen(true)}>
          Settings
        </button>
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
      </div>
      
      {activeTab === 'leads' && (
        <>
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
                  <option value="Plumbing">Plumbing</option>
                  <option value="Electrical">Electrical</option>
                  <option value="HVAC">HVAC</option>
                  <option value="Construction">Construction</option>
                  <option value="Landscaping">Landscaping</option>
                  <option value="Roofing">Roofing</option>
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
      
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} onSave={fetchLeads} />
    </div>
  );
}

export default App;

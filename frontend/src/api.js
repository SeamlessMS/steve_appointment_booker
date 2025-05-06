import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5003/api';

export const getLeads = () => axios.get(`${API_BASE}/leads`).then(r => r.data);
export const addLead = (lead) => axios.post(`${API_BASE}/leads`, lead);
export const updateLead = (id, data) => axios.patch(`${API_BASE}/leads/${id}`, data);
export const scrapeLeads = (limit = 30) => axios.post(`${API_BASE}/scrape`, { limit });
export const callLead = (lead_id, script) => axios.post(`${API_BASE}/call`, { lead_id, script });
export const manualCallLead = (lead_id, script) => axios.post(`${API_BASE}/call`, { lead_id, script, is_manual: true });
export const autoDialLeads = (lead_ids) => axios.post(`${API_BASE}/auto_dial`, { lead_ids });
export const checkBusinessHours = () => axios.get(`${API_BASE}/check_business_hours`).then(r => r.data);
export const getCallLogs = (lead_id) => axios.get(`${API_BASE}/call_logs/${lead_id}`).then(r => r.data);
export const addCallLog = (log) => axios.post(`${API_BASE}/call_logs`, log);
export const getLeadHistory = (lead_id) => axios.get(`${API_BASE}/lead_history/${lead_id}`).then(r => r.data);

// Follow-up API functions
export const getFollowUps = (filters = {}) => {
  // Convert filters to query params
  const params = new URLSearchParams();
  Object.keys(filters).forEach(key => {
    if (filters[key] !== undefined && filters[key] !== null) {
      params.append(key, filters[key]);
    }
  });
  
  return axios.get(`${API_BASE}/follow_ups${params.toString() ? '?' + params.toString() : ''}`).then(r => r.data);
};

export const addFollowUp = (followUp) => axios.post(`${API_BASE}/follow_ups`, followUp);

export const updateFollowUp = (id, data) => axios.patch(`${API_BASE}/follow_ups/${id}`, data);

export const runAutoFollowUp = (maxCalls = 10) => axios.post(`${API_BASE}/auto_follow_up`, { max_calls: maxCalls });

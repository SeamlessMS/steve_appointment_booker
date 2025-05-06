import React, { useState } from 'react';
import { addLead } from '../api';

export default function AddLeadModal({ open, onClose, onSave }) {
  const [leadData, setLeadData] = useState({
    name: '',
    phone: '',
    address: '',
    website: '',
    industry: 'Mobile Services',
    category: 'Mobile Services',
    city: 'Denver',
    state: 'CO',
    employee_count: 10,
    uses_mobile_devices: 'Yes'
  });
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState({ show: false, type: '', message: '' });

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name === 'industry') {
      setLeadData({ ...leadData, [name]: value, category: value });
    } else {
      setLeadData({ ...leadData, [name]: value });
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await addLead(leadData);
      setLoading(false);
      // Show success notification
      setNotification({
        show: true,
        type: 'success',
        message: 'Lead added successfully!'
      });
      // Hide notification after 3 seconds
      setTimeout(() => {
        setNotification({ show: false, type: '', message: '' });
        onSave();
        // Reset form
        setLeadData({
          name: '',
          phone: '',
          address: '',
          website: '',
          industry: 'Mobile Services',
          category: 'Mobile Services',
          city: 'Denver',
          state: 'CO',
          employee_count: 10,
          uses_mobile_devices: 'Yes'
        });
      }, 2000);
    } catch (error) {
      console.error("Error adding lead:", error);
      setLoading(false);
      // Show error notification
      setNotification({
        show: true,
        type: 'error',
        message: 'Error adding lead. Please try again.'
      });
      // Hide notification after 3 seconds
      setTimeout(() => {
        setNotification({ show: false, type: '', message: '' });
      }, 3000);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white p-6 rounded shadow max-w-lg w-full relative overflow-y-auto max-h-screen">
        <button className="absolute top-2 right-2 text-xl" onClick={onClose}>&times;</button>
        <h2 className="text-lg font-bold mb-4">Add New Lead</h2>
        
        {notification.show && (
          <div 
            className={`p-3 mb-4 rounded ${
              notification.type === 'success' 
                ? 'bg-green-100 text-green-800 border border-green-200' 
                : 'bg-red-100 text-red-800 border border-red-200'
            }`}
          >
            {notification.message}
          </div>
        )}
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Business Name*</label>
            <input 
              name="name" 
              value={leadData.name} 
              onChange={handleChange} 
              className="w-full border p-2 rounded" 
              required 
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Phone Number*</label>
            <input 
              name="phone" 
              value={leadData.phone} 
              onChange={handleChange} 
              className="w-full border p-2 rounded" 
              required 
              placeholder="Format: 1234567890"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Industry</label>
            <select 
              name="industry" 
              value={leadData.industry} 
              onChange={handleChange} 
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
              <option value="Mobile Services">Mobile Services</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Address</label>
            <input 
              name="address" 
              value={leadData.address} 
              onChange={handleChange} 
              className="w-full border p-2 rounded" 
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">City</label>
              <input 
                name="city" 
                value={leadData.city} 
                onChange={handleChange} 
                className="w-full border p-2 rounded" 
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">State</label>
              <input 
                name="state" 
                value={leadData.state} 
                onChange={handleChange} 
                className="w-full border p-2 rounded" 
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Website</label>
            <input 
              name="website" 
              value={leadData.website} 
              onChange={handleChange} 
              className="w-full border p-2 rounded" 
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Employee Count</label>
              <input 
                type="number" 
                name="employee_count" 
                value={leadData.employee_count} 
                onChange={handleChange} 
                className="w-full border p-2 rounded" 
                min="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Uses Mobile Devices</label>
              <select 
                name="uses_mobile_devices" 
                value={leadData.uses_mobile_devices} 
                onChange={handleChange} 
                className="w-full border p-2 rounded"
              >
                <option value="Yes">Yes</option>
                <option value="No">No</option>
                <option value="Unknown">Unknown</option>
              </select>
            </div>
          </div>
        </div>
        
        <div className="mt-6 flex justify-end space-x-3">
          <button 
            className="px-4 py-2 border rounded text-gray-600" 
            onClick={onClose}
          >
            Cancel
          </button>
          <button 
            className="bg-indigo-600 text-white px-6 py-2 rounded hover:bg-indigo-700 disabled:opacity-50" 
            onClick={handleSave} 
            disabled={loading || !leadData.name || !leadData.phone}
          >
            {loading ? 'Saving...' : 'Add Lead'}
          </button>
        </div>
      </div>
    </div>
  );
} 
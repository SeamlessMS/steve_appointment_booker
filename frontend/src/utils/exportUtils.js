/**
 * Utility functions for exporting data to various formats
 */

/**
 * Convert array of objects to CSV string
 * @param {Array} data - Array of objects to convert
 * @param {Array} headers - Array of header objects with title and key properties
 * @returns {string} CSV formatted string
 */
export const convertToCSV = (data, headers) => {
  if (!data || !data.length) return '';
  
  // Create header row
  const headerRow = headers.map(header => `"${header.title}"`).join(',');
  
  // Create data rows
  const rows = data.map(item => {
    return headers
      .map(header => {
        // Get the value, handle null/undefined
        const value = item[header.key] !== undefined && item[header.key] !== null 
          ? item[header.key] 
          : '';
        
        // Wrap in quotes and escape quotes within the value
        return `"${String(value).replace(/"/g, '""')}"`;
      })
      .join(',');
  });
  
  // Combine header and data rows
  return [headerRow, ...rows].join('\n');
};

/**
 * Export data as a CSV file
 * @param {Array} data - Array of objects to export
 * @param {Array} headers - Array of header objects with title and key properties
 * @param {string} filename - Name of the file to download
 */
export const exportToCSV = (data, headers, filename) => {
  const csv = convertToCSV(data, headers);
  downloadFile(csv, filename, 'text/csv');
};

/**
 * Export data as Excel file (actually CSV with .xlsx extension)
 * @param {Array} data - Array of objects to export
 * @param {Array} headers - Array of header objects with title and key properties
 * @param {string} filename - Name of the file to download
 */
export const exportToExcel = (data, headers, filename) => {
  const csv = convertToCSV(data, headers);
  downloadFile(csv, `${filename}.xlsx`, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
};

/**
 * Download a file with specified content
 * @param {string} content - The content of the file
 * @param {string} filename - The name of the file
 * @param {string} contentType - The MIME type of the file
 */
export const downloadFile = (content, filename, contentType) => {
  const blob = new Blob([content], { type: contentType });
  const url = URL.createObjectURL(blob);
  
  // Create download link
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  
  // Trigger download
  document.body.appendChild(a);
  a.click();
  
  // Clean up
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

/**
 * Format today's date as YYYY-MM-DD for filenames
 * @returns {string} Formatted date
 */
export const getFormattedDate = () => {
  const date = new Date();
  return date.toISOString().split('T')[0];
}; 
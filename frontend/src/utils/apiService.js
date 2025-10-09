// API service for parameter management using the new backend API
const API_BASE_URL = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

// Whitelist of allowed API endpoints to prevent SSRF
const ALLOWED_ENDPOINTS = [
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'
];

const validateUrl = (url) => {
  try {
    const urlObj = new URL(url);
    // Validate protocol and hostname
    if (urlObj.protocol !== 'https:') return false;
    if (urlObj.hostname !== 'i3if973sp5.execute-api.eu-west-1.amazonaws.com') return false;
    return ALLOWED_ENDPOINTS.some(endpoint => url.startsWith(endpoint));
  } catch {
    return false;
  }
};

const safeFetch = async (url, options = {}) => {
  if (!validateUrl(url)) {
    throw new Error('Invalid or unauthorized URL');
  }
  if (url.includes('..') || url.includes('%2e%2e')) {
    throw new Error('Path traversal detected');
  }
  
  try {
    const response = await fetch(url, { timeout: 10000, ...options });
    return response;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('Request timeout');
    if (error.name === 'TypeError') throw new Error('Network error');
    throw error;
  }
};

const handleResponse = async (response, operation) => {
  if (response.ok) {
    try {
      return await response.json();
    } catch {
      return {};
    }
  }
  
  const status = response.status;
  if (status === 404) throw new Error(`${operation}: Not found`);
  if (status === 401) throw new Error(`${operation}: Unauthorized`);
  if (status === 403) throw new Error(`${operation}: Forbidden`);
  if (status >= 500) throw new Error(`${operation}: Server error`);
  throw new Error(`${operation}: Failed (${status})`);
};

export class ApiService {
  // Get all parameters
  static async getAllParameters() {
    const response = await safeFetch(`${API_BASE_URL}/parameters`);
    return await handleResponse(response, 'Get parameters');
  }

  // Get parameter by ID
  static async getParameter(id) {
    const response = await safeFetch(`${API_BASE_URL}/parameters/${encodeURIComponent(id)}`);
    return await handleResponse(response, 'Get parameter');
  }

  // Get parameter by name
  static async getParameterByName(name) {
    const response = await safeFetch(`${API_BASE_URL}/parameters/name/${encodeURIComponent(name)}`);
    return await handleResponse(response, 'Get parameter by name');
  }

  // Create parameter
  static async createParameter(parameterData) {
    const response = await safeFetch(`${API_BASE_URL}/parameters`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parameterData)
    });
    return await handleResponse(response, 'Create parameter');
  }

  // Update parameter
  static async updateParameter(id, parameterData) {
    const response = await safeFetch(`${API_BASE_URL}/parameters/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parameterData)
    });
    return await handleResponse(response, 'Update parameter');
  }

  // Delete parameter
  static async deleteParameter(id) {
    const response = await safeFetch(`${API_BASE_URL}/parameters/${encodeURIComponent(id)}`, {
      method: 'DELETE'
    });
    await handleResponse(response, 'Delete parameter');
    return true;
  }
}
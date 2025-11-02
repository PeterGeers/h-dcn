// API service for parameter management using the new backend API
import { API_CONFIG } from '../config/api';

const API_BASE_URL = API_CONFIG.BASE_URL;

// Whitelist of allowed API endpoints to prevent SSRF
const ALLOWED_ENDPOINTS = [
  API_CONFIG.BASE_URL
];

interface ParameterData {
  [key: string]: any;
}

const validateUrl = (url: string): boolean => {
  try {
    const urlObj = new URL(url);
    // Validate protocol and hostname
    if (urlObj.protocol !== 'https:') return false;
    const allowedHostname = new URL(API_CONFIG.BASE_URL).hostname;
    if (urlObj.hostname !== allowedHostname) return false;
    return ALLOWED_ENDPOINTS.some(endpoint => url.startsWith(endpoint));
  } catch {
    return false;
  }
};

const safeFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  if (!validateUrl(url)) {
    throw new Error('Invalid or unauthorized URL');
  }
  if (url.includes('..') || url.includes('%2e%2e')) {
    throw new Error('Path traversal detected');
  }
  
  try {
    const response = await fetch(url, options);
    return response;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('Request timeout');
    if (error.name === 'TypeError') throw new Error('Network error');
    throw error;
  }
};

const handleResponse = async (response: Response, operation: string): Promise<any> => {
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
  static async getAllParameters(): Promise<any> {
    const response = await safeFetch(`${API_BASE_URL}/parameters`);
    return await handleResponse(response, 'Get parameters');
  }

  // Get parameter by ID
  static async getParameter(id: string): Promise<any> {
    const response = await safeFetch(`${API_BASE_URL}/parameters/${encodeURIComponent(id)}`);
    return await handleResponse(response, 'Get parameter');
  }

  // Get parameter by name
  static async getParameterByName(name: string): Promise<any> {
    const response = await safeFetch(`${API_BASE_URL}/parameters/name/${encodeURIComponent(name)}`);
    return await handleResponse(response, 'Get parameter by name');
  }

  // Create parameter
  static async createParameter(parameterData: ParameterData): Promise<any> {
    const response = await safeFetch(`${API_BASE_URL}/parameters`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parameterData)
    });
    return await handleResponse(response, 'Create parameter');
  }

  // Update parameter
  static async updateParameter(id: string, parameterData: ParameterData): Promise<any> {
    const response = await safeFetch(`${API_BASE_URL}/parameters/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parameterData)
    });
    return await handleResponse(response, 'Update parameter');
  }

  // Delete parameter
  static async deleteParameter(id: string): Promise<boolean> {
    const response = await safeFetch(`${API_BASE_URL}/parameters/${encodeURIComponent(id)}`, {
      method: 'DELETE'
    });
    await handleResponse(response, 'Delete parameter');
    return true;
  }
}
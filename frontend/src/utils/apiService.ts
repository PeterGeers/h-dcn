// API service for parameter management using the new backend API
// Note: This is a legacy utility service. New code should use the main ApiService from services/apiService.ts

import { API_CONFIG } from '../config/api';
import { ApiService as MainApiService } from '../services/apiService';

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

// Updated to use main ApiService for authenticated requests
const safeFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  if (!validateUrl(url)) {
    throw new Error('Invalid or unauthorized URL');
  }
  if (url.includes('..') || url.includes('%2e%2e')) {
    throw new Error('Path traversal detected');
  }
  
  // Check authentication using main ApiService
  if (!MainApiService.isAuthenticated()) {
    throw new Error('Authentication required');
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
  // Get all parameters - now uses main ApiService for authentication
  static async getAllParameters(): Promise<any> {
    const endpoint = '/parameters';
    const response = await MainApiService.get(endpoint);
    if (!response.success) {
      throw new Error(response.error || 'Failed to get parameters');
    }
    return response.data;
  }

  // Get parameter by ID - now uses main ApiService for authentication
  static async getParameter(id: string): Promise<any> {
    const endpoint = `/parameters/${encodeURIComponent(id)}`;
    const response = await MainApiService.get(endpoint);
    if (!response.success) {
      throw new Error(response.error || 'Failed to get parameter');
    }
    return response.data;
  }

  // Get parameter by name - now uses main ApiService for authentication
  static async getParameterByName(name: string): Promise<any> {
    const endpoint = `/parameters/name/${encodeURIComponent(name)}`;
    const response = await MainApiService.get(endpoint);
    if (!response.success) {
      throw new Error(response.error || 'Failed to get parameter by name');
    }
    return response.data;
  }

  // Create parameter - now uses main ApiService for authentication
  static async createParameter(parameterData: ParameterData): Promise<any> {
    const endpoint = '/parameters';
    const response = await MainApiService.post(endpoint, parameterData);
    if (!response.success) {
      throw new Error(response.error || 'Failed to create parameter');
    }
    return response.data;
  }

  // Update parameter - now uses main ApiService for authentication
  static async updateParameter(id: string, parameterData: ParameterData): Promise<any> {
    const endpoint = `/parameters/${encodeURIComponent(id)}`;
    const response = await MainApiService.put(endpoint, parameterData);
    if (!response.success) {
      throw new Error(response.error || 'Failed to update parameter');
    }
    return response.data;
  }

  // Delete parameter - now uses main ApiService for authentication
  static async deleteParameter(id: string): Promise<boolean> {
    const endpoint = `/parameters/${encodeURIComponent(id)}`;
    const response = await MainApiService.delete(endpoint);
    if (!response.success) {
      throw new Error(response.error || 'Failed to delete parameter');
    }
    return true;
  }
}
import axios, { AxiosResponse } from 'axios';
import { ApiService } from '../../../services/apiService';

interface CartData {
  items?: any[];
  [key: string]: any;
}

interface OrderData {
  [key: string]: any;
}

const validateApiUrl = (url: string): boolean => {
  if (!url) return false;
  try {
    const parsedUrl = new URL(url);
    return parsedUrl.protocol === 'https:' &&
      (parsedUrl.hostname.endsWith('.amazonaws.com') ||
        parsedUrl.hostname === 'api.hdcn-webshop.com');
  } catch {
    return false;
  }
};

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'https://api.hdcn-webshop.com';

if (!validateApiUrl(API_BASE_URL)) {
  console.warn('Invalid API base URL, using fallback');
}

// Helper function to create axios config with auth headers - now uses main ApiService
const createAuthConfig = async (method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET') => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  
  return { 
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    }
  };
};

export const productService = {
  scanProducts: async (): Promise<AxiosResponse<any>> => {
    const config = await createAuthConfig('GET');
    return axios.get('/scan-product/', config);
  },
};

export const cartService = {
  createCart: async (data: CartData): Promise<AxiosResponse<any>> => {
    const config = await createAuthConfig('POST');
    return axios.post('/carts', data, config);
  },
  getCart: async (cartId: string): Promise<AxiosResponse<any>> => {
    if (!cartId || typeof cartId !== 'string') {
      throw new Error('Invalid cart ID');
    }
    const sanitizedCartId = cartId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedCartId || sanitizedCartId !== cartId) {
      throw new Error('Cart ID contains invalid characters');
    }
    const config = await createAuthConfig('GET');
    return axios.get(`/carts/${sanitizedCartId}`, config);
  },
  updateCartItems: async (cartId: string, cartData: CartData): Promise<AxiosResponse<any>> => {
    if (!cartId || typeof cartId !== 'string') {
      throw new Error('Invalid cart ID');
    }
    const sanitizedCartId = cartId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedCartId || sanitizedCartId !== cartId) {
      throw new Error('Cart ID contains invalid characters');
    }
    const config = await createAuthConfig('PUT');
    return axios.put(`/carts/${sanitizedCartId}/items`, cartData, config);
  },
  clearCart: async (cartId: string): Promise<AxiosResponse<any>> => {
    if (!cartId || typeof cartId !== 'string') {
      throw new Error('Invalid cart ID');
    }
    const sanitizedCartId = cartId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedCartId || sanitizedCartId !== cartId) {
      throw new Error('Cart ID contains invalid characters');
    }
    const config = await createAuthConfig('DELETE');
    return axios.delete(`/carts/${sanitizedCartId}`, config);
  },
};

export const orderService = {
  createOrder: async (data: OrderData): Promise<AxiosResponse<any>> => {
    const config = await createAuthConfig('POST');
    return axios.post('/orders', data, config);
  },
};

export const parameterService = {
  getParameter: async (name: string): Promise<AxiosResponse<any>> => {
    if (!name || typeof name !== 'string') {
      throw new Error('Invalid parameter name');
    }
    
    try {
      // Load from parameters.json file instead of API
      const version = process.env.REACT_APP_CACHE_VERSION || '1.0';
      const response = await fetch(`/parameters.json?v=${version}`);
      
      if (!response.ok) {
        throw new Error(`Failed to load parameters.json: ${response.status}`);
      }
      
      const jsonData = await response.json();
      
      // Find the parameter by name
      const parameterValue = jsonData[name];
      if (parameterValue === undefined) {
        throw new Error(`Parameter '${name}' not found`);
      }
      
      // Return in the same format as the old API
      return {
        data: {
          value: Array.isArray(parameterValue) ? JSON.stringify(parameterValue) : parameterValue,
          name: name
        }
      } as AxiosResponse<any>;
      
    } catch (error) {
      console.error(`Error loading parameter '${name}':`, error);
      throw error;
    }
  },
};

export const memberService = {
  getMember: async (memberId: string): Promise<AxiosResponse<any>> => {
    if (!memberId || typeof memberId !== 'string') {
      throw new Error('Invalid member ID');
    }
    const sanitizedMemberId = memberId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedMemberId || sanitizedMemberId !== memberId) {
      throw new Error('Member ID contains invalid characters');
    }
    const config = await createAuthConfig('GET');
    return axios.get(`/members/${sanitizedMemberId}`, config);
  },
};
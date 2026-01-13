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

export const productService = {
  scanProducts: async () => {
    if (!ApiService.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    return ApiService.get('/scan-product/');
  },
};

export const cartService = {
  createCart: async (data: CartData) => {
    if (!ApiService.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    return ApiService.post('/carts', data);
  },
  getCart: async (cartId: string) => {
    if (!cartId || typeof cartId !== 'string') {
      throw new Error('Invalid cart ID');
    }
    const sanitizedCartId = cartId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedCartId || sanitizedCartId !== cartId) {
      throw new Error('Cart ID contains invalid characters');
    }
    if (!ApiService.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    return ApiService.get(`/carts/${sanitizedCartId}`);
  },
  updateCartItems: async (cartId: string, cartData: CartData) => {
    if (!cartId || typeof cartId !== 'string') {
      throw new Error('Invalid cart ID');
    }
    const sanitizedCartId = cartId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedCartId || sanitizedCartId !== cartId) {
      throw new Error('Cart ID contains invalid characters');
    }
    if (!ApiService.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    return ApiService.put(`/carts/${sanitizedCartId}/items`, cartData);
  },
  clearCart: async (cartId: string) => {
    if (!cartId || typeof cartId !== 'string') {
      throw new Error('Invalid cart ID');
    }
    const sanitizedCartId = cartId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedCartId || sanitizedCartId !== cartId) {
      throw new Error('Cart ID contains invalid characters');
    }
    if (!ApiService.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    return ApiService.delete(`/carts/${sanitizedCartId}`);
  },
};

export const orderService = {
  createOrder: async (data: OrderData) => {
    if (!ApiService.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    return ApiService.post('/orders', data);
  },
};

export const memberService = {
  getMember: async (memberId: string) => {
    if (!memberId || typeof memberId !== 'string') {
      throw new Error('Invalid member ID');
    }
    const sanitizedMemberId = memberId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedMemberId || sanitizedMemberId !== memberId) {
      throw new Error('Member ID contains invalid characters');
    }
    if (!ApiService.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    return ApiService.get(`/members/${sanitizedMemberId}`);
  },
};

export const parameterService = {
  getParameter: async (name: string) => {
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
      
      // Return in the same format as the old API but adapted for ApiService
      return {
        success: true,
        data: {
          value: Array.isArray(parameterValue) ? JSON.stringify(parameterValue) : parameterValue,
          name: name
        }
      };
      
    } catch (error) {
      console.error(`Error loading parameter '${name}':`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },
};
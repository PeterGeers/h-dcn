import axios, { AxiosResponse } from 'axios';

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

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

export const productService = {
  scanProducts: (): Promise<AxiosResponse<any>> => api.get('/scan-product/'),
};

export const cartService = {
  createCart: (data: CartData): Promise<AxiosResponse<any>> => api.post('/carts', data),
  getCart: (cartId: string): Promise<AxiosResponse<any>> => {
    if (!cartId || typeof cartId !== 'string') {
      throw new Error('Invalid cart ID');
    }
    const sanitizedCartId = cartId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedCartId || sanitizedCartId !== cartId) {
      throw new Error('Cart ID contains invalid characters');
    }
    return api.get(`/carts/${sanitizedCartId}`);
  },
  updateCartItems: (cartId: string, cartData: CartData): Promise<AxiosResponse<any>> => {
    if (!cartId || typeof cartId !== 'string') {
      throw new Error('Invalid cart ID');
    }
    const sanitizedCartId = cartId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedCartId || sanitizedCartId !== cartId) {
      throw new Error('Cart ID contains invalid characters');
    }
    return api.put(`/carts/${sanitizedCartId}/items`, cartData);
  },
  clearCart: (cartId: string): Promise<AxiosResponse<any>> => {
    if (!cartId || typeof cartId !== 'string') {
      throw new Error('Invalid cart ID');
    }
    const sanitizedCartId = cartId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedCartId || sanitizedCartId !== cartId) {
      throw new Error('Cart ID contains invalid characters');
    }
    return api.delete(`/carts/${sanitizedCartId}`);
  },
};

export const orderService = {
  createOrder: (data: OrderData): Promise<AxiosResponse<any>> => api.post('/orders', data),
};

export const parameterService = {
  getParameter: (name: string): Promise<AxiosResponse<any>> => {
    if (!name || typeof name !== 'string') {
      throw new Error('Invalid parameter name');
    }
    const sanitizedName = name.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedName || sanitizedName !== name) {
      throw new Error('Parameter name contains invalid characters');
    }
    return api.get(`/parameters/name/${sanitizedName}`);
  },
};

export const memberService = {
  getMember: (memberId: string): Promise<AxiosResponse<any>> => {
    if (!memberId || typeof memberId !== 'string') {
      throw new Error('Invalid member ID');
    }
    const sanitizedMemberId = memberId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedMemberId || sanitizedMemberId !== memberId) {
      throw new Error('Member ID contains invalid characters');
    }
    return api.get(`/members/${sanitizedMemberId}`);
  },
};
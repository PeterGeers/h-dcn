import axios from 'axios';

const validateApiUrl = (url) => {
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
  scanProducts: () => api.get('/scan-product/'),
};

export const cartService = {
  createCart: (data) => api.post('/carts', data),
  getCart: (cartId) => {
    if (!cartId || typeof cartId !== 'string') {
      throw new Error('Invalid cart ID');
    }
    const sanitizedCartId = cartId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedCartId || sanitizedCartId !== cartId) {
      throw new Error('Cart ID contains invalid characters');
    }
    return api.get(`/carts/${sanitizedCartId}`);
  },
  updateCartItems: (cartId, cartData) => {
    if (!cartId || typeof cartId !== 'string') {
      throw new Error('Invalid cart ID');
    }
    const sanitizedCartId = cartId.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedCartId || sanitizedCartId !== cartId) {
      throw new Error('Cart ID contains invalid characters');
    }
    return api.put(`/carts/${sanitizedCartId}/items`, cartData);
  },
  clearCart: (cartId) => {
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
  createOrder: (data) => api.post('/orders', data),
};

export const parameterService = {
  getParameter: (name) => {
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
  getMember: (memberId) => {
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
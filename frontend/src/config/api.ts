// Centralized API Configuration
export const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod',
  
  // API Endpoints
  ENDPOINTS: {
    MEMBERS: '/members',
    EVENTS: '/events', 
    PRODUCTS: '/products',
    MEMBERSHIPS: '/memberships',
    PARAMETERS: '/parameters',
    PAYMENTS: '/payments',
    CARTS: '/carts',
    ORDERS: '/orders'
  }
};

// Helper function to build full API URLs
export const buildApiUrl = (endpoint: string, id?: string): string => {
  const baseUrl = `${API_CONFIG.BASE_URL}${endpoint}`;
  return id ? `${baseUrl}/${id}` : baseUrl;
};

// Common API endpoints
export const API_URLS = {
  base: API_CONFIG.BASE_URL,
  members: () => buildApiUrl(API_CONFIG.ENDPOINTS.MEMBERS),
  member: (id: string) => buildApiUrl(API_CONFIG.ENDPOINTS.MEMBERS, id),
  events: () => buildApiUrl(API_CONFIG.ENDPOINTS.EVENTS),
  event: (id: string) => buildApiUrl(API_CONFIG.ENDPOINTS.EVENTS, id),
  products: () => buildApiUrl(API_CONFIG.ENDPOINTS.PRODUCTS),
  product: (id: string) => buildApiUrl(API_CONFIG.ENDPOINTS.PRODUCTS, id),
  memberships: () => buildApiUrl(API_CONFIG.ENDPOINTS.MEMBERSHIPS),
  membership: (id: string) => buildApiUrl(API_CONFIG.ENDPOINTS.MEMBERSHIPS, id),
  parameters: () => buildApiUrl(API_CONFIG.ENDPOINTS.PARAMETERS),
  payments: () => buildApiUrl(API_CONFIG.ENDPOINTS.PAYMENTS),
  carts: () => buildApiUrl(API_CONFIG.ENDPOINTS.CARTS),
  orders: () => buildApiUrl(API_CONFIG.ENDPOINTS.ORDERS)
};
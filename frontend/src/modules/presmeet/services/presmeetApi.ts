/**
 * PresMeet v3 API Client
 *
 * Uses Axios with an auth interceptor for all PresMeet endpoints.
 * Handles 409 (version conflict) and 403 (authorization) errors
 * with structured error types.
 *
 * Endpoints:
 * - GET  /presmeet/orders?event_id=X        → get/create order
 * - PUT  /presmeet/orders/{id}              → save draft
 * - POST /presmeet/orders/{id}/submit       → validate + submit
 * - POST /presmeet/orders/{id}/pay          → initiate Mollie payment
 * - GET  /presmeet/reports/{type}?event_id=X → reports
 * - GET  /events?event_type=presmeet        → get events
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { getAuthHeaders } from '../../../utils/authHeaders';
import { ApiService, ApiResponse } from '../../../services/apiService';
import {
  Order,
  Event,
  Product,
  SaveOrderRequest,
  PaymentInitiationResponse,
  ReportParams,
  ReportResponse,
  VersionConflictError,
  AuthorizationError,
  PresMeetApiError,
} from '../types/presmeet.types';
import {
  PresMeetConfig,
  PresMeetBooking,
  BookingFormData,
  ValidationResult,
  CartItem,
  PaymentSession,
  ManualPayment,
  ReportMetadata as LegacyReportMetadata,
  ReportType as LegacyReportType,
  ReportData,
  ClubRegistry,
  AssignClubResponse,
} from '../types/presmeet';

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

// --- Error Handling ---

/**
 * Check if an error is a version conflict (409).
 */
export function isVersionConflict(error: unknown): error is VersionConflictError {
  return (
    typeof error === 'object' &&
    error !== null &&
    (error as any).type === 'VERSION_CONFLICT'
  );
}

/**
 * Check if an error is an authorization error (403).
 */
export function isAuthorizationError(error: unknown): error is AuthorizationError {
  return (
    typeof error === 'object' &&
    error !== null &&
    (error as any).type === 'AUTHORIZATION_ERROR'
  );
}

/**
 * Parse Axios errors into structured PresMeetApiError types.
 */
function parseApiError(error: AxiosError<any>): PresMeetApiError | AxiosError {
  const status = error.response?.status;
  const data = error.response?.data;

  if (status === 409) {
    return {
      type: 'VERSION_CONFLICT',
      message: data?.message || 'Order has been modified by another user. Please refresh and try again.',
      current_version: data?.current_version ?? 0,
    } as VersionConflictError;
  }

  if (status === 403) {
    return {
      type: 'AUTHORIZATION_ERROR',
      message: data?.message || 'You do not have permission to perform this action.',
      status: 403,
    } as AuthorizationError;
  }

  return error;
}

// --- Axios Client ---

/**
 * Create an Axios instance with auth interceptor and structured error handling.
 */
const createPresMeetClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: BASE_URL,
    headers: { 'Content-Type': 'application/json' },
  });

  // Attach auth headers to every request
  client.interceptors.request.use(async (config) => {
    const authHeaders = await getAuthHeaders();
    Object.entries(authHeaders).forEach(([key, value]) => {
      config.headers.set(key, value);
    });
    return config;
  });

  // Transform 409 and 403 into structured errors; handle 401 session expiry
  client.interceptors.response.use(
    (response) => response,
    (error: AxiosError<any>) => {
      if (error.response?.status === 401) {
        window.location.href = '/login';
        return Promise.reject(error);
      }

      const parsed = parseApiError(error);
      return Promise.reject(parsed);
    }
  );

  return client;
};

const presmeetClient = createPresMeetClient();

// --- API Methods ---

/**
 * Get or create a PresMeet order for the user's club and specified event.
 * If no order exists, the backend creates a new draft order.
 */
export async function getOrder(eventId: string): Promise<Order> {
  const response = await presmeetClient.get<Order>('/presmeet/orders', {
    params: { event_id: eventId },
  });
  return response.data;
}

/**
 * Save draft order (PUT). Sends items and current version for optimistic locking.
 * May throw VersionConflictError (409) if version has changed.
 */
export async function saveOrder(
  orderId: string,
  data: SaveOrderRequest
): Promise<Order> {
  const response = await presmeetClient.put<Order>(
    `/presmeet/orders/${encodeURIComponent(orderId)}`,
    data
  );
  return response.data;
}

/**
 * Submit order for validation. Transitions status from draft to submitted.
 * Returns validation errors if submission fails.
 */
export async function submitOrder(orderId: string): Promise<Order> {
  const response = await presmeetClient.post<Order>(
    `/presmeet/orders/${encodeURIComponent(orderId)}/submit`
  );
  return response.data;
}

/**
 * Initiate a Mollie payment for the outstanding balance on an order.
 * Returns a checkout_url to redirect the user to Mollie's payment page.
 */
export async function pay(orderId: string): Promise<PaymentInitiationResponse> {
  const response = await presmeetClient.post<PaymentInitiationResponse>(
    `/presmeet/orders/${encodeURIComponent(orderId)}/pay`
  );
  return response.data;
}

/**
 * Get a PresMeet event by event_type filter.
 * Uses the existing /events endpoint.
 */
export async function getEvent(eventType: string = 'presmeet'): Promise<Event[]> {
  const response = await presmeetClient.get<Event[]>('/events', {
    params: { event_type: eventType },
  });
  return response.data;
}

/**
 * Get products for a given channel (e.g., 'presmeet').
 * Optionally filter by product_ids from the event definition.
 */
export async function getProducts(
  channel: string = 'presmeet',
  productIds?: string[]
): Promise<Product[]> {
  const response = await presmeetClient.get<Product[]>('/products', {
    params: { channel },
  });
  if (productIds && productIds.length > 0) {
    return response.data.filter((p) => productIds.includes(p.product_id));
  }
  return response.data;
}

/**
 * Get report data for a specific event and report type.
 * Supports filtering by order status and payment status.
 */
export async function getReport(params: ReportParams): Promise<ReportResponse> {
  const { type, event_id, status, payment_status, format } = params;
  const response = await presmeetClient.get<ReportResponse>(
    `/presmeet/reports/${encodeURIComponent(type)}`,
    {
      params: {
        event_id,
        ...(status && { status }),
        ...(payment_status && { payment_status }),
        ...(format && { format }),
      },
    }
  );
  return response.data;
}

/**
 * Manage delegates on an order (add or remove secondary delegate).
 * - action "add": requires email of existing portal user with PresMeet access
 * - action "remove": removes the current secondary delegate
 *
 * Possible errors: 404 (user not found), 403 (no PresMeet access), 400 (already assigned)
 */
export async function manageDelegates(
  orderId: string,
  data: { action: 'add'; email: string } | { action: 'remove' }
): Promise<Order> {
  const response = await presmeetClient.post<Order>(
    `/presmeet/orders/${encodeURIComponent(orderId)}/delegates`,
    data
  );
  return response.data;
}

// --- v3 convenience export ---

export const presmeetApi = {
  getOrder,
  saveOrder,
  submitOrder,
  pay,
  getEvent,
  getProducts,
  getReport,
  manageDelegates,
  isVersionConflict,
  isAuthorizationError,
};

// --- Legacy presmeetService (backward compatibility for existing components) ---

export const presmeetService = {
  getConfig: (): Promise<ApiResponse<PresMeetConfig>> => {
    return ApiService.get<PresMeetConfig>('/presmeet/config');
  },

  getBooking: (clubId?: string): Promise<ApiResponse<PresMeetBooking>> => {
    const endpoint = clubId
      ? `/presmeet/booking?club_id=${encodeURIComponent(clubId)}`
      : '/presmeet/booking';
    return ApiService.get<PresMeetBooking>(endpoint);
  },

  saveBooking: (data: BookingFormData): Promise<ApiResponse<void>> => {
    return ApiService.put<void>('/presmeet/booking', data);
  },

  submitBooking: (): Promise<ApiResponse<void>> => {
    return ApiService.post<void>('/presmeet/booking/submit');
  },

  validateBooking: (items: CartItem[]): Promise<ApiResponse<ValidationResult>> => {
    return ApiService.post<ValidationResult>('/presmeet/booking/validate', { items });
  },

  createPayment: (orderId: string): Promise<ApiResponse<PaymentSession>> => {
    return ApiService.post<PaymentSession>('/presmeet/payment', { order_id: orderId });
  },

  generateReport: (): Promise<ApiResponse<LegacyReportMetadata>> => {
    return ApiService.post<LegacyReportMetadata>('/presmeet/admin/report/generate');
  },

  getReport: (type: LegacyReportType = 'overview'): Promise<ApiResponse<ReportData>> => {
    return ApiService.get<ReportData>(`/presmeet/admin/report?type=${encodeURIComponent(type)}`);
  },

  getReportCsv: async (type: 'export_submitted' | 'export_all'): Promise<ApiResponse<string>> => {
    return ApiService.request<string>(`/presmeet/admin/report?type=${encodeURIComponent(type)}`, {
      method: 'GET',
      headers: { 'Accept': 'text/csv' },
    });
  },

  lockOrders: (orderIds?: string[]): Promise<ApiResponse<void>> => {
    return ApiService.post<void>('/presmeet/admin/lock', { order_ids: orderIds });
  },

  unlockOrder: (orderId: string): Promise<ApiResponse<void>> => {
    return ApiService.post<void>(`/presmeet/admin/unlock/${encodeURIComponent(orderId)}`);
  },

  recordPayment: (data: ManualPayment): Promise<ApiResponse<void>> => {
    return ApiService.post<void>('/presmeet/admin/payment', data);
  },

  getClubRegistry: (): Promise<ApiResponse<ClubRegistry>> => {
    return ApiService.get<ClubRegistry>('/presmeet/clubs');
  },

  assignClub: (clubId: string): Promise<ApiResponse<AssignClubResponse>> => {
    return ApiService.post<AssignClubResponse>('/presmeet/clubs/assign', { club_id: clubId });
  },

  reassignClub: (clubId: string, memberEmail: string): Promise<ApiResponse<AssignClubResponse>> => {
    return ApiService.post<AssignClubResponse>('/presmeet/clubs/assign', {
      club_id: clubId,
      member_email: memberEmail,
    });
  },

  uploadClubLogo: (
    imageData: string,
    clubId: string,
    contentType: string
  ): Promise<ApiResponse<{ logo_url: string }>> => {
    return ApiService.post<{ logo_url: string }>('/presmeet/logo', {
      image_data: imageData,
      club_id: clubId,
      content_type: contentType,
    });
  },
};

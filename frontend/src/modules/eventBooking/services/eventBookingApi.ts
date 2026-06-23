/**
 * Event Booking API Client (Unified Booking Endpoints)
 *
 * Uses Axios with an auth interceptor for all booking endpoints.
 * Handles 409 (version conflict) and 403 (authorization) errors
 * with structured error types.
 *
 * Unified Endpoints:
 * - GET  /booking?source_id={event_id|webshop}  → get/create order
 * - PUT  /orders/{id}/items                     → save draft (update items)
 * - POST /booking/{id}/submit                   → validate + submit
 * - POST /booking/{id}/pay                      → initiate Mollie payment
 * - POST /booking/{id}/delegates                → manage delegates
 * - POST /admin/booking/lock?source_id={id}     → lock orders
 * - GET  /admin/reports?source_id={id}          → reports
 * - GET  /events?event_type=X                   → get events
 * - GET  /products                              → get products
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { getAuthHeaders } from '../../../utils/authHeaders';
import { toPrice } from '../../../utils/formatPrice';
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
  EventBookingApiError,
} from '../types/eventBooking.types';

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
 * Parse Axios errors into structured EventBookingApiError types.
 */
function parseApiError(error: AxiosError<any>): EventBookingApiError | AxiosError {
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
      message: data?.message || data?.error || 'You do not have permission to perform this action.',
      status: 403,
    } as AuthorizationError;
  }

  return error;
}

// --- Axios Client ---

/**
 * Create an Axios instance with auth interceptor and structured error handling.
 */
const createEventBookingClient = (): AxiosInstance => {
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

const eventBookingClient = createEventBookingClient();

// --- API Methods ---

/**
 * Get or create an order for the given source.
 * Uses the unified /booking endpoint with source_id parameter.
 *
 * @param sourceId - event UUID or "webshop"
 */
export async function getOrder(sourceId: string): Promise<Order> {
  const response = await eventBookingClient.get<Order>('/booking', {
    params: { source_id: sourceId },
  });
  return response.data;
}

/**
 * Save draft order items (PUT). Sends items and current version for optimistic locking.
 * Uses the unified /orders/{id}/items endpoint.
 * May throw VersionConflictError (409) if version has changed.
 */
export async function saveOrder(
  orderId: string,
  data: SaveOrderRequest
): Promise<Order> {
  const response = await eventBookingClient.put<Order>(
    `/orders/${encodeURIComponent(orderId)}/items`,
    data
  );
  return response.data;
}

/**
 * Submit order for validation. Transitions status from draft to submitted.
 * Returns validation errors if submission fails.
 */
export async function submitOrder(orderId: string): Promise<Order> {
  const response = await eventBookingClient.post<Order>(
    `/booking/${encodeURIComponent(orderId)}/submit`
  );
  return response.data;
}

/**
 * Initiate a Mollie payment for the outstanding balance on an order.
 * Returns a checkout_url to redirect the user to Mollie's payment page.
 */
export async function pay(orderId: string): Promise<PaymentInitiationResponse> {
  const response = await eventBookingClient.post<PaymentInitiationResponse>(
    `/booking/${encodeURIComponent(orderId)}/pay`
  );
  return response.data;
}

/**
 * Get events, optionally filtered by event_type.
 * Uses the existing /events endpoint.
 */
export async function getEvent(eventType?: string): Promise<Event[]> {
  const params: Record<string, string> = {};
  if (eventType) {
    params.event_type = eventType;
  }
  const response = await eventBookingClient.get<Event[]>('/events', { params });
  return response.data;
}

/**
 * Get products by their IDs from the event's product_ids list.
 * Fetches all products and filters by the event's product_ids.
 *
 * @param sourceId - the event_id (source_id) for context (unused in API call but kept for interface)
 * @param productIds - array of product_ids from the event record to filter by
 */
export async function getProducts(
  sourceId: string,
  productIds?: string[]
): Promise<Product[]> {
  const response = await eventBookingClient.get<Product[]>('/scan-product/');
  let products = response.data;
  if (productIds && productIds.length > 0) {
    products = products.filter((p) => productIds.includes(p.product_id));
  }
  // Normalize: ensure order_item_fields is always an array, price is always a number
  return products.map((p) => ({
    ...p,
    order_item_fields: p.order_item_fields || [],
    price: toPrice(p.price),
    name: p.name || p.product_id,
  }));
}

/**
 * Get report data for a specific source and report type.
 * Supports filtering by order status and payment status.
 */
export async function getReport(params: ReportParams): Promise<ReportResponse> {
  const { type, event_id, status, payment_status, format } = params;
  const response = await eventBookingClient.get<ReportResponse>(
    `/admin/reports/${encodeURIComponent(type)}`,
    {
      params: {
        source_id: event_id,
        ...(status && { status }),
        ...(payment_status && { payment_status }),
        ...(format && { format }),
      },
    }
  );
  return response.data;
}

/**
 * Resend the delegate invitation email for an order with a pending invitation.
 * Uses POST /booking/{id}/invite-email.
 */
export async function resendDelegateInvitation(
  orderId: string,
  locale?: string
): Promise<{ message: string; recipient: string }> {
  const response = await eventBookingClient.post<{ message: string; recipient: string }>(
    `/booking/${encodeURIComponent(orderId)}/invite-email`,
    locale ? { locale } : {}
  );
  return response.data;
}

/**
 * Manage delegates on an order (invite, revoke, or legacy add/remove).
 * Uses the unified /booking/{id}/delegates endpoint.
 * - action "invite": invite secondary delegate by email (stores pending_secondary_email)
 * - action "revoke": revoke pending invitation or remove linked secondary (draft only)
 * - action "add": (legacy) add secondary delegate by member_id/email
 * - action "remove": (legacy) remove current secondary delegate
 *
 * Possible errors: 404 (user not found), 403 (no event access), 400 (validation),
 *                  409 (version conflict)
 */
export async function manageDelegates(
  orderId: string,
  data:
    | { action: 'invite'; email: string }
    | { action: 'revoke' }
    | { action: 'add'; email: string }
    | { action: 'remove' }
): Promise<Order> {
  const response = await eventBookingClient.post<Order>(
    `/booking/${encodeURIComponent(orderId)}/delegates`,
    data
  );
  return response.data;
}

// --- v3 convenience export ---

export const eventBookingApi = {
  getOrder,
  saveOrder,
  submitOrder,
  pay,
  getEvent,
  getProducts,
  getReport,
  manageDelegates,
  resendDelegateInvitation,
  isVersionConflict,
  isAuthorizationError,
};

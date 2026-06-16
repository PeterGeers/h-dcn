/**
 * Admin API client for the Webshop Management module.
 *
 * Uses Axios with an interceptor that attaches Amplify auth headers
 * (access token, user email, enhanced groups) to every request.
 */

import axios, { AxiosInstance } from 'axios';
import { getAuthHeaders } from '../../../utils/authHeaders';
import {
  AdminProduct,
  AdminOrdersResponse,
  StockMovementsResponse,
  ReportResponse,
  CreateProductRequest,
  CreateVariantRequest,
  UpdateVariantRequest,
  AddStockRequest,
  RecordPaymentRequest,
  OrderStatus,
} from '../types/admin.types';

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

/**
 * Create an Axios instance with auth interceptor and 401 session expiry handling.
 */
const createAdminClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: BASE_URL,
    headers: { 'Content-Type': 'application/json' },
  });

  client.interceptors.request.use(async (config) => {
    const authHeaders = await getAuthHeaders();
    Object.entries(authHeaders).forEach(([key, value]) => {
      config.headers.set(key, value);
    });
    return config;
  });

  // Handle 401 session expiry — redirect to login page
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  );

  return client;
};

const adminClient = createAdminClient();

// --- Product Endpoints ---

export const getAdminProducts = async (
  eventId?: string
): Promise<AdminProduct[]> => {
  const params: Record<string, string> = {};
  if (eventId) params.event_id = eventId;
  const response = await adminClient.get('/admin/products', { params });
  // Backend returns {products: [...], total_count: N}
  const data = response.data;
  return data.products ?? data ?? [];
};

export const createAdminProduct = async (
  data: CreateProductRequest
): Promise<AdminProduct> => {
  const response = await adminClient.post<AdminProduct>('/admin/products', data);
  return response.data;
};

export const updateAdminProduct = async (
  id: string,
  data: Partial<CreateProductRequest>
): Promise<AdminProduct> => {
  const response = await adminClient.put<AdminProduct>(
    `/admin/products/${encodeURIComponent(id)}`,
    data
  );
  return response.data;
};

export const createVariant = async (
  productId: string,
  data: CreateVariantRequest
): Promise<void> => {
  await adminClient.post(
    `/admin/products/${encodeURIComponent(productId)}/variants`,
    data
  );
};

export const updateVariant = async (
  productId: string,
  variantId: string,
  data: UpdateVariantRequest
): Promise<void> => {
  await adminClient.put(
    `/admin/products/${encodeURIComponent(productId)}/variants/${encodeURIComponent(variantId)}`,
    data
  );
};

export const deleteVariant = async (
  productId: string,
  variantId: string
): Promise<void> => {
  await adminClient.delete(
    `/admin/products/${encodeURIComponent(productId)}/variants/${encodeURIComponent(variantId)}`
  );
};

export const bulkCreateVariants = async (
  productId: string
): Promise<void> => {
  await adminClient.post(
    `/admin/products/${encodeURIComponent(productId)}/variants/bulk`
  );
};

// --- Stock Endpoints ---

export const addStock = async (
  productId: string,
  variantId: string,
  data: AddStockRequest
): Promise<void> => {
  await adminClient.post(
    `/admin/products/${encodeURIComponent(productId)}/variants/${encodeURIComponent(variantId)}/stock`,
    data
  );
};

export const getStockMovements = async (
  productId: string,
  variantId: string
): Promise<StockMovementsResponse> => {
  const response = await adminClient.get<StockMovementsResponse>(
    `/admin/products/${encodeURIComponent(productId)}/variants/${encodeURIComponent(variantId)}/movements`
  );
  return response.data;
};

// --- Order Endpoints ---

export const getAdminOrders = async (
  eventId?: string,
  status?: string,
  paymentStatus?: string
): Promise<AdminOrdersResponse> => {
  const params: Record<string, string> = {};
  if (eventId) params.event_id = eventId;
  if (status) params.status = status;
  if (paymentStatus) params.payment_status = paymentStatus;
  const response = await adminClient.get('/admin/orders', { params });
  // Backend returns {orders: [...], total_count: N}
  const data = response.data;
  return { orders: data.orders ?? [], total_count: data.total_count ?? 0 };
};

export const updateOrderStatus = async (
  orderId: string,
  targetStatus: OrderStatus
): Promise<void> => {
  await adminClient.put(
    `/admin/orders/${encodeURIComponent(orderId)}/status`,
    { target_status: targetStatus }
  );
};

export const lockOrders = async (eventId?: string): Promise<void> => {
  const params: Record<string, string> = {};
  if (eventId) params.event_id = eventId;
  await adminClient.post('/admin/orders/lock', null, { params });
};

export const unlockOrder = async (orderId: string): Promise<void> => {
  await adminClient.post(
    `/admin/orders/${encodeURIComponent(orderId)}/unlock`
  );
};

// --- Payment Endpoints ---

export const getAdminPayments = async (
  eventId?: string
): Promise<any> => {
  const params: Record<string, string> = {};
  if (eventId) params.event_id = eventId;
  const response = await adminClient.get('/admin/payments', { params });
  // Backend returns {aggregates: {...}, order_payments: [...], total_count: N}
  return response.data;
};

export const recordPayment = async (
  data: RecordPaymentRequest
): Promise<void> => {
  await adminClient.post('/admin/payments', data);
};

// --- Report Endpoints ---

export interface GenerateReportParams {
  event_id?: string;
  report_type?: string;
  order_status?: string;
  payment_status?: string;
}

export const generateReport = async (params?: GenerateReportParams): Promise<void> => {
  const queryParams: Record<string, string> = {};
  if (params?.event_id) queryParams.event_id = params.event_id;
  if (params?.report_type) queryParams.report_type = params.report_type;
  if (params?.order_status && params.order_status !== 'all') queryParams.order_status = params.order_status;
  if (params?.payment_status && params.payment_status !== 'all') queryParams.payment_status = params.payment_status;
  await adminClient.post('/admin/reports/generate', null, { params: queryParams });
};

export const getReport = async (params?: GenerateReportParams): Promise<ReportResponse> => {
  const queryParams: Record<string, string> = {};
  if (params?.event_id) queryParams.event_id = params.event_id;
  if (params?.report_type) queryParams.report_type = params.report_type;
  if (params?.order_status && params.order_status !== 'all') queryParams.order_status = params.order_status;
  if (params?.payment_status && params.payment_status !== 'all') queryParams.payment_status = params.payment_status;
  const response = await adminClient.get<ReportResponse>('/admin/reports', { params: queryParams });
  return response.data;
};

export const exportReport = async (
  format: 'csv' | 'json' = 'json',
  params?: GenerateReportParams
): Promise<Blob> => {
  const queryParams: Record<string, string> = { format };
  if (params?.event_id) queryParams.event_id = params.event_id;
  if (params?.report_type) queryParams.report_type = params.report_type;
  if (params?.order_status && params.order_status !== 'all') queryParams.order_status = params.order_status;
  if (params?.payment_status && params.payment_status !== 'all') queryParams.payment_status = params.payment_status;
  const response = await adminClient.get('/admin/reports/export', {
    params: queryParams,
    responseType: 'blob',
  });
  return response.data;
};

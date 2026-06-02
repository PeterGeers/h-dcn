/**
 * API service for the PresMeet module.
 *
 * Uses the shared ApiService for authenticated requests.
 * All endpoints are prefixed with /presmeet/.
 */

import { ApiService, ApiResponse } from '../../../services/apiService';
import {
  PresMeetConfig,
  PresMeetBooking,
  BookingFormData,
  ValidationResult,
  CartItem,
  PaymentSession,
  ManualPayment,
  ReportMetadata,
  ReportType,
  ReportData,
} from '../types/presmeet';

export const presmeetService = {
  // --- Club User endpoints ---

  /**
   * Get product type configurations and event info.
   */
  getConfig: (): Promise<ApiResponse<PresMeetConfig>> => {
    return ApiService.get<PresMeetConfig>('/presmeet/config');
  },

  /**
   * Get the current club's booking (or a specific club's booking for admins).
   */
  getBooking: (clubId?: string): Promise<ApiResponse<PresMeetBooking>> => {
    const endpoint = clubId
      ? `/presmeet/booking?club_id=${encodeURIComponent(clubId)}`
      : '/presmeet/booking';
    return ApiService.get<PresMeetBooking>(endpoint);
  },

  /**
   * Save booking as draft (upsert). Maps form data to cart items on the backend.
   */
  saveBooking: (data: BookingFormData): Promise<ApiResponse<void>> => {
    return ApiService.put<void>('/presmeet/booking', data);
  },

  /**
   * Validate and submit the booking. Transitions order from draft to submitted.
   */
  submitBooking: (): Promise<ApiResponse<void>> => {
    return ApiService.post<void>('/presmeet/booking/submit');
  },

  /**
   * Validate cart items without submitting. Returns validation errors if any.
   */
  validateBooking: (items: CartItem[]): Promise<ApiResponse<ValidationResult>> => {
    return ApiService.post<ValidationResult>('/presmeet/booking/validate', { items });
  },

  /**
   * Initiate a Mollie payment session for the outstanding balance.
   */
  createPayment: (orderId: string): Promise<ApiResponse<PaymentSession>> => {
    return ApiService.post<PaymentSession>('/presmeet/payment', { order_id: orderId });
  },

  // --- Admin endpoints ---

  /**
   * Trigger report data generation (writes overview, orders, CSV to S3).
   */
  generateReport: (): Promise<ApiResponse<ReportMetadata>> => {
    return ApiService.post<ReportMetadata>('/presmeet/admin/report/generate');
  },

  /**
   * Get pre-computed report data from S3.
   */
  getReport: (type: ReportType = 'overview'): Promise<ApiResponse<ReportData>> => {
    return ApiService.get<ReportData>(`/presmeet/admin/report?type=${encodeURIComponent(type)}`);
  },

  /**
   * Get CSV export data as text.
   */
  getReportCsv: async (type: 'export_submitted' | 'export_all'): Promise<ApiResponse<string>> => {
    return ApiService.request<string>(`/presmeet/admin/report?type=${encodeURIComponent(type)}`, {
      method: 'GET',
      headers: { 'Accept': 'text/csv' },
    });
  },

  /**
   * Lock one or all submitted orders.
   * If orderIds is provided, locks those specific orders.
   * If omitted, performs "Lock ALL" (all submitted → locked).
   */
  lockOrders: (orderIds?: string[]): Promise<ApiResponse<void>> => {
    return ApiService.post<void>('/presmeet/admin/lock', { order_ids: orderIds });
  },

  /**
   * Unlock a locked order (transitions back to submitted).
   */
  unlockOrder: (orderId: string): Promise<ApiResponse<void>> => {
    return ApiService.post<void>(`/presmeet/admin/unlock/${encodeURIComponent(orderId)}`);
  },

  /**
   * Record a manual payment (admin only).
   */
  recordPayment: (data: ManualPayment): Promise<ApiResponse<void>> => {
    return ApiService.post<void>('/presmeet/admin/payment', data);
  },
};

/**
 * useAdminPayments Hook
 *
 * Fetches payment aggregates and order payment list for the Payments tab.
 * Provides a recordPayment function for manual payment recording and
 * a refetch function to reload data.
 *
 * Validates: Requirements 5.1, 5.2
 */

import { useState, useEffect, useCallback } from 'react';
import { getAdminPayments, recordPayment as recordPaymentApi } from '../services/adminApi';
import { PaymentRecord, RecordPaymentRequest } from '../types/admin.types';

export interface PaymentAggregates {
  totalCharged: number;
  totalPaid: number;
  totalOutstanding: number;
}

export interface OrderPaymentSummary {
  order_id: string;
  tenant: string;
  customer: string;
  total: number;
  paid: number;
  outstanding: number;
  payment_status: 'paid' | 'partial' | 'unpaid';
}

export interface UseAdminPaymentsReturn {
  aggregates: PaymentAggregates;
  orderPayments: OrderPaymentSummary[];
  loading: boolean;
  error: string | null;
  recordPayment: (data: RecordPaymentRequest) => Promise<void>;
  refetch: () => void;
}

/**
 * Hook for managing payment data in the admin Payments tab.
 * Loads payment aggregates and per-order payment summaries filtered by tenant.
 */
export function useAdminPayments(tenant: string): UseAdminPaymentsReturn {
  const [aggregates, setAggregates] = useState<PaymentAggregates>({
    totalCharged: 0,
    totalPaid: 0,
    totalOutstanding: 0,
  });
  const [orderPayments, setOrderPayments] = useState<OrderPaymentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPayments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminPayments(tenant || undefined);
      // The API returns payment records — aggregate them client-side
      // Group payments by order_id to build order summaries
      const orderMap = new Map<string, {
        order_id: string;
        tenant: string;
        customer: string;
        total: number;
        paid: number;
      }>();

      // The backend returns a response with aggregates and order details
      // Adapt based on actual API response shape
      const response = data as any;

      if (response.aggregates && response.order_payments) {
        // Structured response from backend
        setAggregates({
          totalCharged: response.aggregates.total_charged ?? 0,
          totalPaid: response.aggregates.total_paid ?? 0,
          totalOutstanding: response.aggregates.total_outstanding ?? 0,
        });

        const summaries: OrderPaymentSummary[] = (response.order_payments || []).map((order: any) => ({
          order_id: order.order_id,
          tenant: order.tenant || '',
          customer: order.customer_name || '',
          total: order.total_amount ?? 0,
          paid: order.amount_paid ?? 0,
          outstanding: order.outstanding ?? (order.total_amount - order.amount_paid),
          payment_status: order.payment_status || 'unpaid',
        }));
        setOrderPayments(summaries);
      } else if (Array.isArray(data)) {
        // Flat payment records array — compute aggregates locally
        let totalPaid = 0;
        data.forEach((p: PaymentRecord) => {
          totalPaid += p.amount;
        });
        setAggregates({
          totalCharged: 0,
          totalPaid,
          totalOutstanding: 0,
        });
        setOrderPayments([]);
      }
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || 'Fout bij laden betalingen');
    } finally {
      setLoading(false);
    }
  }, [tenant]);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  const recordPayment = useCallback(async (data: RecordPaymentRequest) => {
    await recordPaymentApi(data);
    await fetchPayments();
  }, [fetchPayments]);

  const refetch = useCallback(() => {
    fetchPayments();
  }, [fetchPayments]);

  return {
    aggregates,
    orderPayments,
    loading,
    error,
    recordPayment,
    refetch,
  };
}

export default useAdminPayments;

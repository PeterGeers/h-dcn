/**
 * useAdminOrders Hook
 *
 * Data fetching hook for admin order management.
 * Fetches orders from the /admin/orders endpoint with optional
 * channel and status filtering. Provides loading state, error handling,
 * and a refetch function for refreshing data after mutations.
 *
 * Validates: Requirements 4.3, 4.4, 4.5
 */

import { useState, useEffect, useCallback } from 'react';
import { AdminOrder } from '../types/admin.types';
import { getAdminOrders } from '../services/adminApi';

export interface UseAdminOrdersReturn {
  /** List of orders matching the current filters */
  orders: AdminOrder[];
  /** Whether the initial or refetch request is in progress */
  loading: boolean;
  /** Error message if the last request failed */
  error: string | null;
  /** Re-fetch orders with current filters */
  refetch: () => void;
}

/**
 * Fetches admin orders with optional channel and status filtering.
 *
 * @param channel - Filter by channel value (empty string or undefined = all channels)
 * @param status - Filter by order status (optional)
 */
export function useAdminOrders(
  channel?: string,
  status?: string
): UseAdminOrdersReturn {
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getAdminOrders(
        channel || undefined,
        status || undefined
      );
      setOrders(response.orders);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Fout bij ophalen bestellingen';
      setError(message);
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, [channel, status]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  return { orders, loading, error, refetch: fetchOrders };
}

export default useAdminOrders;

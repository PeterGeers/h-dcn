/**
 * useEffectiveLimits — Fetches sold counts and calculates effective limits per product.
 *
 * Effective limit = min(max_per_club - order_qty, max_per_event - sold_count)
 * When max_per_event is absent, only the per-order limit applies.
 *
 * Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.8
 */

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { getAuthHeaders } from '../../../utils/authHeaders';
import { Product } from '../types/eventBooking.types';
import { PersonFormState } from '../utils/orderTransformer';

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

export interface ProductEffectiveLimit {
  product_id: string;
  product_name: string;
  /** Total capacity (Y in "X of Y remaining") */
  totalCapacity: number;
  /** Current remaining (X in "X of Y remaining") */
  remaining: number;
  /** Whether the product is at or below zero remaining */
  isExhausted: boolean;
}

export interface UseEffectiveLimitsResult {
  /** Effective limit info per product */
  limits: ProductEffectiveLimit[];
  /** Whether sold counts are currently loading */
  isLoading: boolean;
  /** Error message if fetch failed */
  error: string | null;
  /** Manually refresh sold counts */
  refresh: () => void;
}

/**
 * Calculate the quantity of a given product across all persons in the current order.
 */
function getOrderQuantityForProduct(
  formState: PersonFormState,
  productId: string
): number {
  let count = 0;
  for (const person of formState.persons) {
    for (const pp of person.products) {
      if (pp.product_id === productId) {
        count += 1;
      }
    }
  }
  return count;
}

/**
 * Hook that fetches product sold counts from the backend and calculates
 * the effective limit for each product based on dual constraints:
 * per-order (max_per_club) and per-event (max_per_event).
 *
 * @param eventId - The event ID to fetch sold counts for
 * @param formState - Current form state (to calculate order quantities)
 * @param products - Product definitions (with purchase_rules)
 */
export function useEffectiveLimits(
  eventId: string | undefined,
  formState: PersonFormState,
  products: Product[]
): UseEffectiveLimitsResult {
  const [soldCounts, setSoldCounts] = useState<Record<string, number>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSoldCounts = useCallback(async () => {
    if (!eventId) return;

    setIsLoading(true);
    setError(null);

    try {
      const headers = await getAuthHeaders();
      const response = await axios.get<Record<string, number>>(
        `${BASE_URL}/products/sold-counts`,
        {
          params: { event_id: eventId },
          headers,
        }
      );
      setSoldCounts(response.data);
    } catch (err: any) {
      const message =
        err?.response?.data?.message || err?.message || 'Failed to fetch sold counts';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [eventId]);

  // Fetch on mount and when eventId changes
  useEffect(() => {
    fetchSoldCounts();
  }, [fetchSoldCounts]);

  // Calculate effective limits based on current form state + sold counts
  const limits: ProductEffectiveLimit[] = products.map((product) => {
    const maxPerClub = product.purchase_rules?.max_per_club;
    const maxPerEvent = product.purchase_rules?.max_per_event;
    const orderQty = getOrderQuantityForProduct(formState, product.product_id);
    const soldCount = soldCounts[product.product_id] || 0;

    // Per-order remaining (how many more can this order add)
    const perOrderRemaining =
      maxPerClub !== undefined ? maxPerClub - orderQty : Infinity;

    // Per-event remaining (how many are left globally)
    const perEventRemaining =
      maxPerEvent !== undefined ? maxPerEvent - soldCount : Infinity;

    // Effective remaining = min of both
    const remaining = Math.min(perOrderRemaining, perEventRemaining);

    // Total capacity (Y in "X of Y remaining"):
    // min(max_per_club, max_per_event) — or whichever is defined
    let totalCapacity: number;
    if (maxPerClub !== undefined && maxPerEvent !== undefined) {
      totalCapacity = Math.min(maxPerClub, maxPerEvent);
    } else if (maxPerClub !== undefined) {
      totalCapacity = maxPerClub;
    } else if (maxPerEvent !== undefined) {
      totalCapacity = maxPerEvent;
    } else {
      totalCapacity = Infinity;
    }

    return {
      product_id: product.product_id,
      product_name: product.naam,
      totalCapacity,
      remaining: Math.max(remaining, 0),
      isExhausted: remaining <= 0,
    };
  });

  return {
    limits,
    isLoading,
    error,
    refresh: fetchSoldCounts,
  };
}

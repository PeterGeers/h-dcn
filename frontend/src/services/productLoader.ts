/**
 * Shared product loading service.
 *
 * Single function to load products for any source (webshop or event).
 * Used by ALL flows: webshop, event booking, admin dashboards.
 *
 * Flow:
 *   1. Fetch event record by source_id → read product_ids[]
 *   2. Batch-get products by IDs via GET /products?product_ids=...
 *   3. Filter out inactive products (active === false)
 *   4. Normalize fields (naam, prijs, order_item_fields)
 */

import { ApiService } from './apiService';

export interface LoadedProduct {
  product_id: string;
  naam?: string;
  name?: string;
  prijs?: number;
  price?: number;
  active?: boolean;
  is_parent?: boolean;
  groep?: string;
  subgroep?: string;
  order_item_fields?: any[];
  variant_attributes?: Record<string, string>;
  [key: string]: any;
}

/**
 * Load products for a given source.
 * This is the ONLY function that should be used to load products across the app.
 *
 * @param sourceId - 'evt-webshop' for webshop, or an event UUID for event booking
 * @returns Array of active, normalized products linked to that source
 *
 * @example
 * // Webshop
 * const products = await loadProductsForSource('evt-webshop');
 *
 * // Event booking
 * const products = await loadProductsForSource('some-event-uuid');
 */
export async function loadProductsForSource(sourceId: string): Promise<LoadedProduct[]> {
  // Step 1: Fetch event record to get product_ids
  const eventResponse = await ApiService.get(`/events/${encodeURIComponent(sourceId)}`);

  if (!eventResponse.success || !eventResponse.data) {
    console.warn(`[productLoader] Could not load event ${sourceId}:`, eventResponse.error);
    return [];
  }

  const eventRecord = eventResponse.data;
  const productIds: string[] = eventRecord.product_ids || [];

  if (productIds.length === 0) {
    return [];
  }

  // Step 2: Batch-get products by IDs (server-side filtering)
  const idsParam = productIds.join(',');
  const productResponse = await ApiService.get(`/products?product_ids=${encodeURIComponent(idsParam)}`);

  if (!productResponse.success) {
    console.warn(`[productLoader] Could not load products for ${sourceId}:`, productResponse.error);
    return [];
  }

  const products = productResponse.data?.products || productResponse.data || [];

  if (!Array.isArray(products)) {
    return [];
  }

  // Step 3: Filter inactive + normalize
  return products
    .filter((p: any) => p.active !== false)
    .map((p: any) => ({
      ...p,
      naam: p.naam || p.name || p.product_id,
      prijs: Number(p.prijs || p.price || 0),
      order_item_fields: Array.isArray(p.order_item_fields) ? p.order_item_fields : [],
    }));
}

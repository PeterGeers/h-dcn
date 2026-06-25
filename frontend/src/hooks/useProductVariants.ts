/**
 * useProductVariants — Shared hook for fetching variant records for a product.
 *
 * Used by both the webshop (ProductCard) and event booking (ProductConfigurator)
 * to load variant data from the GET /products/{id}/variants endpoint.
 *
 * Returns variant records, loading/error state, and whether the product has
 * selectable variant axes (i.e., variants with non-empty variant_attributes).
 */

import { useState, useEffect, useCallback } from 'react';
import { ApiService } from '../services/apiService';
import { VariantRecord } from '../modules/webshop/types/unifiedProduct.types';

export interface UseProductVariantsResult {
  /** Active variant records for the product */
  variants: VariantRecord[];
  /** Whether the fetch is in progress */
  loading: boolean;
  /** Whether the fetch failed */
  error: boolean;
  /** Whether any variant has non-empty variant_attributes (i.e., needs axis selection) */
  hasVariantAxes: boolean;
  /** The default variant (empty variant_attributes) if one exists, null otherwise */
  defaultVariant: VariantRecord | null;
}

/**
 * Fetches variant records for a given product.
 *
 * @param productId - The parent product ID to fetch variants for. Null/empty skips the fetch.
 * @param enabled - Whether to fetch (e.g., false while a modal is closed). Defaults to true.
 */
export function useProductVariants(
  productId: string | null | undefined,
  enabled: boolean = true
): UseProductVariantsResult {
  const [variants, setVariants] = useState<VariantRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<boolean>(false);

  const fetchVariants = useCallback(async (id: string) => {
    // Validate product ID
    const sanitizedId = id.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitizedId || sanitizedId !== id) {
      setError(true);
      return;
    }

    setLoading(true);
    setError(false);

    try {
      const response = await ApiService.get<any>(`/products/${sanitizedId}/variants`);

      // Handle response shape: direct array or { data: { variants: [...] } }
      let variantData: VariantRecord[];
      if (Array.isArray(response)) {
        variantData = response;
      } else if (Array.isArray(response?.data?.variants)) {
        variantData = response.data.variants;
      } else {
        variantData = [];
      }

      // Filter to active variants only
      variantData = variantData.filter((v) => v.active !== false);

      setVariants(variantData);
    } catch (err) {
      console.error('Failed to fetch variants:', err);
      setVariants([]);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!productId || !enabled) {
      setVariants([]);
      setError(false);
      return;
    }

    fetchVariants(productId);
  }, [productId, enabled, fetchVariants]);

  // Derived: does the product have selectable axes?
  const hasVariantAxes = variants.some(
    (v) => Object.keys(v.variant_attributes || {}).length > 0
  );

  // Derived: default variant (variant with empty variant_attributes, used for simple products)
  const defaultVariant = variants.find(
    (v) => Object.keys(v.variant_attributes || {}).length === 0
  ) ?? null;

  return { variants, loading, error, hasVariantAxes, defaultVariant };
}

/**
 * Variant utility functions for deriving axis information from variant records.
 *
 * These are pure functions used by both admin (VariantEditModal) and
 * webshop (VariantSelector) modules.
 */

import { VariantRecord, VariantSchema } from '../modules/webshop/types/unifiedProduct.types';
import { isActive } from './productHelpers';

/**
 * Derives the variant axes and their values from active variant records.
 *
 * Aggregates `variant_attributes` across all active variants to build a map
 * of axis names to unique value arrays. Inactive variants are excluded.
 *
 * @param variants - Array of VariantRecord objects (may include inactive)
 * @returns A VariantSchema mapping each axis name to its unique values
 */
export function deriveAxesFromVariants(variants: VariantRecord[]): VariantSchema {
  const axisMap: Record<string, Set<string>> = {};

  for (const variant of variants) {
    if (!isActive(variant)) continue;

    for (const [axis, value] of Object.entries(variant.variant_attributes || {})) {
      if (!axisMap[axis]) axisMap[axis] = new Set();
      axisMap[axis].add(value);
    }
  }

  const result: VariantSchema = {};
  for (const [axis, values] of Object.entries(axisMap)) {
    result[axis] = Array.from(values);
  }

  return result;
}

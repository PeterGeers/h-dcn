import { VariantSchema } from '../webshop/types/unifiedProduct.types';

/**
 * Formats a variant_schema for CSV export display.
 *
 * Single-axis: "Maat: S, M, L, XL"
 * Multi-axis: "Maat: S, M, L; Kleur: Rood, Blauw"
 * No schema (null/undefined/empty): "Standaard"
 */
export function formatVariantSchemaForCsv(
  variantSchema: VariantSchema | null | undefined
): string {
  if (!variantSchema || Object.keys(variantSchema).length === 0) {
    return 'Standaard';
  }

  return Object.entries(variantSchema)
    .map(([axis, values]) => `${axis}: ${values.join(', ')}`)
    .join('; ');
}

/**
 * Extracted variant unpacking logic from ProductCard.tsx for testability.
 *
 * The fixed code correctly extracts `response.data.variants` (the VariantRecord[] array)
 * instead of `response.data` (the entire wrapper object).
 */
export function extractVariants(response: any): any {
  const variantData = Array.isArray(response)
    ? response
    : Array.isArray(response?.data?.variants)
      ? response.data.variants
      : [];
  return variantData;
}

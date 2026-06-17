/**
 * Shared product helper functions.
 *
 * Centralizes logic that's reused across admin and webshop modules
 * to prevent inconsistencies.
 */

/**
 * Determines if a product can have variants (is a parent or regular product).
 *
 * Returns true for:
 * - Products with is_parent=true
 * - Products with is_parent undefined/null (legacy products, not explicitly a variant)
 *
 * Returns false for:
 * - Products with is_parent=false (these ARE variant records)
 *
 * This is the single source of truth for the "should show variants" check.
 */
export function canHaveVariants(product: { is_parent?: boolean | null }): boolean {
  return product.is_parent !== false;
}

/**
 * Determines if a product/variant is active.
 *
 * Returns true for:
 * - Items with active=true
 * - Items with active undefined/null (legacy — treated as active)
 *
 * Returns false ONLY for:
 * - Items with active=false (explicitly deactivated)
 *
 * This is the single source of truth for "is this item active" checks.
 */
export function isActive(item: { active?: boolean | null }): boolean {
  return item.active !== false;
}

/**
 * Application-wide constants for the H-DCN admin portal.
 */

/**
 * Maximum number of variant axes allowed per product.
 *
 * Per an explicit product decision, a product supports a single variant axis at
 * a time (either sizes or colours, not a size×colour matrix). This value is
 * therefore 1.
 *
 * Controls VariantEditModal create mode behavior:
 * - Under MAX_AXES (zero axes): allow free-text axis name input
 * - At MAX_AXES (one axis already present): restrict to the existing axis only
 */
export const MAX_AXES = 1;

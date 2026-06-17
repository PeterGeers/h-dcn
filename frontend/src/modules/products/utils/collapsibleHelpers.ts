/**
 * Helper functions for CollapsibleSection default state logic.
 */

/**
 * Determines whether a CollapsibleSection should default to open (expanded).
 *
 * Returns true when the images array is non-empty, false when empty, undefined, or null.
 * Used by the images CollapsibleSection to default expanded iff images exist.
 *
 * @param images - The product images array (may be undefined or null)
 * @returns true if section should be expanded, false if collapsed
 */
export function shouldDefaultOpen(images: string[] | undefined | null): boolean {
  if (!images) {
    return false;
  }
  return images.length > 0;
}

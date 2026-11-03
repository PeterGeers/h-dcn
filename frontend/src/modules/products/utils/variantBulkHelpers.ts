/**
 * Pure helpers for the single-axis bulk variant generator.
 *
 * These functions contain no React and no I/O. They support the BulkVariantCreator
 * modal by normalizing the raw value list the admin enters and by computing a live
 * preview of how many variants a submission would create.
 */

/**
 * Normalize a raw list of axis values before submission.
 *
 * Trims each entry, drops empty / whitespace-only entries, and de-duplicates
 * case-sensitively while preserving first-seen order.
 *
 * @param raw - Raw value strings as entered by the admin (e.g. one per line)
 * @returns Cleaned, de-duplicated values in first-seen order
 */
export function normalizeValues(raw: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];

  for (const entry of raw) {
    const trimmed = entry.trim();
    if (trimmed.length === 0) {
      continue;
    }
    if (seen.has(trimmed)) {
      continue;
    }
    seen.add(trimmed);
    result.push(trimmed);
  }

  return result;
}

/**
 * Count how many variants would be created for the requested values.
 *
 * Normalizes the requested values, then counts those whose value is not already
 * present among the existing values. Existing values are compared case-sensitively.
 *
 * @param requested - Requested axis values (raw, not yet normalized)
 * @param existing - Values that already exist for this axis on the parent
 * @returns The number of new variants that would be created
 */
export function previewCreateCount(requested: string[], existing: string[]): number {
  const existingSet = new Set(existing);
  const normalized = normalizeValues(requested);

  let count = 0;
  for (const value of normalized) {
    if (!existingSet.has(value)) {
      count += 1;
    }
  }

  return count;
}

import { AdminVariant } from '../types/admin.types';

/**
 * Priority map for standard clothing sizes.
 * Recognized sizes are sorted in this fixed order (case-insensitive matching).
 */
export const SIZE_ORDER: Record<string, number> = {
  xxs: 1,
  xs: 2,
  s: 3,
  m: 4,
  l: 5,
  xl: 6,
  xxl: 7,
  '3xl': 8,
  '4xl': 9,
  '5xl': 10,
};

/**
 * Checks if a string represents a numeric value.
 */
function isNumeric(value: string): boolean {
  return value.trim() !== '' && !isNaN(Number(value));
}

/**
 * Sorts an array of size values using clothing-size logic:
 * 1. Recognized clothing sizes first, in standard order (XXS → 5XL)
 * 2. Unrecognized non-numeric values next, sorted case-insensitively alphabetically
 * 3. Numeric values last, sorted in ascending numeric order
 *
 * Matching is case-insensitive.
 *
 * @param values - Array of size strings to sort
 * @returns A new sorted array (does not mutate the input)
 */
export function sortSizeValues(values: string[]): string[] {
  const recognized: string[] = [];
  const unrecognizedNonNumeric: string[] = [];
  const numeric: string[] = [];

  for (const value of values) {
    const lower = value.toLowerCase();
    if (SIZE_ORDER[lower] !== undefined) {
      recognized.push(value);
    } else if (isNumeric(value)) {
      numeric.push(value);
    } else {
      unrecognizedNonNumeric.push(value);
    }
  }

  recognized.sort(
    (a, b) => SIZE_ORDER[a.toLowerCase()] - SIZE_ORDER[b.toLowerCase()]
  );

  unrecognizedNonNumeric.sort((a, b) =>
    a.toLowerCase().localeCompare(b.toLowerCase())
  );

  numeric.sort((a, b) => Number(a) - Number(b));

  return [...recognized, ...unrecognizedNonNumeric, ...numeric];
}

/**
 * Sorts variants by:
 * 1. First axis defined in variantSchema using sizeSorter logic
 * 2. Subsequent axes in case-insensitive alphabetical order
 *
 * @param variants - Array of AdminVariant objects to sort
 * @param variantSchema - The variant schema defining axes and their values
 * @returns A new sorted array (does not mutate the input)
 */
export function sortVariants(
  variants: AdminVariant[],
  variantSchema: Record<string, string[]>
): AdminVariant[] {
  const axes = Object.keys(variantSchema);
  if (axes.length === 0) {
    return [...variants];
  }

  const firstAxis = axes[0];

  // Build a sort-order index for the first axis using sizeSorter logic
  const firstAxisValues = variantSchema[firstAxis] ?? [];
  const sortedFirstAxisValues = sortSizeValues(firstAxisValues);
  const firstAxisOrder = new Map<string, number>();
  sortedFirstAxisValues.forEach((val, idx) => {
    firstAxisOrder.set(val.toLowerCase(), idx);
  });

  return [...variants].sort((a, b) => {
    // Sort by first axis using size sorter logic
    const aFirstVal = a.variant_attributes[firstAxis] ?? '';
    const bFirstVal = b.variant_attributes[firstAxis] ?? '';

    const aFirstOrder = firstAxisOrder.get(aFirstVal.toLowerCase());
    const bFirstOrder = firstAxisOrder.get(bFirstVal.toLowerCase());

    // Values not in the schema get sorted to the end via size sort logic
    const aFirstPos = aFirstOrder ?? sortedFirstAxisValues.length;
    const bFirstPos = bFirstOrder ?? sortedFirstAxisValues.length;

    if (aFirstPos !== bFirstPos) {
      return aFirstPos - bFirstPos;
    }

    // If first axis values are equal, sort by subsequent axes alphabetically
    for (let i = 1; i < axes.length; i++) {
      const axis = axes[i];
      const aVal = (a.variant_attributes[axis] ?? '').toLowerCase();
      const bVal = (b.variant_attributes[axis] ?? '').toLowerCase();
      const cmp = aVal.localeCompare(bVal);
      if (cmp !== 0) {
        return cmp;
      }
    }

    return 0;
  });
}

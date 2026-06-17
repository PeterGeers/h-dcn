/**
 * Helper functions for VariantEditModal create mode logic.
 *
 * - determineFormMode: determines the UI state based on existing variant axes
 * - validateAxisInput: validates axis name and value inputs
 */

import { AdminVariant } from '../../webshop-management/types/admin.types';
import { MAX_AXES } from '../../../config/constants';

/**
 * Possible form mode states for the VariantEditModal create mode.
 *
 * - 'zero-axes': No variants exist yet — free text for axis name and value
 * - 'under-max': 1 to MAX_AXES-1 distinct axes exist — dropdown of existing + free text option
 * - 'at-max': MAX_AXES distinct axes exist — dropdown only, no free text
 */
export type FormMode = 'zero-axes' | 'under-max' | 'at-max';

/**
 * Determines the form mode for VariantEditModal create mode based on existing variants.
 *
 * Counts distinct axis names across all variant_attributes in the provided variants.
 * - 0 distinct axes → 'zero-axes'
 * - 1 to MAX_AXES-1 → 'under-max'
 * - MAX_AXES or more → 'at-max'
 *
 * @param existingVariants - Array of AdminVariant records for the parent product
 * @returns The form mode state
 */
export function determineFormMode(existingVariants: AdminVariant[]): FormMode {
  const axisNames = new Set<string>();

  for (const variant of existingVariants) {
    for (const axisName of Object.keys(variant.variant_attributes)) {
      axisNames.add(axisName);
    }
  }

  const distinctCount = axisNames.size;

  if (distinctCount === 0) {
    return 'zero-axes';
  }

  if (distinctCount >= MAX_AXES) {
    return 'at-max';
  }

  return 'under-max';
}

/**
 * Validates axis name and value inputs for variant creation.
 *
 * Both axisName and value must be non-empty strings after trimming.
 * Rejects empty strings and whitespace-only strings.
 *
 * @param axisName - The axis name to validate
 * @param value - The axis value to validate
 * @returns true if both inputs are valid, false otherwise
 */
export function validateAxisInput(axisName: string, value: string): boolean {
  return axisName.trim().length > 0 && value.trim().length > 0;
}

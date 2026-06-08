/**
 * Purchase Rules Configuration
 *
 * Defines the available options for purchase rules configuration
 * in the product admin modal. Used by PurchaseRulesEditor to
 * populate dropdown options from configuration data.
 */

export interface OrderModeOption {
  value: string;
  label: string;
  description: string;
}

/**
 * Available order modes for products.
 * Used to populate the Bestelmodus dropdown in PurchaseRulesEditor.
 */
export const ORDER_MODE_OPTIONS: OrderModeOption[] = [
  {
    value: 'single',
    label: 'Single (eenmalige bestelling)',
    description: 'Klant kan het product één keer bestellen',
  },
  {
    value: 'persistent',
    label: 'Persistent (heropbare bestelling per club)',
    description: 'Bestellingen kunnen heropend worden per club',
  },
];

/**
 * Default order mode when none is configured
 */
export const DEFAULT_ORDER_MODE = 'single';

/**
 * Numeric field constraints for purchase rules
 */
export const PURCHASE_RULES_LIMITS = {
  min: 1,
  max: 9999,
} as const;

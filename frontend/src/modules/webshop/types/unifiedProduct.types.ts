/**
 * Unified Product Types for the H-DCN Webshop.
 *
 * These types represent the unified product/order/payment pipeline that merges
 * the H-DCN webshop and PresMeet booking systems. The core change splits the
 * legacy `required_attributes` field into purpose-built fields:
 * - order_item_fields: per-item data collected from the buyer at checkout
 * - purchase_rules: business constraints on purchasing
 *
 * Variant axes are no longer stored on parent products. They are derived at
 * runtime from active variant records via `deriveAxesFromVariants()`.
 */

import { Product } from '../../../types';

// --- Variant Schema ---

/** Maps axis names to their possible values (e.g., { "Maat": ["S", "M", "L"] }) */
export type VariantSchema = Record<string, string[]>;

/** Array-of-axes format used by PresMeet products (e.g., [{name: "Size", values: ["S","M","L"]}]) */
export type VariantSchemaAxes = Array<{ name: string; values: string[] }>;

/**
 * Normalize variant_schema to the Record format expected by VariantSelector.
 * Used by PresMeet products which use an array-of-axes format.
 * Handles both formats:
 * - Record format (h-dcn products): { "Maat": ["S", "M", "L"] } → returned as-is
 * - Array format (presmeet products): [{name: "Size", values: ["S","M","L"]}] → converted
 */
export function normalizeVariantSchema(
  schema: VariantSchema | VariantSchemaAxes | null | undefined
): VariantSchema | null {
  if (!schema) return null;
  if (Array.isArray(schema)) {
    // Array-of-axes format → convert to Record
    const result: VariantSchema = {};
    for (const axis of schema) {
      if (axis.name && Array.isArray(axis.values)) {
        result[axis.name] = axis.values;
      }
    }
    return Object.keys(result).length > 0 ? result : null;
  }
  // Already in Record format
  return schema;
}

// --- Order Item Fields ---

/** Supported field types for per-item data collection */
export type OrderItemFieldType = 'text' | 'select' | 'date' | 'number' | 'email';

/** Validation constraints for an order item field */
export interface OrderItemFieldValidation {
  /** Minimum string length (text, email) */
  min_length?: number;
  /** Maximum string length (text, email) */
  max_length?: number;
  /** Minimum numeric value (number) */
  minimum?: number;
  /** Maximum numeric value (number) */
  maximum?: number;
  /** Regex pattern for value validation (text, email) */
  pattern?: string;
}

/** Definition of a single per-item data field configured on a product */
export interface OrderItemField {
  /** Unique identifier within the product (alphanumeric + underscores, max 50 chars) */
  id: string;
  /** Display label shown to the buyer (max 200 chars) */
  label: string;
  /** Input type determining the rendered control and validation rules */
  type: OrderItemFieldType;
  /** Whether the field must be filled before order submission */
  required: boolean;
  /** Optional validation constraints (type-specific) */
  validation?: OrderItemFieldValidation;
  /** Options for select-type fields (1–50 string values) */
  options?: string[];
}

// --- Purchase Rules ---

/** Order mode determining order lifecycle behaviour */
export type OrderMode = 'single' | 'persistent';

/** Business constraints on purchasing a product */
export interface PurchaseRules {
  /** Maximum quantity allowed per single order (1–9999) */
  max_per_order?: number;
  /** Maximum total quantity a member can purchase across paid/pending orders (1–9999) */
  max_per_member?: number;
  /** Maximum total quantity a club can purchase across paid/pending orders (1–9999) */
  max_per_club?: number;
  /** Minimum quantity a club must order (1–9999, must not exceed max_per_club) */
  min_per_club?: number;
  /** Whether an active membership is required to purchase */
  requires_membership?: boolean;
  /** Order mode: "single" (one-shot) or "persistent" (reopenable per club) */
  order_mode?: OrderMode;
}

// --- Unified Product ---

/**
 * Unified product interface extending the base Product type with the three
 * new configuration fields and additional catalog/metadata fields.
 */
export interface UnifiedProduct extends Product {
  /** Unique product identifier */
  product_id: string;
  /** Event linkage: null for general webshop products, event UUID for event-linked products */
  event_id?: string | null;
  /** Product description */
  description?: string;
  /** Whether the product is active and visible in the webshop */
  active: boolean;
  /** Whether this is a parent product record */
  is_parent: boolean;
  /** Array of S3 image URLs (up to 10) */
  images?: string[];

  /** Per-item data fields collected from the buyer at checkout */
  order_item_fields?: OrderItemField[];
  /** Business constraints on purchasing */
  purchase_rules?: PurchaseRules;

  /** Legacy field — ignored when new fields are present */
  required_attributes?: Record<string, unknown>;
  /** Original opties value preserved after migration */
  legacy_opties?: string;

  /** Admin who created the product */
  created_by?: string;
  /** ISO 8601 creation timestamp */
  created_at?: string;
  /** ISO 8601 last update timestamp */
  updated_at?: string;
}

// --- Variant Record ---

/** A variant record representing a specific purchasable SKU with its own stock */
export interface VariantRecord {
  /** Unique variant identifier (PK in Producten table) */
  product_id: string;
  /** Reference to the parent product */
  parent_id: string;
  /** Display name (e.g., "Club T-shirt - S / Male") */
  name: string;
  /** Mapping of axis name to selected value for this variant */
  variant_attributes: Record<string, string>;
  /** Price (inherited from parent or overridden) */
  price: number;
  /** Current available stock count */
  stock: number;
  /** Total units sold */
  sold_count: number;
  /** Whether orders are accepted when stock is 0 */
  allow_oversell: boolean;
  /** Whether the variant is active */
  active: boolean;
}

// --- Cart Types ---

/** Per-item field values collected during cart/checkout phase */
export interface ItemFieldsEntry {
  /** Map of field_id to submitted value for a single item */
  field_values: Record<string, string>;
}

/** A single line item in the shopping cart */
export interface CartItem {
  /** Reference to the parent product */
  product_id: string;
  /** Reference to the specific variant being purchased */
  variant_id: string;
  /** Axis selections for display (e.g., { "Maat": "S", "Gender": "Male" }) */
  variant_attributes: Record<string, string>;
  /** Number of units (minimum 1) */
  quantity: number;
  /** Unit price at time of adding to cart */
  unit_price: number;
  /** Per-item registration data (one entry per quantity unit, can be partial) */
  item_fields_data?: ItemFieldsEntry[];
}

// --- Payment Types ---

/** Supported payment methods */
export type PaymentMethod = 'ideal' | 'creditcard' | 'bank_transfer';

/** Response from backend when a Mollie payment is created */
export interface MolliePaymentResponse {
  /** Order identifier */
  order_id: string;
  /** Current payment status */
  payment_status: 'pending' | 'unpaid';
  /** Mollie-hosted checkout URL for redirect (present for online payments) */
  checkout_url?: string;
  /** Bank transfer instructions (present for bank_transfer method) */
  transfer_instructions?: TransferInstructions;
}

/** Instructions for completing a bank transfer payment */
export interface TransferInstructions {
  /** Order reference to include in the transfer description */
  reference: string;
  /** Bank account IBAN to transfer to */
  iban: string;
  /** Amount to transfer in EUR */
  amount: number;
}

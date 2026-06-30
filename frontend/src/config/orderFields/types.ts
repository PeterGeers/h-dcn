/**
 * Order Field Configuration System - Type Definitions
 *
 * All interfaces and type aliases used across the orderFields module.
 * Follows the eventFields pattern as single source of truth for Orders table fields.
 *
 * Architecture decision: Orders replace Carts table (see docs/decisions/orders-replace-carts.md).
 * Status lifecycle:
 *   - Event orders: draft → submitted → locked
 *   - Webshop orders: draft → submitted → order_received → paid → shipped → delivered → completed
 */

import type { HDCNGroup } from '../../types/user';
export type { HDCNGroup } from '../../types/user';

// ============================================================================
// BASE TYPE ALIASES
// ============================================================================

export type DataType = 'string' | 'number' | 'boolean' | 'enum' | 'map' | 'list' | 'datetime';
export type InputType = 'text' | 'number' | 'select' | 'hidden' | 'json' | 'datetime' | 'multiselect';
export type FieldGroup = 'identity' | 'source' | 'status' | 'financial' | 'items' | 'delegates' | 'metadata';

// ============================================================================
// ORDER STATUS TYPES (mirroring frontend type definitions)
// ============================================================================

/**
 * Event booking order statuses.
 */
export const EVENT_ORDER_STATUSES = ['draft', 'submitted', 'locked'] as const;

/**
 * Webshop order statuses (full fulfillment lifecycle).
 */
export const WEBSHOP_ORDER_STATUSES = [
  'draft',
  'submitted',
  'locked',
  'order_received',
  'payment_pending',
  'payment_failed',
  'paid',
  'picked',
  'packed',
  'shipped',
  'delivered',
  'return_requested',
  'return_received',
  'completed',
] as const;

/**
 * All possible order statuses (union).
 */
export const ALL_ORDER_STATUSES = [...WEBSHOP_ORDER_STATUSES] as const;

export type OrderStatus = (typeof ALL_ORDER_STATUSES)[number];

/**
 * Payment statuses.
 */
export const PAYMENT_STATUSES = ['unpaid', 'partial', 'paid', 'pending', 'awaiting_payment'] as const;
export type PaymentStatus = (typeof PAYMENT_STATUSES)[number];

// ============================================================================
// FIELD CONFIGURATION INTERFACES
// ============================================================================

export interface ConditionalRule {
  field: string;
  operator: 'equals' | 'not_equals' | 'exists' | 'not_exists';
  value?: any;
}

export interface ValidationRule {
  type: 'required' | 'min_length' | 'max_length' | 'min' | 'max' | 'pattern' | 'custom';
  value?: any;
  message?: string;
  condition?: ConditionalRule;
}

export interface PermissionConfig {
  view: HDCNGroup[];
  edit: HDCNGroup[];
}

export interface OrderFieldDefinition {
  /** DynamoDB attribute name — the canonical key */
  key: string;
  /** Display label (Dutch) */
  label: string;
  /** DynamoDB data type */
  dataType: DataType;
  /** Form input type */
  inputType: InputType;
  /** Logical field group */
  group: FieldGroup;
  /** Display order within group */
  order: number;
  /** Whether field is required for save */
  required?: boolean;
  /** Validation rules */
  validation?: ValidationRule[];
  /** Permission configuration */
  permissions?: PermissionConfig;

  // UI Properties
  /** Placeholder text for form input */
  placeholder?: string;
  /** Help text / tooltip */
  helpText?: string;
  /** Column width hint */
  width?: 'small' | 'medium' | 'large' | 'full';

  // Data Properties
  /** Enum options for select fields */
  enumOptions?: readonly string[];
  /** Default value for new records */
  defaultValue?: any;
  /** Field cannot be edited (system-managed) */
  readOnly?: boolean;

  // Conditional Logic
  /** Only show this field when conditions are met */
  showWhen?: ConditionalRule[];
}

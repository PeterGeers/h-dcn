/**
 * Event Field Configuration System - Type Definitions
 *
 * All interfaces and type aliases used across the eventFields module.
 * Follows the memberFields pattern as single source of truth for Event table fields.
 */

import type { HDCNGroup } from '../../types/user';
export type { HDCNGroup } from '../../types/user';

// ============================================================================
// BASE TYPE ALIASES
// ============================================================================

export type DataType = 'string' | 'date' | 'number' | 'boolean' | 'enum' | 'map' | 'object';
export type InputType = 'text' | 'date' | 'select' | 'textarea' | 'number' | 'toggle' | 'json' | 'password';
export type FieldGroup = 'core' | 'booking';

// ============================================================================
// FIELD CONFIGURATION INTERFACES
// ============================================================================

export interface ConditionalRule {
  field: string;
  operator: 'equals' | 'not_equals' | 'exists' | 'not_exists';
  value?: any;
}

export interface ValidationRule {
  type: 'required' | 'min_length' | 'max_length' | 'pattern' | 'custom';
  value?: any;
  message?: string;
  condition?: ConditionalRule;
}

export interface PermissionConfig {
  view: HDCNGroup[];
  edit: HDCNGroup[];
  writeOnly?: boolean; // Field is never returned in API responses (e.g., event_password)
}

export interface FieldDefinition {
  key: string;
  label: string;
  dataType: DataType;
  inputType: InputType;
  group: FieldGroup;
  order: number;
  required?: boolean | ConditionalRule;
  validation?: ValidationRule[];
  permissions?: PermissionConfig;

  // UI Properties
  placeholder?: string;
  helpText?: string;
  width?: 'small' | 'medium' | 'large' | 'full';

  // Data Properties
  enumOptions?: string[];
  defaultValue?: any;
  readOnly?: boolean; // Field cannot be edited (e.g., event_id)

  // Conditional Logic
  showWhen?: ConditionalRule[];

  // Display Properties
  displayFormat?: string;
}

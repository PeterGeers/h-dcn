/**
 * Member Field Configuration System - Type Definitions
 *
 * All interfaces and type aliases used across the memberFields module.
 */

// Import HDCNGroup from user.ts to avoid duplication
import type { HDCNGroup } from '../../types/user';
export type { HDCNGroup } from '../../types/user';

// ============================================================================
// BASE TYPE ALIASES
// ============================================================================

export type DataType = 'string' | 'date' | 'number' | 'boolean' | 'enum';
export type InputType = 'text' | 'email' | 'date' | 'select' | 'textarea' | 'number' | 'tel' | 'url' | 'iban';
export type FieldGroup = 'personal' | 'address' | 'membership' | 'motor' | 'financial' | 'administrative';

// ============================================================================
// FIELD CONFIGURATION INTERFACES
// ============================================================================

export interface ConditionalRule {
  field: string;
  operator: 'equals' | 'not_equals' | 'contains' | 'not_contains' | 'exists' | 'not_exists' | 'age_less_than';
  value?: any;
}

export interface ValidationRule {
  type: 'required' | 'email' | 'phone' | 'postal_code' | 'iban' | 'min_length' | 'max_length' | 'min' | 'max' | 'pattern' | 'custom';
  value?: any;
  message?: string;
  condition?: ConditionalRule;
}

export interface PermissionConfig {
  view: HDCNGroup[];
  edit: HDCNGroup[];
  selfService?: boolean; // Can members edit their own data
  regionalRestricted?: boolean; // Restricted to regional access
  membershipTypeRestricted?: string[]; // Only for specific membership types
}

export interface FieldDefinition {
  key: string;
  label: string;
  dataType: DataType;
  inputType: InputType;
  group: FieldGroup;
  order: number; // Display order within group
  required?: boolean | ConditionalRule;
  validation?: ValidationRule[];
  permissions?: PermissionConfig;

  // UI Properties
  placeholder?: string;
  helpText?: string;
  width?: 'small' | 'medium' | 'large' | 'full';

  // Data Properties
  enumOptions?: string[]; // For select/enum fields
  enumPermissions?: Record<string, HDCNGroup[]>; // Role-based enum option filtering
  defaultValue?: any;

  // Conditional Logic
  showWhen?: ConditionalRule[];
  hideWhen?: ConditionalRule[];
  conditionalEdit?: {
    condition: ConditionalRule;
    permissions: PermissionConfig;
  };

  // Display Properties
  displayFormat?: string; // For dates, numbers, etc.
  prefix?: string; // € for currency
  suffix?: string; // % for percentages

  // Computed Fields
  computed?: boolean;
  computeFrom?: string | string[];
  computeFunction?: string;
}

// ============================================================================
// EMAIL NOTIFICATION CONFIGURATION
// ============================================================================

export interface EmailNotificationConfig {
  enabled: boolean;
  templates: {
    applicantConfirmation: string;
    adminNotification: string;
  };
  recipients: {
    admin: string[];
    cc?: string[];
    bcc?: string[];
  };
  triggers: {
    onSubmission: boolean;
    onStatusChange: boolean;
    onApproval: boolean;
    onRejection: boolean;
  };
}

// ============================================================================
// TABLE CONFIGURATION INTERFACES
// ============================================================================

export interface TableColumnConfig {
  fieldKey: string;
  visible: boolean;
  order: number;
  width?: number | string; // pixels or percentage
  sortable?: boolean;
  filterable?: boolean;
  filterType?: 'text' | 'select' | 'date' | 'number' | 'boolean';
  sticky?: boolean; // for sticky columns
  align?: 'left' | 'center' | 'right';
}

export interface TableContextConfig {
  name: string;
  description: string;
  columns: TableColumnConfig[];
  defaultSort?: {
    field: string;
    direction: 'asc' | 'desc';
  };
  pageSize?: number;
  exportable?: boolean;
  regionalRestricted?: boolean; // Filter data to user's region only
  permissions: {
    view: HDCNGroup[];
    export?: HDCNGroup[];
  };
}

// ============================================================================
// MODAL CONFIGURATION INTERFACES
// ============================================================================

export interface ModalFieldConfig {
  fieldKey: string;
  visible: boolean;
  readOnly?: boolean;
  order: number;
  span?: 1 | 2 | 3; // Grid span (1=33%, 2=66%, 3=100%)
  conditionalVisible?: ConditionalRule[];
}

export interface ModalGroupConfig {
  group: FieldGroup;
  visible: boolean;
  order: number;
  excludeFields?: string[]; // Fields to exclude from the group
  includeFields?: string[]; // Only include these fields from the group
  fieldOverrides?: Partial<ModalFieldConfig>[]; // Override specific field configs
}

export interface ModalSectionConfig {
  name: string;
  title: string;
  order: number;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  fields?: ModalFieldConfig[]; // Individual field configs
  groups?: ModalGroupConfig[]; // Group-based field configs
  showWhen?: ConditionalRule[];
  permissions?: {
    view: HDCNGroup[];
    edit?: HDCNGroup[];
  };
}

export interface ModalContextConfig {
  name: string;
  description: string;
  sections: ModalSectionConfig[];
  permissions: {
    view: HDCNGroup[];
    edit?: HDCNGroup[];
  };
}

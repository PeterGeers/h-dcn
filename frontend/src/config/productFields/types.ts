/**
 * Product Field Configuration System - Type Definitions
 *
 * Defines the canonical field structure for the Producten DynamoDB table.
 * All code (frontend, backend, specs) MUST reference this registry.
 */

export type ProductDataType = 'string' | 'number' | 'boolean' | 'list' | 'map';
export type ProductInputType = 'text' | 'number' | 'select' | 'multiselect' | 'textarea' | 'checkbox' | 'image-upload' | 'json-editor' | 'hidden';
export type ProductFieldGroup = 'identity' | 'pricing' | 'categorization' | 'media' | 'variants' | 'ordering' | 'metadata';
export type ProductRecordType = 'parent' | 'variant' | 'both';

export interface ProductFieldDefinition {
  /** DynamoDB attribute name — the canonical key */
  key: string;
  /** Display label (Dutch) */
  label: string;
  /** DynamoDB data type */
  dataType: ProductDataType;
  /** Form input type */
  inputType: ProductInputType;
  /** Logical field group */
  group: ProductFieldGroup;
  /** Display order within group */
  order: number;
  /** Whether field is required for save */
  required?: boolean;
  /** Applies to parent records, variant records, or both */
  recordType: ProductRecordType;
  /** Placeholder text for form input */
  placeholder?: string;
  /** Help text / tooltip */
  helpText?: string;
  /** Whether field is editable by the user */
  editable?: boolean;
  /** Default value for new records */
  defaultValue?: any;
}

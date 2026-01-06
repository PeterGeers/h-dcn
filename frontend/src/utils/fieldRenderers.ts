/**
 * Field Rendering Utilities
 * 
 * Utilities for rendering field values and generating form inputs based on field definitions
 */

import { FieldDefinition, HDCNGroup } from '../config/memberFields';

/**
 * Format a field value for display based on field definition
 */
export function renderFieldValue(
  field: FieldDefinition, 
  value: any, 
  displayFormat?: string
): string {
  if (value === null || value === undefined || value === '') {
    return '-';
  }

  const format = displayFormat || field.displayFormat;

  switch (field.dataType) {
    case 'date':
      return formatDateValue(value, format);
    
    case 'number':
      return formatNumberValue(value, field);
    
    case 'boolean':
      return value ? 'Ja' : 'Nee';
    
    case 'enum':
      return formatEnumValue(value, field);
    
    case 'string':
    default:
      return formatStringValue(value, field);
  }
}

/**
 * Format date values
 */
function formatDateValue(value: any, format?: string): string {
  try {
    const date = new Date(value);
    if (isNaN(date.getTime())) {
      return String(value);
    }

    // Default format is dd-MM-yyyy
    const defaultFormat = format || 'dd-MM-yyyy';
    
    if (defaultFormat === 'dd-MM-yyyy') {
      return date.toLocaleDateString('nl-NL', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
    }
    
    if (defaultFormat === 'dd-MM-yyyy HH:mm:ss') {
      return date.toLocaleDateString('nl-NL', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    }
    
    // Fallback to ISO string
    return date.toLocaleDateString('nl-NL');
  } catch (error) {
    return String(value);
  }
}

/**
 * Format number values with prefix/suffix
 */
function formatNumberValue(value: any, field: FieldDefinition): string {
  const numValue = Number(value);
  if (isNaN(numValue)) {
    return String(value);
  }

  let formatted = numValue.toString();
  
  if (field.prefix) {
    formatted = field.prefix + formatted;
  }
  
  if (field.suffix) {
    formatted = formatted + ' ' + field.suffix;
  }
  
  return formatted;
}

/**
 * Format enum values with human-readable labels
 */
function formatEnumValue(value: any, field: FieldDefinition): string {
  // For now, return the value as-is
  // In the future, we could add a mapping for more user-friendly labels
  return String(value);
}

/**
 * Format string values
 */
function formatStringValue(value: any, field: FieldDefinition): string {
  let formatted = String(value);
  
  // Handle special formatting for specific input types
  switch (field.inputType) {
    case 'email':
      // Could add email masking for privacy if needed
      return formatted;
    
    case 'tel':
      // Could add phone number formatting
      return formatted;
    
    case 'iban':
      // Format IBAN with spaces for readability
      return formatIBAN(formatted);
    
    default:
      return formatted;
  }
}

/**
 * Format IBAN for better readability
 */
function formatIBAN(iban: string): string {
  if (!iban) return iban;
  
  // Remove existing spaces and convert to uppercase
  const cleanIban = iban.replace(/\s/g, '').toUpperCase();
  
  // Add spaces every 4 characters
  return cleanIban.replace(/(.{4})/g, '$1 ').trim();
}

/**
 * Get appropriate input component type based on field definition
 */
export function getFieldInputComponent(field: FieldDefinition): {
  type: string;
  component: 'input' | 'select' | 'textarea';
  props: Record<string, any>;
} {
  const baseProps = {
    placeholder: field.placeholder,
    required: Boolean(field.required),
    disabled: field.computed || false
  };

  switch (field.inputType) {
    case 'select':
      return {
        type: 'select',
        component: 'select',
        props: {
          ...baseProps,
          options: field.enumOptions || []
        }
      };
    
    case 'textarea':
      return {
        type: 'textarea',
        component: 'textarea',
        props: {
          ...baseProps,
          rows: 3
        }
      };
    
    case 'date':
      return {
        type: 'date',
        component: 'input',
        props: baseProps
      };
    
    case 'number':
      return {
        type: 'number',
        component: 'input',
        props: {
          ...baseProps,
          min: getValidationValue(field, 'min_length'),
          max: getValidationValue(field, 'max_length')
        }
      };
    
    case 'email':
      return {
        type: 'email',
        component: 'input',
        props: baseProps
      };
    
    case 'tel':
      return {
        type: 'tel',
        component: 'input',
        props: baseProps
      };
    
    case 'iban':
      return {
        type: 'text',
        component: 'input',
        props: {
          ...baseProps,
          pattern: '[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}',
          maxLength: 34
        }
      };
    
    case 'text':
    default:
      return {
        type: 'text',
        component: 'input',
        props: {
          ...baseProps,
          maxLength: getValidationValue(field, 'max_length')
        }
      };
  }
}

/**
 * Get validation value from field definition
 */
function getValidationValue(field: FieldDefinition, validationType: string): any {
  if (!field.validation) return undefined;
  
  const rule = field.validation.find(rule => rule.type === validationType);
  return rule?.value;
}

/**
 * Validate field value against field definition
 */
export function validateFieldValue(
  field: FieldDefinition, 
  value: any, 
  memberData?: any
): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  if (!field.validation) {
    return { isValid: true, errors: [] };
  }

  for (const rule of field.validation) {
    // Check if validation rule has a condition
    if (rule.condition && memberData) {
      const conditionMet = evaluateCondition(rule.condition, memberData);
      if (!conditionMet) {
        continue; // Skip this validation rule
      }
    }

    const error = validateRule(rule, value, field);
    if (error) {
      errors.push(error);
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Validate a single validation rule
 */
function validateRule(rule: any, value: any, field: FieldDefinition): string | null {
  switch (rule.type) {
    case 'required':
      if (!value || (typeof value === 'string' && value.trim() === '')) {
        return rule.message || `${field.label} is verplicht`;
      }
      break;
    
    case 'email':
      if (value && !isValidEmail(value)) {
        return rule.message || 'Voer een geldig emailadres in';
      }
      break;
    
    case 'phone':
      if (value && !isValidPhone(value)) {
        return rule.message || 'Voer een geldig telefoonnummer in';
      }
      break;
    
    case 'iban':
      if (value && !isValidIBAN(value)) {
        return rule.message || 'Voer een geldig IBAN nummer in';
      }
      break;
    
    case 'min_length':
      if (value && value.length < rule.value) {
        return rule.message || `Minimaal ${rule.value} karakters vereist`;
      }
      break;
    
    case 'max_length':
      if (value && value.length > rule.value) {
        return rule.message || `Maximaal ${rule.value} karakters toegestaan`;
      }
      break;
    
    case 'min':
      if (value !== null && value !== undefined && Number(value) < rule.value) {
        return rule.message || `Waarde moet minimaal ${rule.value} zijn`;
      }
      break;
    
    case 'max':
      if (value !== null && value !== undefined && Number(value) > rule.value) {
        return rule.message || `Waarde mag maximaal ${rule.value} zijn`;
      }
      break;
    
    case 'pattern':
      if (value && !new RegExp(rule.value).test(value)) {
        return rule.message || 'Ongeldige invoer';
      }
      break;
  }
  
  return null;
}

/**
 * Simple email validation
 */
function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Simple phone validation (supports international formats)
 */
function isValidPhone(phone: string): boolean {
  // Remove all non-digit characters
  const digits = phone.replace(/\D/g, '');
  
  // Should have at least 10 digits
  return digits.length >= 10;
}

/**
 * Basic IBAN validation
 */
function isValidIBAN(iban: string): boolean {
  // Remove spaces and convert to uppercase
  const cleanIban = iban.replace(/\s/g, '').toUpperCase();
  
  // Basic format check (2 letters + 2 digits + up to 30 alphanumeric)
  const ibanRegex = /^[A-Z]{2}[0-9]{2}[A-Z0-9]{4,30}$/;
  
  if (!ibanRegex.test(cleanIban)) {
    return false;
  }
  
  // For now, just check format. Full IBAN validation would require mod-97 check
  return true;
}

/**
 * Evaluate a conditional rule (copied from fieldResolver for consistency)
 */
function evaluateCondition(condition: any, memberData: any): boolean {
  const fieldValue = memberData[condition.field];
  
  switch (condition.operator) {
    case 'equals':
      return fieldValue === condition.value;
    case 'not_equals':
      return fieldValue !== condition.value;
    case 'contains':
      return Array.isArray(condition.value) 
        ? condition.value.includes(fieldValue)
        : String(fieldValue).includes(String(condition.value));
    case 'not_contains':
      return Array.isArray(condition.value)
        ? !condition.value.includes(fieldValue)
        : !String(fieldValue).includes(String(condition.value));
    case 'exists':
      return fieldValue !== undefined && fieldValue !== null && fieldValue !== '';
    case 'not_exists':
      return fieldValue === undefined || fieldValue === null || fieldValue === '';
    case 'age_less_than':
      if (condition.field === 'geboortedatum' && fieldValue) {
        const birthDate = new Date(fieldValue);
        const today = new Date();
        const age = today.getFullYear() - birthDate.getFullYear();
        const monthDiff = today.getMonth() - birthDate.getMonth();
        
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
          return (age - 1) < condition.value;
        }
        return age < condition.value;
      }
      return false;
    default:
      return true;
  }
}

/**
 * Format field for display in tables/lists
 */
export function formatFieldForDisplay(
  field: FieldDefinition, 
  value: any, 
  context: 'table' | 'modal' | 'form' = 'table'
): string {
  const formatted = renderFieldValue(field, value);
  
  // Apply context-specific formatting
  if (context === 'table') {
    // Truncate long values in tables
    if (formatted.length > 50) {
      return formatted.substring(0, 47) + '...';
    }
  }
  
  return formatted;
}

/**
 * Get field width class for CSS styling
 */
export function getFieldWidthClass(field: FieldDefinition): string {
  switch (field.width) {
    case 'small':
      return 'w-1/4';
    case 'medium':
      return 'w-1/2';
    case 'large':
      return 'w-3/4';
    case 'full':
      return 'w-full';
    default:
      return 'w-1/2'; // Default to medium
  }
}

/**
 * Generate form field props for React components
 */
export function getFormFieldProps(
  field: FieldDefinition,
  value: any,
  onChange: (value: any) => void,
  userRole: HDCNGroup,
  memberData?: any
): {
  field: FieldDefinition;
  value: any;
  onChange: (value: any) => void;
  inputProps: Record<string, any>;
  validation: { isValid: boolean; errors: string[] };
  disabled: boolean;
} {
  const inputComponent = getFieldInputComponent(field);
  const validation = validateFieldValue(field, value, memberData);
  
  // Check if field is disabled (computed, no edit permission, etc.)
  const disabled = field.computed || 
    !field.permissions?.edit?.includes(userRole) ||
    inputComponent.props.disabled;

  return {
    field,
    value,
    onChange,
    inputProps: {
      ...inputComponent.props,
      type: inputComponent.type,
      disabled
    },
    validation,
    disabled
  };
}
import type { TFunction } from 'i18next';

/** Supported validation rule types matching the Field Registry */
export type ValidationRuleType =
  | 'required'
  | 'email'
  | 'phone'
  | 'iban'
  | 'min_length'
  | 'max_length'
  | 'min'
  | 'max'
  | 'pattern'
  | 'invalid_number'
  | 'invalid_option';

/** Parameters for interpolation per rule type */
export interface ValidationParams {
  field?: string;
  count?: number;
  value?: number;
}

/**
 * Returns a translated validation message using the caller's domain-bound t function.
 *
 * The t function determines namespace resolution — if the caller uses
 * useTranslation('products'), keys resolve from products:validation.*.
 *
 * Falls back to the original Dutch string via defaultValue for backward
 * compatibility during incremental migration.
 */
export function getValidationMessage(
  t: TFunction,
  ruleType: ValidationRuleType,
  params?: ValidationParams,
): string {
  const key = `validation.${ruleType}`;

  // Fallback Dutch strings match the current hardcoded messages
  const fallbacks: Record<ValidationRuleType, string> = {
    required: `${params?.field || 'Veld'} is verplicht`,
    email: 'Voer een geldig emailadres in',
    phone: 'Voer een geldig telefoonnummer in',
    iban: 'Voer een geldig IBAN nummer in',
    min_length: `Minimaal ${params?.count || 0} karakters vereist`,
    max_length: `Maximaal ${params?.count || 0} karakters toegestaan`,
    min: `Waarde moet minimaal ${params?.value || 0} zijn`,
    max: `Waarde mag maximaal ${params?.value || 0} zijn`,
    pattern: 'Ongeldige invoer',
    invalid_number: 'Voer een geldig nummer in',
    invalid_option: 'Selecteer een geldige optie',
  };

  return t(key, { ...params, defaultValue: fallbacks[ruleType] });
}

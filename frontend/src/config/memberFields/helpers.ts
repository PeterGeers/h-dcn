/**
 * Member Field Configuration System - Helper Functions
 *
 * All exported utility functions for working with field definitions,
 * table contexts, and modal contexts.
 */

import type {
  FieldDefinition,
  FieldGroup,
  HDCNGroup,
  ModalContextConfig,
  ModalFieldConfig,
  ModalSectionConfig,
} from './types';

import { MEMBER_MODAL_CONTEXTS } from './modalConfig';
import {
  personalFields,
  addressFields,
  membershipFields,
  motorFields,
  financialFields,
  administrativeFields,
} from './fields';

// Assemble field registry from partials (avoids circular dependency with index.ts)
const MEMBER_FIELDS: Record<string, FieldDefinition> = {
  ...personalFields,
  ...addressFields,
  ...membershipFields,
  ...motorFields,
  ...financialFields,
  ...administrativeFields,
};

// ============================================================================
// MODAL CONTEXT UTILITY FUNCTIONS
// ============================================================================

/**
 * Get modal configuration by context name
 */
export function getModalContext(contextName: string): ModalContextConfig | undefined {
  return MEMBER_MODAL_CONTEXTS[contextName];
}

/**
 * Get visible sections for a modal context, sorted by order
 */
export function getVisibleSections(contextName: string, userRole: HDCNGroup): ModalSectionConfig[] {
  const context = MEMBER_MODAL_CONTEXTS[contextName];
  if (!context) return [];

  return context.sections
    .filter(section => section.permissions?.view.includes(userRole))
    .sort((a, b) => a.order - b.order);
}

/**
 * Get visible fields for a section, sorted by order
 * Supports both individual fields and group-based configurations
 */
export function getVisibleFields(section: ModalSectionConfig): ModalFieldConfig[] {
  const fields: ModalFieldConfig[] = [];

  // Add individual fields
  if (section.fields) {
    fields.push(...section.fields.filter(field => field.visible));
  }

  // Add group-based fields
  if (section.groups) {
    section.groups
      .filter(groupConfig => groupConfig.visible)
      .forEach(groupConfig => {
        const groupFields = getFieldsByGroup(groupConfig.group);

        groupFields.forEach(fieldDef => {
          // Check if field should be included
          if (groupConfig.includeFields && !groupConfig.includeFields.includes(fieldDef.key)) {
            return; // Skip if not in include list
          }

          if (groupConfig.excludeFields && groupConfig.excludeFields.includes(fieldDef.key)) {
            return; // Skip if in exclude list
          }

          // Create field config with defaults
          const fieldConfig: ModalFieldConfig = {
            fieldKey: fieldDef.key,
            visible: true,
            order: fieldDef.order + (groupConfig.order * 100), // Offset by group order
            span: fieldDef.width === 'small' ? 1 : fieldDef.width === 'large' ? 2 : fieldDef.width === 'full' ? 3 : 1
          };

          // Apply field overrides
          if (groupConfig.fieldOverrides) {
            const override = groupConfig.fieldOverrides.find(o => o.fieldKey === fieldDef.key);
            if (override) {
              Object.assign(fieldConfig, override);
            }
          }

          fields.push(fieldConfig);
        });
      });
  }

  return fields.sort((a, b) => a.order - b.order);
}

/**
 * Check if user can edit a modal context
 */
export function canEditModalContext(contextName: string, userRole: HDCNGroup): boolean {
  const context = MEMBER_MODAL_CONTEXTS[contextName];
  if (!context || !context.permissions.edit) return false;

  return context.permissions.edit.includes(userRole);
}

// ============================================================================
// FIELD UTILITY FUNCTIONS
// ============================================================================

/**
 * Get all fields for a specific group
 */
export function getFieldsByGroup(group: FieldGroup): FieldDefinition[] {
  return Object.values(MEMBER_FIELDS)
    .filter(field => field.group === group)
    .sort((a, b) => a.order - b.order);
}

/**
 * Get field definition by key
 */
export function getFieldDefinition(key: string): FieldDefinition | undefined {
  return MEMBER_FIELDS[key];
}

/**
 * Get all field keys
 */
export function getAllFieldKeys(): string[] {
  return Object.keys(MEMBER_FIELDS);
}

/**
 * Get fields by permission level
 */
export function getFieldsByPermission(permissionLevel: HDCNGroup, action: 'view' | 'edit'): FieldDefinition[] {
  return Object.values(MEMBER_FIELDS).filter(field =>
    field.permissions?.[action]?.includes(permissionLevel)
  );
}

/**
 * Get filtered enum options based on user role permissions
 */
export function getFilteredEnumOptions(field: FieldDefinition, userRole: HDCNGroup): string[] {
  if (!field.enumOptions) return [];

  // If no enum permissions are defined, return all options
  if (!field.enumPermissions) return field.enumOptions;

  // Filter options based on role permissions
  return field.enumOptions.filter(option => {
    const requiredRoles = field.enumPermissions![option];
    // If no specific permissions for this option, it's available to all
    if (!requiredRoles) return true;
    // Check if user role is in the required roles
    return requiredRoles.includes(userRole);
  });
}

// ============================================================================
// REGION NORMALIZATION
// ============================================================================

/**
 * Region normalization mapping for consistent region names
 * Maps various input formats to standardized region names
 */
export const REGION_NORMALIZATION_MAP: Record<string, string> = {
  // Brabant/Zeeland variations
  'brabant/zeeland': 'Brabant/Zeeland',
  'BRABANT/ZEELAND': 'Brabant/Zeeland',
  'Noord-Brabant/Zeeland': 'Brabant/Zeeland',
  'noord-brabant/zeeland': 'Brabant/Zeeland',
  'NOORD-BRABANT/ZEELAND': 'Brabant/Zeeland',

  // Other region normalizations
  'noord-holland': 'Noord-Holland',
  'NOORD-HOLLAND': 'Noord-Holland',
  'zuid-holland': 'Zuid-Holland',
  'ZUID-HOLLAND': 'Zuid-Holland',
  'friesland': 'Friesland',
  'FRIESLAND': 'Friesland',
  'utrecht': 'Utrecht',
  'UTRECHT': 'Utrecht',
  'oost': 'Oost',
  'OOST': 'Oost',
  'limburg': 'Limburg',
  'LIMBURG': 'Limburg',
  'groningen/drenthe': 'Groningen/Drenthe',
  'GRONINGEN/DRENTHE': 'Groningen/Drenthe',
  'duitsland': 'Duitsland',
  'DUITSLAND': 'Duitsland',
  'overig': 'Overig',
  'OVERIG': 'Overig'
};

/**
 * Normalize region name to standard format
 * @param region - Input region name (any case/format)
 * @returns Normalized region name or original if no mapping found
 */
export function normalizeRegion(region: string): string {
  if (!region) return region;

  // Check direct mapping first
  const normalized = REGION_NORMALIZATION_MAP[region];
  if (normalized) return normalized;

  // Check case-insensitive mapping
  const lowerRegion = region.toLowerCase();
  const normalizedLower = REGION_NORMALIZATION_MAP[lowerRegion];
  if (normalizedLower) return normalizedLower;

  // Return original if no mapping found
  return region;
}

/**
 * Get field groups in display order
 */
export function getFieldGroups(): FieldGroup[] {
  return ['personal', 'address', 'membership', 'motor', 'financial', 'administrative'];
}

/**
 * Member Field Configuration System - Table Context Definitions
 *
 * Contains all table context configurations and table-related utility functions.
 * Types are imported from ./types (TableColumnConfig, TableContextConfig).
 */

import type { TableColumnConfig, TableContextConfig, HDCNGroup } from './types';

// ============================================================================
// MEMBER TABLE CONFIGURATIONS
// ============================================================================

export const MEMBER_TABLE_CONTEXTS: Record<string, TableContextConfig> = {
  // Default member overview table
  memberOverview: {
    name: 'Member Overview',
    description: 'Standard member table for general administration',
    columns: [
      { fieldKey: 'lidnummer', visible: true, order: 1, width: 80, sortable: true, filterable: true, filterType: 'number', sticky: true },
      { fieldKey: 'korte_naam', visible: true, order: 2, width: 200, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'geboortedatum', visible: true, order: 3, width: 110, sortable: true, filterable: true, filterType: 'date' },
      { fieldKey: 'email', visible: true, order: 4, width: 200, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'telefoon', visible: false, order: 7, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'straat', visible: true, order: 8, width: 180, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'postcode', visible: true, order: 9, width: 80, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'woonplaats', visible: true, order: 10, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'land', visible: false, order: 11, width: 100, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'regio', visible: true, order: 12, width: 120, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'status', visible: true, order: 13, width: 100, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'lidmaatschap', visible: true, order: 14, width: 130, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'ingangsdatum', visible: true, order: 15, width: 110, sortable: true, filterable: true, filterType: 'date' },
      { fieldKey: 'jaren_lid', visible: true, order: 16, width: 80, sortable: true, filterable: true, filterType: 'number', align: 'center' }
    ],
    defaultSort: { field: 'korte_naam', direction: 'asc' },
    pageSize: 50,
    exportable: true,
    regionalRestricted: true,
    permissions: {
      view: ['Members_Read', 'Members_CRUD', 'System_User_Management'],
      export: ['Members_Read', 'Members_CRUD', 'System_User_Management']
    }
  },

  // Compact table for quick lookups
  memberCompact: {
    name: 'Member Compact',
    description: 'Minimal member table for quick reference',
    columns: [
      { fieldKey: 'lidnummer', visible: true, order: 1, width: 50, sortable: true, filterable: true, filterType: 'number', sticky: true },
      { fieldKey: 'korte_naam', visible: true, order: 2, width: 180, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'email', visible: true, order: 3, width: 180, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'regio', visible: true, order: 4, width: 100, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'status', visible: true, order: 6, width: 90, sortable: true, filterable: true, filterType: 'select' }
    ],
    defaultSort: { field: 'lidnummer', direction: 'asc' },
    pageSize: 100,
    exportable: false,
    regionalRestricted: true,
    permissions: {
      view: ['Members_Read', 'Members_CRUD', 'System_User_Management']
    }
  },

  // Motor-focused view for events/rides
  motorView: {
    name: 'Motor Members',
    description: 'Member table focused on motor information',
    columns: [
      { fieldKey: 'lidnummer', visible: true, order: 1, width: 80, sortable: true, filterable: true, filterType: 'number', sticky: true },
      { fieldKey: 'korte_naam', visible: true, order: 2, width: 180, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'regio', visible: true, order: 3, width: 120, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'motormerk', visible: true, order: 4, width: 130, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'motortype', visible: true, order: 6, width: 150, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'bouwjaar', visible: true, order: 7, width: 90, sortable: true, filterable: true, filterType: 'number', align: 'center' },
      { fieldKey: 'kenteken', visible: true, order: 8, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'telefoon', visible: true, order: 9, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'email', visible: false, order: 10, width: 200, sortable: true, filterable: true, filterType: 'text' }
    ],
    defaultSort: { field: 'motormerk', direction: 'asc' },
    pageSize: 50,
    exportable: true,
    regionalRestricted: true,
    permissions: {
      view: ['hdcnLeden', 'Members_Read', 'Members_CRUD', 'System_User_Management', 'Events_Read'],
      export: ['Members_CRUD', 'Events_CRUD']
    }
  },

  // Communication-focused view
  communicationView: {
    name: 'Communication List',
    description: 'Member table for communication and marketing',
    columns: [
      { fieldKey: 'korte_naam', visible: true, order: 1, width: 180, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'email', visible: true, order: 2, width: 220, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'straat', visible: true, order: 3, width: 180, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'postcode', visible: true, order: 5, width: 80, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'woonplaats', visible: true, order: 6, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'land', visible: false, order: 7, width: 100, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'regio', visible: true, order: 8, width: 120, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'clubblad', visible: true, order: 9, width: 100, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'nieuwsbrief', visible: true, order: 10, width: 100, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'privacy', visible: true, order: 11, width: 80, sortable: true, filterable: true, filterType: 'select', align: 'center' },
      { fieldKey: 'status', visible: true, order: 12, width: 100, sortable: true, filterable: true, filterType: 'select' }
    ],
    defaultSort: { field: 'korte_naam', direction: 'asc' },
    pageSize: 100,
    exportable: true,
    regionalRestricted: true,
    permissions: {
      view: ['Members_Read', 'Members_CRUD', 'Communication_Read', 'Communication_CRUD'],
      export: ['Members_CRUD', 'Communication_Export']
    }
  },

  // Financial overview
  financialView: {
    name: 'Financial Overview',
    description: 'Member table for financial administration',
    columns: [
      { fieldKey: 'lidnummer', visible: true, order: 1, width: 80, sortable: true, filterable: true, filterType: 'number', sticky: true },
      { fieldKey: 'korte_naam', visible: true, order: 2, width: 180, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'lidmaatschap', visible: true, order: 3, width: 130, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'betaalwijze', visible: true, order: 4, width: 110, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'bankrekeningnummer', visible: true, order: 6, width: 200, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'status', visible: true, order: 7, width: 100, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'regio', visible: true, order: 8, width: 120, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'ingangsdatum', visible: true, order: 9, width: 110, sortable: true, filterable: true, filterType: 'date' },
      { fieldKey: 'jaren_lid', visible: true, order: 10, width: 80, sortable: true, filterable: true, filterType: 'number', align: 'center' }
    ],
    defaultSort: { field: 'korte_naam', direction: 'asc' },
    pageSize: 50,
    exportable: true,
    permissions: {
      view: ['Members_Read', 'Members_CRUD'],
      export: ['Members_Read', 'Members_CRUD']
    }
  }
};

// ============================================================================
// TABLE UTILITY FUNCTIONS
// ============================================================================

/**
 * Get table configuration by context name
 */
export function getTableContext(contextName: string): TableContextConfig | undefined {
  return MEMBER_TABLE_CONTEXTS[contextName];
}

/**
 * Get visible columns for a table context, sorted by order
 */
export function getVisibleColumns(contextName: string): TableColumnConfig[] {
  const context = MEMBER_TABLE_CONTEXTS[contextName];
  if (!context) return [];

  return context.columns
    .filter(col => col.visible)
    .sort((a, b) => a.order - b.order);
}

/**
 * Get filterable columns for a table context
 */
export function getFilterableColumns(contextName: string): TableColumnConfig[] {
  const context = MEMBER_TABLE_CONTEXTS[contextName];
  if (!context) return [];

  return context.columns.filter(col => col.visible && col.filterable);
}

/**
 * Check if user has permission to view table context
 */
export function canViewTableContext(contextName: string, userRole: HDCNGroup): boolean {
  const context = MEMBER_TABLE_CONTEXTS[contextName];
  if (!context) return false;

  return context.permissions.view.includes(userRole);
}

/**
 * Get all available table contexts for a user role
 */
export function getAvailableTableContexts(userRole: HDCNGroup): TableContextConfig[] {
  return Object.values(MEMBER_TABLE_CONTEXTS)
    .filter(context => context.permissions.view.includes(userRole));
}

/**
 * Event Field Configuration System - Permission Helpers
 *
 * Permission configuration factory function and permission-related constants
 * for the event field system.
 */

import type { HDCNGroup, PermissionConfig } from './types';

// ============================================================================
// PERMISSION LEVEL TYPES
// ============================================================================

export type ViewLevel = 'public' | 'participant' | 'admin' | 'system';
export type EditLevel = 'none' | 'admin' | 'system';

// ============================================================================
// PERMISSION HELPER FUNCTIONS
// ============================================================================

/**
 * Helper function to generate permission configurations for event fields.
 * Event fields are generally admin-managed (no self-service by members).
 */
export const createPermissionConfig = (
  viewLevel: ViewLevel = 'admin',
  editLevel: EditLevel = 'none',
  options?: { writeOnly?: boolean }
): PermissionConfig => {
  const viewPermissions: HDCNGroup[] = [];
  const editPermissions: HDCNGroup[] = [];

  // View permissions based on level
  switch (viewLevel) {
    case 'public':
      viewPermissions.push('hdcnLeden', 'Events_Read', 'Events_CRUD');
      break;
    case 'participant':
      viewPermissions.push('hdcnLeden', 'Events_Read', 'Events_CRUD');
      break;
    case 'admin':
      viewPermissions.push('Events_Read', 'Events_CRUD');
      break;
    case 'system':
      viewPermissions.push('System_User_Management');
      break;
  }

  // Edit permissions based on level
  switch (editLevel) {
    case 'admin':
      editPermissions.push('Events_CRUD');
      break;
    case 'system':
      editPermissions.push('System_User_Management');
      break;
    // 'none' case: no edit permissions
  }

  return {
    view: viewPermissions,
    edit: editPermissions,
    ...(options?.writeOnly ? { writeOnly: true } : {}),
  };
};

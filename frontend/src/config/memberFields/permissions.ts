/**
 * Member Field Configuration System - Permission Helpers
 *
 * Permission configuration factory function and permission-related constants
 * for the member field system.
 */

import type { HDCNGroup } from './types';
import type { PermissionConfig } from './types';

// ============================================================================
// PERMISSION LEVEL TYPES
// ============================================================================

export type ViewLevel = 'public' | 'member' | 'admin' | 'system';
export type EditLevel = 'none' | 'self' | 'admin' | 'system';

// ============================================================================
// PERMISSION HELPER FUNCTIONS FOR NEW ROLE STRUCTURE
// ============================================================================

/**
 * Helper function to generate permission configurations for the new role structure
 * This makes it easier to maintain consistent permissions across all fields
 */
export const createPermissionConfig = (
  viewLevel: ViewLevel = 'member',
  editLevel: EditLevel = 'none',
  selfService: boolean = false
): PermissionConfig => {
  const viewPermissions: HDCNGroup[] = [];
  const editPermissions: HDCNGroup[] = [];

  // View permissions based on level
  switch (viewLevel) {
    case 'public':
      viewPermissions.push('hdcnLeden', 'Members_Read', 'Members_CRUD');
      break;
    case 'member':
      viewPermissions.push('hdcnLeden', 'Members_Read', 'Members_CRUD');
      break;
    case 'admin':
      viewPermissions.push('Members_Read', 'Members_CRUD');
      break;
    case 'system':
      viewPermissions.push('System_User_Management');
      break;
  }

  // Edit permissions based on level
  switch (editLevel) {
    case 'self':
      if (selfService) {
        editPermissions.push('hdcnLeden');
      }
      editPermissions.push('Members_CRUD');
      // System administrators can edit self-service fields for user support
      if (selfService) {
        editPermissions.push('System_User_Management');
      }
      break;
    case 'admin':
      editPermissions.push('Members_CRUD');
      // System administrators can edit self-service fields for user support
      if (selfService) {
        editPermissions.push('System_User_Management');
      }
      break;
    case 'system':
      editPermissions.push('System_User_Management');
      break;
    // 'none' case: no edit permissions
  }

  return {
    view: viewPermissions,
    edit: editPermissions,
    selfService
  };
};

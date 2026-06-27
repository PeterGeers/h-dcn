/**
 * Order Field Configuration System - Permission Helpers
 *
 * Permission configuration factory function and permission-related constants
 * for the order field system.
 *
 * Orders are primarily managed by members (their own orders) and admins.
 * Regional scoping is NOT applied to orders — admins see all orders.
 */

import type { HDCNGroup, PermissionConfig } from './types';

// ============================================================================
// PERMISSION LEVEL TYPES
// ============================================================================

export type ViewLevel = 'owner' | 'admin' | 'system';
export type EditLevel = 'none' | 'owner' | 'admin' | 'system';

// ============================================================================
// PERMISSION HELPER FUNCTIONS
// ============================================================================

/**
 * Helper function to generate permission configurations for order fields.
 *
 * - 'owner': the member who owns the order (hdcnLeden) + admins (Webshop_Management)
 * - 'admin': only users with Webshop_Management
 * - 'system': only System_User_Management
 *
 * Note: There is no separate Orders_Read/Orders_CRUD role.
 * Order admin access is governed by Webshop_Management.
 */
export const createPermissionConfig = (
  viewLevel: ViewLevel = 'admin',
  editLevel: EditLevel = 'none'
): PermissionConfig => {
  const viewPermissions: HDCNGroup[] = [];
  const editPermissions: HDCNGroup[] = [];

  // View permissions based on level
  switch (viewLevel) {
    case 'owner':
      viewPermissions.push('hdcnLeden', 'Webshop_Management');
      break;
    case 'admin':
      viewPermissions.push('Webshop_Management');
      break;
    case 'system':
      viewPermissions.push('System_User_Management');
      break;
  }

  // Edit permissions based on level
  switch (editLevel) {
    case 'owner':
      editPermissions.push('hdcnLeden', 'Webshop_Management');
      break;
    case 'admin':
      editPermissions.push('Webshop_Management');
      break;
    case 'system':
      editPermissions.push('System_User_Management');
      break;
    // 'none' case: no edit permissions
  }

  return {
    view: viewPermissions,
    edit: editPermissions,
  };
};

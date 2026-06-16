/**
 * useAdminPermissions — Shared hook for webshop management role-based access control.
 *
 * Returns permission flags based on user's Cognito groups:
 * - canRead: user can view all tabs (Products_Read, Products_CRUD, Products_Export, or Webshop_Management)
 * - canMutate: user can create, update, delete, lock/unlock, record payments (Products_CRUD or Webshop_Management)
 * - canExport: user can download CSV/JSON exports (Products_Export)
 *
 * Webshop_Management is treated as equivalent to Products_CRUD for backward compatibility.
 *
 * Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
 */

import { useContext } from 'react';
import { AuthContext } from '../../../context/AuthProvider';

export interface AdminPermissions {
  canRead: boolean;
  canMutate: boolean;
  canExport: boolean;
}

const CRUD_ROLES = ['Products_CRUD', 'Webshop_Management'];
const READ_ROLES = ['Products_Read', 'Products_CRUD', 'Products_Export', 'Webshop_Management'];
const EXPORT_ROLES = ['Products_Export'];

/**
 * Determines if user has CRUD (mutation) permission.
 * Exported for use in components that don't use the hook (e.g., unit tests).
 */
export function hasCrudPermission(groups: string[]): boolean {
  return groups.some((g) => CRUD_ROLES.includes(g));
}

/**
 * Determines if user has read permission (any Products_* or Webshop_Management role).
 */
export function hasReadPermission(groups: string[]): boolean {
  return groups.some((g) => READ_ROLES.includes(g));
}

/**
 * Determines if user has export permission.
 */
export function hasExportPermission(groups: string[]): boolean {
  return groups.some((g) => EXPORT_ROLES.includes(g));
}

/**
 * Hook returning role-based permission flags for the webshop management section.
 * Returns safe defaults (no permissions) if AuthProvider is not available.
 */
export function useAdminPermissions(): AdminPermissions {
  const context = useContext(AuthContext);
  const groups = context?.user?.groups ?? [];

  return {
    canRead: hasReadPermission(groups),
    canMutate: hasCrudPermission(groups),
    canExport: hasExportPermission(groups),
  };
}

export default useAdminPermissions;

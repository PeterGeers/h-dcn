/**
 * useTenantFilter Hook
 *
 * Custom React hook for managing tenant filter state.
 * Persists the selected tenant to localStorage so the selection
 * is preserved across page navigations and refreshes.
 */

import { useState, useCallback } from 'react';

const STORAGE_KEY = 'webshop-management-tenant-filter';

function getInitialTenant(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'presmeet' || stored === 'h-dcn') {
      return stored;
    }
  } catch {
    // localStorage not available (SSR or privacy mode)
  }
  return '';
}

export interface UseTenantFilterReturn {
  /** Currently selected tenant (empty string means "all") */
  tenant: string;
  /** Update the selected tenant */
  setTenant: (value: string) => void;
}

/**
 * Manages tenant filter state with localStorage persistence.
 * Returns the current tenant value and a setter function.
 *
 * An empty string ("") represents "all tenants" (no filter applied).
 */
export function useTenantFilter(): UseTenantFilterReturn {
  const [tenant, setTenantState] = useState<string>(getInitialTenant);

  const setTenant = useCallback((value: string) => {
    setTenantState(value);
    try {
      if (value) {
        localStorage.setItem(STORAGE_KEY, value);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // localStorage not available
    }
  }, []);

  return { tenant, setTenant };
}

export default useTenantFilter;

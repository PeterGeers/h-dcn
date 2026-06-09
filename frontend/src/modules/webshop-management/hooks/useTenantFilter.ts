/**
 * useChannelFilter Hook
 *
 * Custom React hook for managing channel filter state.
 * Persists the selected channel to localStorage so the selection
 * is preserved across page navigations and refreshes.
 */

import { useState, useCallback } from 'react';

const STORAGE_KEY = 'webshop-management-channel-filter';

function getInitialChannel(): string {
  try {
    // Check new key first, fall back to legacy key
    const stored = localStorage.getItem(STORAGE_KEY)
      || localStorage.getItem('webshop-management-tenant-filter');
    if (stored === 'presmeet' || stored === 'h-dcn') {
      return stored;
    }
  } catch {
    // localStorage not available (SSR or privacy mode)
  }
  return '';
}

export interface UseChannelFilterReturn {
  /** Currently selected channel (empty string means "all") */
  channel: string;
  /** Update the selected channel */
  setChannel: (value: string) => void;
}

/**
 * Manages channel filter state with localStorage persistence.
 * Returns the current channel value and a setter function.
 *
 * An empty string ("") represents "all channels" (no filter applied).
 */
export function useChannelFilter(): UseChannelFilterReturn {
  const [channel, setChannelState] = useState<string>(getInitialChannel);

  const setChannel = useCallback((value: string) => {
    setChannelState(value);
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

  return { channel, setChannel };
}

/** @deprecated Use useChannelFilter instead */
export function useTenantFilter(): { tenant: string; setTenant: (value: string) => void } {
  const { channel, setChannel } = useChannelFilter();
  return { tenant: channel, setTenant: setChannel };
}

export default useChannelFilter;

/**
 * useEventFilter Hook
 *
 * Custom React hook for managing event-based filter state.
 *
 * Filter values:
 * - "" (empty string) = "Alle" (all products, no filter)
 * - "webshop" = products where event_id is null (generic webshop products)
 * - "<event_id>" = products linked to a specific event
 *
 * Persists the selected filter to localStorage so the selection
 * is preserved across page navigations and refreshes.
 */

import { useState, useCallback, useEffect } from 'react';
import { getAuthHeaders } from '../../../utils/authHeaders';

const STORAGE_KEY = 'webshop-management-event-filter';

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

export interface EventOption {
  event_id: string;
  name: string;
}

export interface UseEventFilterReturn {
  /** Currently selected filter value (empty = all, "webshop" = null event_id, UUID = specific event) */
  eventFilter: string;
  /** Update the selected filter */
  setEventFilter: (value: string) => void;
  /** Available events loaded from the API */
  events: EventOption[];
  /** Whether events are currently loading */
  loadingEvents: boolean;
}

function getInitialFilter(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return stored;
    }
  } catch {
    // localStorage not available
  }
  return '';
}

/**
 * Manages event filter state with localStorage persistence.
 * Fetches events from the backend to populate filter options.
 *
 * An empty string ("") represents "all" (no filter applied).
 * "webshop" represents products with event_id = null.
 * Any other value is treated as an event_id UUID.
 */
export function useEventFilter(): UseEventFilterReturn {
  const [eventFilter, setEventFilterState] = useState<string>(getInitialFilter);
  const [events, setEvents] = useState<EventOption[]>([]);
  const [loadingEvents, setLoadingEvents] = useState<boolean>(true);

  const setEventFilter = useCallback((value: string) => {
    setEventFilterState(value);
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

  useEffect(() => {
    let cancelled = false;

    const fetchEvents = async () => {
      try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${BASE_URL}/events`, {
          headers: {
            'Content-Type': 'application/json',
            ...headers,
          },
        });

        if (!response.ok) {
          console.error('Failed to fetch events for filter:', response.status);
          return;
        }

        const data = await response.json();
        // Backend may return array directly or {events: [...]}
        const eventsList = Array.isArray(data) ? data : (data.events ?? []);

        if (!cancelled) {
          setEvents(
            eventsList.map((e: any) => ({
              event_id: e.event_id,
              name: e.name || e.title || e.naam || 'Onbekend evenement',
            }))
          );
        }
      } catch (error) {
        console.error('Error fetching events for filter:', error);
      } finally {
        if (!cancelled) {
          setLoadingEvents(false);
        }
      }
    };

    fetchEvents();

    return () => {
      cancelled = true;
    };
  }, []);

  return { eventFilter, setEventFilter, events, loadingEvents };
}

export default useEventFilter;

/**
 * EventFilter Component
 *
 * Dropdown filter for selecting which event's data to display.
 *
 * Options:
 * - "Alle" — no filter, shows everything
 * - "Webshop" — filters to products where event_id is null
 * - Event names — fetched from GET /events, each filters to that event's event_id
 *
 * Validates: Requirements 10.5, 12.6, 12.10
 */

import React from 'react';
import { FormControl, FormLabel, Select, Spinner } from '@chakra-ui/react';
import { EventOption } from '../hooks/useEventFilter';

export interface EventFilterProps {
  /** Currently selected filter value */
  value: string;
  /** Callback when filter selection changes */
  onChange: (value: string) => void;
  /** Available events to display as options */
  events: EventOption[];
  /** Whether events are still loading */
  loading?: boolean;
  /** Optional label for the dropdown (defaults to "Filter") */
  label?: string;
}

export const EventFilter: React.FC<EventFilterProps> = ({
  value,
  onChange,
  events,
  loading = false,
  label = 'Filter',
}) => {
  return (
    <FormControl maxW="250px">
      <FormLabel fontSize="sm" fontWeight="medium" mb={1}>
        {label}
      </FormLabel>
      {loading ? (
        <Spinner size="sm" color="orange.400" />
      ) : (
        <Select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          size="sm"
        >
          <option value="">Alle</option>
          <option value="webshop">Webshop</option>
          {events.map((event) => (
            <option key={event.event_id} value={event.event_id}>
              {event.name}
            </option>
          ))}
        </Select>
      )}
    </FormControl>
  );
};

export default EventFilter;

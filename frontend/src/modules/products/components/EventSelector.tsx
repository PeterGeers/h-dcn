import React, { useState, useMemo } from 'react';
import {
  Box,
  Checkbox,
  Input,
  InputGroup,
  InputLeftElement,
  Spinner,
  Text,
  VStack,
} from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import { Event as HDCNEvent } from '../../../types';

// --- Types ---

export interface EventSelectorProps {
  /** Available events to choose from */
  events: HDCNEvent[];
  /** Currently selected event IDs */
  selectedIds: string[];
  /** Called with updated array of selected IDs */
  onChange: (ids: string[]) => void;
  /** Shows loading spinner when true */
  isLoading?: boolean;
  /** Disables all inputs when true */
  isDisabled?: boolean;
}

// --- Filter utility (exported for property testing) ---

/**
 * Filters events by case-insensitive substring match on the event name.
 * Returns events whose name contains the search string.
 */
export function filterEvents(events: HDCNEvent[], search: string): HDCNEvent[] {
  if (!search.trim()) return events;
  const lowerSearch = search.toLowerCase();
  return events.filter((event) => {
    const name = event.name || event.event_id || '';
    return name.toLowerCase().includes(lowerSearch);
  });
}

// --- Collapsed display utility (exported for property testing) ---

export interface EventTag {
  id: string;
  label: string;
}

/**
 * Returns an array of tag objects for the collapsed display of selected events.
 * Each tag has an id and label matching the event name (title || naam || event_id).
 * Only returns tags for selectedIds that exist in the events array.
 */
export function getSelectedEventTags(events: HDCNEvent[], selectedIds: string[]): EventTag[] {
  return selectedIds
    .map((id) => {
      const event = events.find((e) => (e.event_id || '') === id);
      if (!event) return null;
      const label = event.name || event.event_id || '';
      return { id, label };
    })
    .filter((tag): tag is EventTag => tag !== null);
}

// --- Component ---

export default function EventSelector({
  events,
  selectedIds,
  onChange,
  isLoading = false,
  isDisabled = false,
}: EventSelectorProps) {
  const [search, setSearch] = useState('');

  const filteredEvents = useMemo(
    () => filterEvents(events, search),
    [events, search]
  );

  const handleToggle = (eventId: string, checked: boolean) => {
    if (checked) {
      onChange([...selectedIds, eventId]);
    } else {
      onChange(selectedIds.filter((id) => id !== eventId));
    }
  };

  if (isLoading) {
    return (
      <Box py={4} textAlign="center">
        <Spinner size="sm" color="orange.400" />
        <Text fontSize="xs" color="gray.400" mt={2}>
          Events laden...
        </Text>
      </Box>
    );
  }

  return (
    <Box bg="gray.800" borderRadius="md" p={3}>
      {/* Search input */}
      <InputGroup size="sm" mb={2}>
        <InputLeftElement pointerEvents="none">
          <SearchIcon color="gray.400" />
        </InputLeftElement>
        <Input
          placeholder="Zoek evenement..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          bg="gray.700"
          borderColor="gray.600"
          color="white"
          _placeholder={{ color: 'gray.400' }}
          _focus={{ borderColor: 'orange.400' }}
          isDisabled={isDisabled}
        />
      </InputGroup>

      {/* Checkbox list */}
      <VStack
        align="stretch"
        spacing={1}
        maxH="200px"
        overflowY="auto"
        px={1}
      >
        {/* Filtered event list */}
        {filteredEvents.map((event) => {
          const id = event.event_id || '';
          const label = event.name || event.event_id || '';
          return (
            <Checkbox
              key={id}
              isChecked={selectedIds.includes(id)}
              onChange={(e) => handleToggle(id, e.target.checked)}
              colorScheme="orange"
              size="sm"
              isDisabled={isDisabled}
            >
              <Text fontSize="sm" color="white">
                {label}
              </Text>
            </Checkbox>
          );
        })}

        {filteredEvents.length === 0 && events.length > 0 && (
          <Text fontSize="xs" color="gray.500" py={2} textAlign="center">
            Geen evenementen gevonden
          </Text>
        )}
      </VStack>
    </Box>
  );
}

import React, { useState } from 'react';
import {
  Box,
  Button,
  Collapse,
  HStack,
  Tag,
  TagLabel,
  TagCloseButton,
  Text,
  useDisclosure,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronRightIcon, EditIcon } from '@chakra-ui/icons';
import { Event as HDCNEvent } from '../../../types';
import EventSelector from './EventSelector';

// --- Types ---

export interface EventSelectorSectionProps {
  /** Available events to choose from */
  events: HDCNEvent[];
  /** Currently selected event IDs */
  selectedIds: string[];
  /** Called with updated array of selected IDs */
  onChange: (ids: string[]) => void;
  /** Shows loading spinner inside EventSelector when true */
  isLoading?: boolean;
  /** Disables all inputs when true */
  isDisabled?: boolean;
}

// --- Utility (exported for property testing) ---

/**
 * Returns display names for selected event IDs.
 * Maps each selected ID to its event name from the events list.
 */
export function getSelectedEventNames(
  selectedIds: string[],
  events: HDCNEvent[]
): string[] {
  return selectedIds.map((id) => {
    const event = events.find((e) => e.event_id === id);
    if (event) return event.name || event.event_id || id;
    return id;
  });
}

// --- Component ---

/**
 * EventSelectorSection wraps the EventSelector in a CollapsibleSection.
 *
 * - Collapsed: Shows "Evenementen" title + selected event tags in header
 * - Expanded: Shows selected events as removable tags + a button to open the
 *   searchable checkbox dropdown for adding/removing events
 */
export default function EventSelectorSection({
  events,
  selectedIds,
  onChange,
  isLoading = false,
  isDisabled = false,
}: EventSelectorSectionProps) {
  const { isOpen, onToggle } = useDisclosure({ defaultIsOpen: false });
  const [showDropdown, setShowDropdown] = useState(false);

  const selectedNames = getSelectedEventNames(selectedIds, events);

  const handleRemoveEvent = (eventId: string) => {
    onChange(selectedIds.filter((id) => id !== eventId));
  };

  return (
    <Box w="100%" borderWidth="1px" borderColor="gray.400" borderRadius="md" overflow="hidden">
      {/* Collapsible header */}
      <Button
        w="100%"
        variant="ghost"
        justifyContent="space-between"
        onClick={onToggle}
        size="sm"
        rightIcon={isOpen ? <ChevronDownIcon /> : <ChevronRightIcon />}
        bg="gray.700"
        color="white"
        _hover={{ bg: 'gray.600' }}
        borderRadius="0"
        px={3}
      >
        <HStack spacing={2} flex="1" overflow="hidden" align="center">
          <Text fontSize="sm" fontWeight="medium" flexShrink={0}>
            Evenementen
          </Text>
          {!isOpen && (
            selectedNames.length > 0 ? (
              <Wrap spacing={1} overflow="hidden" flex="1">
                {selectedNames.map((name, idx) => (
                  <WrapItem key={idx}>
                    <Tag size="sm" colorScheme="orange" variant="subtle">
                      <TagLabel fontSize="xs">{name}</TagLabel>
                    </Tag>
                  </WrapItem>
                ))}
              </Wrap>
            ) : (
              <Text fontSize="xs" color="gray.400" fontWeight="normal">
                Geen evenementen geselecteerd
              </Text>
            )
          )}
        </HStack>
      </Button>

      {/* Expanded content */}
      <Collapse in={isOpen}>
        <Box p={3} bg="gray.800">
          {/* Selected events as removable tags */}
          {selectedNames.length > 0 ? (
            <Wrap spacing={2} mb={3}>
              {selectedIds.map((id, idx) => (
                <WrapItem key={id}>
                  <Tag size="md" colorScheme="orange" variant="solid" borderRadius="full">
                    <TagLabel>{selectedNames[idx]}</TagLabel>
                    {!isDisabled && (
                      <TagCloseButton onClick={() => handleRemoveEvent(id)} />
                    )}
                  </Tag>
                </WrapItem>
              ))}
            </Wrap>
          ) : (
            <Text fontSize="sm" color="gray.400" mb={3}>
              Geen evenementen geselecteerd
            </Text>
          )}

          {/* Button to open the dropdown */}
          {!showDropdown ? (
            <Button
              size="sm"
              leftIcon={<EditIcon />}
              colorScheme="orange"
              variant="outline"
              onClick={() => setShowDropdown(true)}
              isDisabled={isDisabled}
            >
              Evenementen bewerken
            </Button>
          ) : (
            <Box>
              <EventSelector
                events={events}
                selectedIds={selectedIds}
                onChange={onChange}
                isLoading={isLoading}
                isDisabled={isDisabled}
              />
              <Button
                size="xs"
                mt={2}
                variant="ghost"
                color="gray.400"
                onClick={() => setShowDropdown(false)}
              >
                Sluiten
              </Button>
            </Box>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}

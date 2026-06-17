import React from 'react';
import {
  Box,
  Button,
  Collapse,
  HStack,
  Tag,
  TagLabel,
  Text,
  useDisclosure,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronRightIcon } from '@chakra-ui/icons';
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

// --- Constants ---

const WEBSHOP_EVENT_ID = 'evt-webshop';
const WEBSHOP_EVENT_LABEL = 'Webshop (algemeen)';

// --- Utility (exported for property testing) ---

/**
 * Returns display names for selected event IDs.
 * Maps each selected ID to its event name. The special "evt-webshop" ID maps to "Webshop (algemeen)".
 */
export function getSelectedEventNames(
  selectedIds: string[],
  events: HDCNEvent[]
): string[] {
  return selectedIds.map((id) => {
    if (id === WEBSHOP_EVENT_ID) return WEBSHOP_EVENT_LABEL;
    const event = events.find((e) => e.event_id === id);
    if (event) return event.title || event.naam || event.event_id || id;
    return id;
  });
}

// --- Component ---

/**
 * EventSelectorSection wraps the EventSelector in a CollapsibleSection
 * with badges/tags in the header showing selected events when collapsed.
 *
 * - Collapsed: Shows "Evenementen" title + selected event tags (or placeholder)
 * - Expanded: Shows full searchable EventSelector
 *
 * Uses same expand/collapse animation and styling as OrderItemFieldsEditor/PurchaseRulesEditor sections.
 */
export default function EventSelectorSection({
  events,
  selectedIds,
  onChange,
  isLoading = false,
  isDisabled = false,
}: EventSelectorSectionProps) {
  const { isOpen, onToggle } = useDisclosure({
    defaultIsOpen: selectedIds.length > 0,
  });

  const selectedNames = getSelectedEventNames(selectedIds, events);

  return (
    <Box w="100%" borderWidth="1px" borderColor="gray.400" borderRadius="md" overflow="hidden">
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
      <Collapse in={isOpen}>
        <Box p={3} bg="gray.800">
          <EventSelector
            events={events}
            selectedIds={selectedIds}
            onChange={onChange}
            isLoading={isLoading}
            isDisabled={isDisabled}
          />
        </Box>
      </Collapse>
    </Box>
  );
}

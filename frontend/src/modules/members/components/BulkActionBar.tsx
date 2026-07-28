/**
 * BulkActionBar Component
 *
 * Sticky bar displayed above the MemberAdminTable when one or more members
 * are selected. Shows the count, a dropdown of available transitions
 * (intersection of valid events for all selected members), and an Execute button.
 *
 * Validates: Requirements 2.2, 2.3
 */

import React, { useMemo, useState } from 'react';
import {
  Box,
  HStack,
  Text,
  Button,
  Select,
  IconButton,
  Flex,
  Spacer,
} from '@chakra-ui/react';
import { CloseIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { membershipWorkflow, STATUS_TO_STATE } from '../../../config/workflows/membershipWorkflow';
import type { MemberWorkflowState, TransitionConfig } from '../../../config/workflows/types';

// ============================================================================
// TYPES
// ============================================================================

export interface BulkActionBarProps {
  /** Full member objects for selected members (need status for computing transitions) */
  selectedMembers: Array<{ member_id: string; status?: string; [key: string]: any }>;
  /** Current user's roles */
  userRoles: string[];
  /** Callback when Execute is clicked with the event and selected member IDs */
  onExecute: (event: string, memberIds: string[]) => void;
  /** Callback to clear selection */
  onClearSelection: () => void;
  /** Whether a bulk action is currently in progress */
  isLoading?: boolean;
}

// ============================================================================
// COMPONENT
// ============================================================================

const BulkActionBar: React.FC<BulkActionBarProps> = ({
  selectedMembers,
  userRoles,
  onExecute,
  onClearSelection,
  isLoading = false,
}) => {
  const { t } = useTranslation('workflows');
  const [selectedEvent, setSelectedEvent] = useState<string>('');

  // Compute available transitions for all selected members
  const { availableTransitions, hasMixedStatuses } = useMemo(() => {
    if (selectedMembers.length === 0) {
      return { availableTransitions: [] as TransitionConfig[], hasMixedStatuses: false };
    }

    // Get unique statuses
    const statuses = new Set(selectedMembers.map((m) => m.status).filter(Boolean));

    // If members have different statuses, no common transitions
    if (statuses.size > 1) {
      return { availableTransitions: [] as TransitionConfig[], hasMixedStatuses: true };
    }

    const status = selectedMembers[0]?.status;
    if (!status) {
      return { availableTransitions: [] as TransitionConfig[], hasMixedStatuses: false };
    }

    // Map DynamoDB status to workflow state
    const state: MemberWorkflowState | undefined = STATUS_TO_STATE[status];
    if (!state) {
      return { availableTransitions: [] as TransitionConfig[], hasMixedStatuses: false };
    }

    // Get transitions for this state
    const stateConfig = membershipWorkflow.states[state];
    if (!stateConfig) {
      return { availableTransitions: [] as TransitionConfig[], hasMixedStatuses: false };
    }

    // Filter by user role
    const roleFiltered = stateConfig.transitions.filter((tr) =>
      tr.actors.some((actor) => userRoles.includes(actor))
    );

    return { availableTransitions: roleFiltered, hasMixedStatuses: false };
  }, [selectedMembers, userRoles]);

  const handleExecute = () => {
    if (selectedEvent) {
      const memberIds = selectedMembers.map((m) => m.member_id);
      onExecute(selectedEvent, memberIds);
      setSelectedEvent('');
    }
  };

  return (
    <Box
      bg="blue.700"
      borderRadius="md"
      px={4}
      py={3}
      position="sticky"
      top={0}
      zIndex={10}
    >
      <Flex align="center" wrap="wrap" gap={3}>
        {/* Selection count */}
        <HStack spacing={2}>
          <IconButton
            aria-label="Clear selection"
            icon={<CloseIcon />}
            size="xs"
            variant="ghost"
            color="white"
            _hover={{ bg: 'blue.600' }}
            onClick={onClearSelection}
          />
          <Text color="white" fontWeight="semibold" fontSize="sm">
            {t('membership.bulk.selected', { count: selectedMembers.length })}
          </Text>
        </HStack>

        <Spacer />

        {/* Action dropdown + execute */}
        <HStack spacing={2}>
          {hasMixedStatuses ? (
            <Text color="yellow.200" fontSize="sm">
              {t('membership.bulk.selectSameStatus', {
                defaultValue: 'Select members with the same status',
              })}
            </Text>
          ) : (
            <>
              <Select
                size="sm"
                bg="white"
                color="black"
                maxW="200px"
                value={selectedEvent}
                onChange={(e) => setSelectedEvent(e.target.value)}
                placeholder={t('membership.bulk.title', { defaultValue: 'Select action' })}
                isDisabled={availableTransitions.length === 0 || isLoading}
              >
                {availableTransitions.map((tr) => (
                  <option key={tr.event} value={tr.event}>
                    {t(`membership.${tr.event.toLowerCase()}`, {
                      defaultValue: tr.event,
                    })}
                  </option>
                ))}
              </Select>
              <Button
                size="sm"
                colorScheme="green"
                onClick={handleExecute}
                isDisabled={!selectedEvent || isLoading}
                isLoading={isLoading}
              >
                {t('membership.bulk.execute', { defaultValue: 'Execute' })}
              </Button>
            </>
          )}
        </HStack>
      </Flex>
    </Box>
  );
};

export default BulkActionBar;

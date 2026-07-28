/**
 * MemberWorkflowPanel
 *
 * Displays the current workflow status as a colored badge and renders
 * action buttons for valid transitions filtered by the user's Cognito roles.
 * Buttons are disabled (with tooltip) when required fields on the member
 * record are missing (e.g. regio not set). Clicking a button opens
 * TransitionConfirmDialog (task 6.2).
 *
 * Validates: Requirements 1.1, 1.4
 */

import React, { useMemo, useState, useCallback } from 'react';
import {
  Badge,
  Box,
  Button,
  HStack,
  Tooltip,
  VStack,
  Text,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { Member } from '../../../types';
import {
  STATUS_TO_STATE,
  membershipWorkflow,
} from '../../../config/workflows';
import type { MemberWorkflowState, TransitionConfig } from '../../../config/workflows';
import TransitionConfirmDialog from './TransitionConfirmDialog';
import { useMemberTransition } from '../hooks/useMemberTransition';

// ============================================================================
// TYPES
// ============================================================================

interface MemberWorkflowPanelProps {
  /** The member record (with status, regio, etc.) */
  member: Member;
  /** Current user's Cognito role strings */
  userRoles: string[];
  /** Callback after a successful transition (to refresh member data) */
  onTransitionComplete: () => void;
}

// ============================================================================
// BADGE COLOR SCHEME
// ============================================================================

const STATE_COLOR_SCHEME: Record<MemberWorkflowState, string> = {
  draft: 'gray',
  applied: 'blue',
  pending: 'orange',
  wait_payment: 'yellow',
  active: 'green',
  cancelled: 'red',
  suspended: 'purple',
};

// ============================================================================
// HELPERS
// ============================================================================

/** Build display name from member fields */
function getMemberDisplayName(member: Member): string {
  const parts: string[] = [];
  if (member.voornaam) parts.push(member.voornaam);
  if (member.tussenvoegsel) parts.push(member.tussenvoegsel);
  if (member.achternaam) parts.push(member.achternaam);
  if (parts.length > 0) return parts.join(' ');
  return member.name || member.email || '';
}

// ============================================================================
// COMPONENT
// ============================================================================

function MemberWorkflowPanel({
  member,
  userRoles,
  onTransitionComplete,
}: MemberWorkflowPanelProps) {
  const { t } = useTranslation('workflows');

  // State for the confirmation dialog
  const [selectedTransition, setSelectedTransition] = useState<TransitionConfig | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Transition hook
  const memberId = member.member_id || member.id;
  const { mutate, isLoading } = useMemberTransition(memberId, {
    onSuccess: () => {
      setIsDialogOpen(false);
      setSelectedTransition(null);
      onTransitionComplete();
    },
  });

  // Map the member's DynamoDB status to a workflow state
  const currentState: MemberWorkflowState | null = useMemo(() => {
    if (!member.status) return null;
    return STATUS_TO_STATE[member.status] ?? null;
  }, [member.status]);

  // Get available transitions for the current state, filtered by user roles
  const availableTransitions = useMemo(() => {
    if (!currentState) return [];
    const stateConfig = membershipWorkflow.states[currentState];
    if (!stateConfig) return [];

    // Filter by user roles: user must have at least one role in transition.actors
    return stateConfig.transitions.filter((transition) =>
      transition.actors.some((actor) => userRoles.includes(actor))
    );
  }, [currentState, userRoles]);

  /**
   * Determine if a transition button should be disabled.
   * Checks if required fields (that must already exist on the member) are present.
   * Returns null if enabled, or a tooltip message if disabled.
   *
   * Note: 'reason' is collected in the confirmation dialog, not checked here.
   */
  const getDisabledReason = useCallback(
    (transition: TransitionConfig): string | null => {
      if (!transition.requiredFields || transition.requiredFields.length === 0) {
        return null;
      }

      for (const field of transition.requiredFields) {
        // 'reason' is provided at confirm time via the dialog — skip
        if (field === 'reason') continue;

        const value = (member as unknown as Record<string, unknown>)[field];
        if (value === undefined || value === null || value === '') {
          if (field === 'regio') {
            return t('membership.errors.regionRequired');
          }
          // Generic fallback for other required fields
          return t('membership.errors.regionRequired');
        }
      }
      return null;
    },
    [member, t]
  );

  const handleTransitionClick = (transition: TransitionConfig) => {
    setSelectedTransition(transition);
    setIsDialogOpen(true);
  };

  const handleDialogClose = () => {
    if (!isLoading) {
      setIsDialogOpen(false);
      setSelectedTransition(null);
    }
  };

  const handleConfirm = useCallback(
    (context: Record<string, string>) => {
      if (!selectedTransition) return;
      mutate(selectedTransition.event, context);
    },
    [selectedTransition, mutate]
  );

  // If status is not in the workflow (e.g., HdcnAccount, Club), show grey badge
  if (!currentState) {
    return (
      <Box>
        <HStack spacing={3} align="center">
          <Text fontSize="sm" fontWeight="medium" color="gray.600">
            Status:
          </Text>
          <Badge colorScheme="gray" fontSize="sm" px={2} py={1} borderRadius="md">
            {member.status || t('membership.errors.notInWorkflow')}
          </Badge>
        </HStack>
        <Text fontSize="xs" color="gray.500" mt={1}>
          {t('membership.errors.notInWorkflow')}
        </Text>
      </Box>
    );
  }

  const colorScheme = STATE_COLOR_SCHEME[currentState];
  const memberName = getMemberDisplayName(member);

  return (
    <VStack align="stretch" spacing={3}>
      {/* Current status badge */}
      <HStack spacing={3} align="center">
        <Text fontSize="sm" fontWeight="medium" color="gray.600">
          Status:
        </Text>
        <Badge
          colorScheme={colorScheme}
          fontSize="sm"
          px={2}
          py={1}
          borderRadius="md"
        >
          {t(`membership.status.${currentState}`)}
        </Badge>
      </HStack>

      {/* Action buttons */}
      {availableTransitions.length > 0 && (
        <HStack spacing={2} flexWrap="wrap">
          {availableTransitions.map((transition) => {
            const disabledReason = getDisabledReason(transition);
            const isDisabled = disabledReason !== null;

            const button = (
              <Button
                key={transition.event}
                size="sm"
                colorScheme="blue"
                variant="outline"
                isDisabled={isDisabled}
                onClick={() => handleTransitionClick(transition)}
              >
                {t(`membership.${transition.label.replace('workflows.membership.', '')}`)}
              </Button>
            );

            if (isDisabled) {
              return (
                <Tooltip
                  key={transition.event}
                  label={disabledReason}
                  hasArrow
                >
                  {/* Wrap in Box so tooltip works on disabled button */}
                  <Box display="inline-block">
                    {button}
                  </Box>
                </Tooltip>
              );
            }

            return button;
          })}
        </HStack>
      )}

      {/* Confirmation dialog */}
      {selectedTransition && (
        <TransitionConfirmDialog
          isOpen={isDialogOpen}
          onClose={handleDialogClose}
          transition={selectedTransition}
          memberName={memberName}
          isLoading={isLoading}
          onConfirm={handleConfirm}
        />
      )}
    </VStack>
  );
}

export default MemberWorkflowPanel;

/**
 * MemberWorkflowTimeline
 *
 * Vertical timeline component that renders a member's status_history array.
 * Each entry shows the from→to status transition, the event name, date/time,
 * and who triggered it. Entries are displayed in reverse chronological order
 * (most recent first).
 *
 * Validates: Requirements 7.2
 */

import {
  Badge,
  Box,
  HStack,
  Text,
  VStack,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import type { MemberWorkflowState } from '../../../config/workflows';
import { STATUS_TO_STATE } from '../../../config/workflows';

// ============================================================================
// TYPES
// ============================================================================

/** A single entry in the member's status_history array (from DynamoDB). */
export interface MemberStatusHistoryEntry {
  from: string;
  to: string;
  event: string;
  at: string;
  by: string;
}

interface MemberWorkflowTimelineProps {
  /** The status_history array from the member record */
  statusHistory?: MemberStatusHistoryEntry[];
}

// ============================================================================
// COLOR MAPPING
// ============================================================================

/** Color scheme for each workflow state badge */
const STATE_COLOR_SCHEME: Record<MemberWorkflowState, string> = {
  draft: 'gray',
  applied: 'blue',
  pending: 'orange',
  wait_payment: 'yellow',
  active: 'green',
  cancelled: 'red',
  suspended: 'purple',
  rejected: 'red',
};

/**
 * Get the Chakra color scheme for a DynamoDB status value.
 * Falls back to 'gray' if the status is not in the workflow.
 */
function getStatusColorScheme(status: string): string {
  const state = STATUS_TO_STATE[status];
  if (state && state in STATE_COLOR_SCHEME) {
    return STATE_COLOR_SCHEME[state as MemberWorkflowState];
  }
  return 'gray';
}

// ============================================================================
// DATE FORMATTING
// ============================================================================

/**
 * Format an ISO date string to a readable locale date/time.
 * Example: "24 jul 2026 14:30"
 */
function formatDateTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    return date.toLocaleString('nl-NL', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

// ============================================================================
// COMPONENT
// ============================================================================

function MemberWorkflowTimeline({ statusHistory }: MemberWorkflowTimelineProps) {
  const { t } = useTranslation('workflows');

  // Empty state
  if (!statusHistory || statusHistory.length === 0) {
    return (
      <Box py={3}>
        <Text fontSize="sm" color="gray.500">
          {t('membership.timeline.empty')}
        </Text>
      </Box>
    );
  }

  // Sort entries in reverse chronological order (most recent first)
  const sortedEntries = [...statusHistory].sort((a, b) => {
    const dateA = new Date(a.at).getTime();
    const dateB = new Date(b.at).getTime();
    // If dates can't be parsed, keep original order
    if (isNaN(dateA) || isNaN(dateB)) return 0;
    return dateB - dateA;
  });

  return (
    <VStack align="stretch" spacing={0} position="relative">
      {sortedEntries.map((entry, index) => {
        const isLast = index === sortedEntries.length - 1;
        const fromColor = getStatusColorScheme(entry.from);
        const toColor = getStatusColorScheme(entry.to);

        return (
          <HStack
            key={`${entry.at}-${index}`}
            spacing={3}
            align="flex-start"
            position="relative"
            pb={isLast ? 0 : 4}
          >
            {/* Timeline line + dot */}
            <Box
              position="relative"
              display="flex"
              flexDirection="column"
              alignItems="center"
              minW="20px"
            >
              <Box
                w={3}
                h={3}
                borderRadius="full"
                bg={`${toColor}.400`}
                mt={1}
                flexShrink={0}
              />
              {!isLast && (
                <Box
                  position="absolute"
                  top="14px"
                  left="50%"
                  transform="translateX(-50%)"
                  width="2px"
                  bottom={0}
                  bg="gray.200"
                />
              )}
            </Box>

            {/* Entry content */}
            <Box flex={1} pb={isLast ? 0 : 2}>
              {/* From → To badges */}
              <HStack spacing={1} flexWrap="wrap" mb={1}>
                <Badge
                  colorScheme={fromColor}
                  fontSize="xs"
                  px={1.5}
                  borderRadius="sm"
                >
                  {entry.from}
                </Badge>
                <Text fontSize="xs" color="gray.400">→</Text>
                <Badge
                  colorScheme={toColor}
                  fontSize="xs"
                  px={1.5}
                  borderRadius="sm"
                >
                  {entry.to}
                </Badge>
                <Badge
                  variant="outline"
                  colorScheme="gray"
                  fontSize="xs"
                  px={1.5}
                  borderRadius="sm"
                  ml={1}
                >
                  {entry.event}
                </Badge>
              </HStack>

              {/* Date + triggered by */}
              <HStack spacing={2} fontSize="xs" color="gray.500">
                <Text>{formatDateTime(entry.at)}</Text>
                <Text>•</Text>
                <Text>{entry.by}</Text>
              </HStack>
            </Box>
          </HStack>
        );
      })}
    </VStack>
  );
}

export default MemberWorkflowTimeline;

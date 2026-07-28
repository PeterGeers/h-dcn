/**
 * BulkResultSummary
 *
 * Modal showing success/failure per member after bulk transition execution.
 * Displays a summary ("X of Y members successfully processed") at the top,
 * followed by a list showing each member's result — green checkmark for success
 * with new status, red X for failure with name + error reason.
 *
 * Validates: Requirements 2.4, 2.5
 */

import React from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Button,
  Text,
  HStack,
  VStack,
  Icon,
  Badge,
  Divider,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { STATUS_TO_STATE } from '../../../config/workflows';
import type { BulkTransitionResponse } from '../hooks/useBulkTransition';

// ============================================================================
// TYPES
// ============================================================================

export interface BulkResultSummaryProps {
  /** Whether the modal is visible */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** The bulk transition response containing results array, total, succeeded, failed */
  result: BulkTransitionResponse;
  /** Map of member_id → display name for showing readable names in results */
  memberNames: Record<string, string>;
}

// ============================================================================
// COMPONENT
// ============================================================================

export const BulkResultSummary: React.FC<BulkResultSummaryProps> = ({
  isOpen,
  onClose,
  result,
  memberNames,
}) => {
  const { t } = useTranslation(['workflows', 'common']);

  const { total, succeeded, failed, results } = result;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg" isCentered scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent bg="gray.800" borderColor="orange.400" borderWidth="1px">
        <ModalHeader color="orange.300">
          {t('workflows:membership.bulk.title')}
        </ModalHeader>
        <ModalCloseButton color="gray.400" />

        <ModalBody>
          <VStack align="stretch" spacing={4}>
            {/* Summary text */}
            <Text color="white" fontWeight="bold" fontSize="md">
              {t('workflows:membership.bulk.result', { succeeded, total })}
            </Text>

            {failed > 0 && (
              <Text color="red.300" fontSize="sm">
                {t('workflows:membership.bulk.failed', { failed })}
              </Text>
            )}

            <Divider borderColor="gray.600" />

            {/* Per-member results */}
            <VStack align="stretch" spacing={2} maxH="300px" overflowY="auto">
              {results.map((item) => (
                <HStack
                  key={item.member_id}
                  spacing={3}
                  p={2}
                  borderRadius="md"
                  bg={item.success ? 'green.900' : 'red.900'}
                  opacity={0.9}
                >
                  <Icon
                    as={item.success ? CheckCircleIcon : WarningIcon}
                    color={item.success ? 'green.300' : 'red.300'}
                    boxSize={4}
                  />
                  <VStack align="start" spacing={0} flex={1}>
                    <HStack spacing={2}>
                      <Text color="white" fontSize="sm" fontWeight="medium">
                        {memberNames[item.member_id] || item.member_id}
                      </Text>
                      {item.success && item.new_status && (
                        <Badge
                          colorScheme="green"
                          fontSize="xs"
                          variant="subtle"
                        >
                          {STATUS_TO_STATE[item.new_status]
                            ? t(`workflows:membership.status.${STATUS_TO_STATE[item.new_status]}`)
                            : item.new_status}
                        </Badge>
                      )}
                    </HStack>
                    {!item.success && item.error && (
                      <Text color="red.200" fontSize="xs">
                        {item.error}
                      </Text>
                    )}
                  </VStack>
                </HStack>
              ))}
            </VStack>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button colorScheme="orange" onClick={onClose}>
            {t('common:buttons.close')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default BulkResultSummary;

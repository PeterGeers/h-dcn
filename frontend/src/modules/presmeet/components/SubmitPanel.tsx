/**
 * SubmitPanel — Submit button with client-side validation and server error display.
 *
 * Performs client-side required field validation before calling the submit API.
 * Displays inline validation errors (both client-side and server-returned).
 * On success, updates the parent UI state.
 *
 * Validates: Requirements 11.8, 11.9
 */

import React from 'react';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  List,
  ListIcon,
  ListItem,
  Text,
  VStack,
} from '@chakra-ui/react';
import { CheckIcon, WarningIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { OrderStatus } from '../types/presmeet.types';

export interface SubmitPanelProps {
  /** Current order status */
  orderStatus: OrderStatus;
  /** Whether a submit is currently in progress */
  isSubmitting: boolean;
  /** Whether there are validation errors blocking submission */
  hasErrors: boolean;
  /** General submit error message (e.g., server-side failure message) */
  submitError: string | null;
  /** Server validation errors grouped by item/field */
  serverErrors: Array<{ item_index: number; field: string; message: string }>;
  /** Callback to trigger submit */
  onSubmit: () => void;
  /** Whether the form is disabled (locked, saving, etc.) */
  isDisabled?: boolean;
}

const SubmitPanel: React.FC<SubmitPanelProps> = ({
  orderStatus,
  isSubmitting,
  hasErrors,
  submitError,
  serverErrors,
  onSubmit,
  isDisabled = false,
}) => {
  const { t } = useTranslation('eventBooking');
  const isSubmitted = orderStatus === 'submitted';

  return (
    <VStack spacing={3} align="stretch">
      {/* Success state */}
      {isSubmitted && !submitError && serverErrors.length === 0 && (
        <Alert status="success" borderRadius="md">
          <AlertIcon />
          <AlertDescription>
            {t('submit.success')}
          </AlertDescription>
        </Alert>
      )}

      {/* General submit error */}
      {submitError && (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertDescription>{submitError}</AlertDescription>
          </Box>
        </Alert>
      )}

      {/* Server validation errors */}
      {serverErrors.length > 0 && (
        <Alert status="warning" borderRadius="md" flexDirection="column" alignItems="flex-start">
          <Box display="flex" alignItems="center" mb={2}>
            <AlertIcon />
            <Text fontWeight="semibold" fontSize="sm">
              {t('submit.failed')}
            </Text>
          </Box>
          <List spacing={1} pl={6} fontSize="sm">
            {serverErrors.map((err, idx) => (
              <ListItem key={idx}>
                <ListIcon as={WarningIcon} color="orange.500" />
                <Text as="span" fontWeight="medium">
                  {t('submit.person_field', { index: err.item_index + 1, field: err.field })}
                </Text>{' '}
                {err.message}
              </ListItem>
            ))}
          </List>
        </Alert>
      )}

      {/* Submit button */}
      <Button
        colorScheme={isSubmitted ? 'green' : 'orange'}
        size="md"
        onClick={onSubmit}
        isLoading={isSubmitting}
        isDisabled={isDisabled || isSubmitting}
        leftIcon={isSubmitted ? <CheckIcon /> : undefined}
        width="full"
      >
        {isSubmitted ? t('submit.button_resubmit') : t('submit.button')}
      </Button>

      {hasErrors && (
        <Text fontSize="xs" color="red.500" textAlign="center">
          {t('submit.fix_fields')}
        </Text>
      )}
    </VStack>
  );
};

export default SubmitPanel;

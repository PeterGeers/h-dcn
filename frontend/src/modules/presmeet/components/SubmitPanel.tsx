/**
 * SubmitPanel — Submit button with validation display and confirmation view.
 *
 * - Calls backend submit endpoint via onSubmit callback
 * - Displays validation errors grouped per person (scrolls to first error)
 * - Transitions to confirmation view on success with payment option
 * - Handles capacity exceeded errors showing current remaining
 *
 * Validates: Requirements 9.7, 9.8, 9.9
 */

import React, { useRef, useEffect } from 'react';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  Heading,
  List,
  ListIcon,
  ListItem,
  Text,
  VStack,
} from '@chakra-ui/react';
import { CheckIcon, WarningIcon, WarningTwoIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { Order, OrderStatus, ValidationError } from '../types/presmeet.types';
import PaymentPanel from './PaymentPanel';

// --- Types ---

/** Errors grouped by person_index (null key for order-level errors) */
export interface GroupedErrors {
  /** Order-level errors (e.g., capacity exceeded) */
  orderLevel: ValidationError[];
  /** Errors grouped by person index */
  byPerson: Record<number, ValidationError[]>;
}

export interface SubmitPanelProps {
  /** The full order object (needed for confirmation/payment view) */
  order: Order;
  /** Current order status */
  orderStatus: OrderStatus;
  /** Whether a submit is currently in progress */
  isSubmitting: boolean;
  /** Whether there are client-side validation errors blocking submission */
  hasErrors: boolean;
  /** General submit error message (e.g., server-side failure message) */
  submitError: string | null;
  /** Server validation errors (flat list from backend) */
  serverErrors: ValidationError[];
  /** Callback to trigger submit */
  onSubmit: () => void;
  /** Whether the form is disabled (locked, saving, etc.) */
  isDisabled?: boolean;
  /** Whether to show the confirmation view (order just submitted) */
  showConfirmation?: boolean;
}

// --- Helpers ---

/**
 * Group validation errors by person_index.
 * Errors with person_index === null go into orderLevel (capacity, etc.)
 */
function groupErrorsByPerson(errors: ValidationError[]): GroupedErrors {
  const result: GroupedErrors = { orderLevel: [], byPerson: {} };

  for (const err of errors) {
    if (err.person_index === null || err.person_index === undefined) {
      result.orderLevel.push(err);
    } else {
      if (!result.byPerson[err.person_index]) {
        result.byPerson[err.person_index] = [];
      }
      result.byPerson[err.person_index].push(err);
    }
  }

  return result;
}

// --- Component ---

const SubmitPanel: React.FC<SubmitPanelProps> = ({
  order,
  orderStatus,
  isSubmitting,
  hasErrors,
  submitError,
  serverErrors,
  onSubmit,
  isDisabled = false,
  showConfirmation = false,
}) => {
  const { t } = useTranslation('eventBooking');
  const errorContainerRef = useRef<HTMLDivElement>(null);
  const isSubmitted = orderStatus === 'submitted';

  // Scroll to first error when server errors appear
  useEffect(() => {
    if (serverErrors.length > 0 && errorContainerRef.current) {
      errorContainerRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  }, [serverErrors]);

  const grouped = groupErrorsByPerson(serverErrors);
  const personIndices = Object.keys(grouped.byPerson)
    .map(Number)
    .sort((a, b) => a - b);

  // --- Confirmation view (after successful submission) ---
  if (showConfirmation && isSubmitted) {
    return (
      <VStack spacing={5} align="stretch">
        <Alert status="success" borderRadius="md">
          <AlertIcon />
          <Box>
            <Text fontWeight="semibold">{t('submit.confirmation_title')}</Text>
            <AlertDescription>{t('submit.confirmation_message')}</AlertDescription>
          </Box>
        </Alert>

        {/* Payment panel */}
        <PaymentPanel order={order} />
      </VStack>
    );
  }

  // --- Standard submit view ---
  return (
    <VStack spacing={3} align="stretch" ref={errorContainerRef}>
      {/* Success state (brief) */}
      {isSubmitted && !submitError && serverErrors.length === 0 && !showConfirmation && (
        <Alert status="success" borderRadius="md">
          <AlertIcon />
          <AlertDescription>{t('submit.success')}</AlertDescription>
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

      {/* Order-level errors (capacity exceeded, etc.) */}
      {grouped.orderLevel.length > 0 && (
        <Alert status="error" borderRadius="md" flexDirection="column" alignItems="flex-start">
          <Box display="flex" alignItems="center" mb={2}>
            <AlertIcon />
            <Text fontWeight="semibold" fontSize="sm">
              {t('submit.capacity_errors_title')}
            </Text>
          </Box>
          <List spacing={2} pl={6} fontSize="sm">
            {grouped.orderLevel.map((err, idx) => (
              <ListItem key={`order-${idx}`}>
                <ListIcon as={WarningTwoIcon} color="red.500" />
                <Text as="span">{err.message}</Text>
                {err.field === 'max_per_event' && err.remaining !== undefined && (
                  <Text as="span" fontWeight="bold" color="red.600" ml={1}>
                    ({t('submit.remaining_capacity', { count: err.remaining })})
                  </Text>
                )}
              </ListItem>
            ))}
          </List>
        </Alert>
      )}

      {/* Per-person validation errors */}
      {personIndices.length > 0 && (
        <Alert
          status="warning"
          borderRadius="md"
          flexDirection="column"
          alignItems="flex-start"
        >
          <Box display="flex" alignItems="center" mb={2}>
            <AlertIcon />
            <Text fontWeight="semibold" fontSize="sm">
              {t('submit.failed')}
            </Text>
          </Box>

          <VStack spacing={3} align="stretch" width="full" pl={6}>
            {personIndices.map((personIdx) => (
              <Box key={personIdx}>
                <Heading size="xs" mb={1} color="orange.700">
                  {t('submit.person_header', { index: personIdx + 1 })}
                </Heading>
                <List spacing={1} fontSize="sm">
                  {grouped.byPerson[personIdx].map((err, idx) => (
                    <ListItem key={idx}>
                      <ListIcon as={WarningIcon} color="orange.500" />
                      <Text as="span">{err.message}</Text>
                    </ListItem>
                  ))}
                </List>
              </Box>
            ))}
          </VStack>
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

/**
 * TransitionConfirmDialog
 *
 * Confirmation modal for workflow transitions. Shows action description,
 * consequence text, optional required input fields (reason textarea),
 * Confirm/Cancel buttons, and loading state during API call.
 *
 * Uses Chakra UI v2 AlertDialog pattern for confirm/cancel flow.
 *
 * Validates: Requirements 1.3, 1.4
 */

import { useRef, useState, useCallback } from 'react';
import {
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  Button,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Text,
  Textarea,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import type { TransitionConfig } from '../../../config/workflows/types';

// ============================================================================
// TYPES
// ============================================================================

interface TransitionConfirmDialogProps {
  /** Whether the dialog is visible */
  isOpen: boolean;
  /** Callback to close the dialog */
  onClose: () => void;
  /** The transition config describing the action */
  transition: TransitionConfig;
  /** Member name for display in the dialog */
  memberName: string;
  /** Whether the API call is in progress */
  isLoading: boolean;
  /** Callback when the user confirms — receives context with any required fields */
  onConfirm: (context: Record<string, string>) => void;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const REASON_MIN_LENGTH = 10;

// ============================================================================
// COMPONENT
// ============================================================================

export const TransitionConfirmDialog: React.FC<TransitionConfirmDialogProps> = ({
  isOpen,
  onClose,
  transition,
  memberName,
  isLoading,
  onConfirm,
}) => {
  const { t } = useTranslation(['workflows', 'common']);
  const cancelRef = useRef<HTMLButtonElement>(null);

  const [reason, setReason] = useState('');
  const [reasonTouched, setReasonTouched] = useState(false);

  const requiresReason = transition.requiredFields?.includes('reason') ?? false;
  const isReasonOptional = transition.event === 'CANCEL';

  // Validation: reason required for SUSPEND (min 10 chars), optional for CANCEL (min 10 if provided)
  const reasonError = (() => {
    if (!requiresReason && !isReasonOptional) return '';
    if (requiresReason && reason.trim().length < REASON_MIN_LENGTH) {
      return t('workflows:membership.errors.reasonRequired');
    }
    if (isReasonOptional && reason.trim().length > 0 && reason.trim().length < REASON_MIN_LENGTH) {
      return t('workflows:membership.errors.reasonRequired');
    }
    return '';
  })();

  const showReasonField = requiresReason || isReasonOptional;

  // Confirm button is disabled when loading or when required validation is not met
  const isConfirmDisabled = isLoading || (requiresReason && reason.trim().length < REASON_MIN_LENGTH);

  const handleConfirm = useCallback(() => {
    const context: Record<string, string> = {};
    if (showReasonField && reason.trim().length > 0) {
      context.reason = reason.trim();
    }
    onConfirm(context);
  }, [onConfirm, reason, showReasonField]);

  const handleClose = useCallback(() => {
    if (!isLoading) {
      setReason('');
      setReasonTouched(false);
      onClose();
    }
  }, [isLoading, onClose]);

  return (
    <AlertDialog
      isOpen={isOpen}
      leastDestructiveRef={cancelRef}
      onClose={handleClose}
      isCentered
    >
      <AlertDialogOverlay>
        <AlertDialogContent bg="gray.800" borderColor="orange.400" borderWidth="1px">
          <AlertDialogHeader fontSize="lg" fontWeight="bold" color="orange.300">
            {t(transition.label)} — {memberName}
          </AlertDialogHeader>

          <AlertDialogBody>
            {/* Confirmation message */}
            <Text color="white" mb={2}>
              {t(transition.confirmMessage)}
            </Text>

            {/* Description of what will happen */}
            <Text color="gray.300" fontSize="sm" mb={showReasonField ? 4 : 0}>
              {t(transition.description)}
            </Text>

            {/* Reason textarea (shown when transition requires or optionally accepts reason) */}
            {showReasonField && (
              <FormControl isInvalid={reasonTouched && !!reasonError}>
                <FormLabel color="gray.200">
                  {t('workflows:membership.fields.reason')}
                  {!requiresReason && (
                    <Text as="span" color="gray.400" fontSize="sm" ml={1}>
                      ({t('common:optional', 'optional')})
                    </Text>
                  )}
                </FormLabel>
                <Textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  onBlur={() => setReasonTouched(true)}
                  placeholder={t('workflows:membership.fields.reasonPlaceholder')}
                  bg="gray.700"
                  color="white"
                  borderColor="gray.600"
                  _hover={{ borderColor: 'gray.500' }}
                  _focus={{ borderColor: 'orange.400', boxShadow: '0 0 0 1px var(--chakra-colors-orange-400)' }}
                  isDisabled={isLoading}
                  minH="80px"
                />
                {reasonTouched && reasonError && (
                  <FormErrorMessage>{reasonError}</FormErrorMessage>
                )}
              </FormControl>
            )}
          </AlertDialogBody>

          <AlertDialogFooter>
            <Button
              ref={cancelRef}
              onClick={handleClose}
              isDisabled={isLoading}
            >
              {t('common:buttons.cancel')}
            </Button>
            <Button
              colorScheme="orange"
              onClick={handleConfirm}
              ml={3}
              isLoading={isLoading}
              isDisabled={isConfirmDisabled}
            >
              {t('common:buttons.confirm')}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialogOverlay>
    </AlertDialog>
  );
};

export default TransitionConfirmDialog;

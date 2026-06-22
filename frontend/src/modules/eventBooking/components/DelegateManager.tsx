/**
 * DelegateManager — Manage primary and secondary delegates for a booking order.
 *
 * Features:
 * - Shows current delegates (primary + secondary if linked)
 * - Shows pending invitation state (email + "Pending" badge)
 * - Invite form: email input + invite button (primary only)
 * - Client-side validation: reject self-invitation
 * - Calls POST /booking/{order_id}/delegates with action='invite'
 * - Revoke button: calls POST with action='revoke' (only in draft status)
 * - On 409 (version conflict): shows toast notification with "Reload" button
 *
 * Validates: Requirements 5.1, 5.2, 5.3, 5.5, 5.6, 5.7
 */

import React, { useState } from 'react';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  Button,
  HStack,
  Heading,
  Input,
  InputGroup,
  InputRightElement,
  Text,
  VStack,
  useToast,
} from '@chakra-ui/react';
import { DeleteIcon, RepeatIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { Order } from '../types/eventBooking.types';
import { manageDelegates, resendDelegateInvitation, isVersionConflict } from '../services/eventBookingApi';

export interface DelegateManagerProps {
  /** The current order containing delegates info */
  order: Order;
  /** Email of the currently logged-in user */
  currentUserEmail: string;
  /** Callback to refresh the order after delegate changes */
  onDelegateChange: () => void;
}

/**
 * Maps API error status codes to translation-friendly error keys or messages.
 */
function getDelegateErrorKey(error: any): string {
  const status = error?.response?.status;
  const serverMessage = error?.response?.data?.message;

  if (status === 404) {
    return serverMessage || 'delegate_manager.error_not_found';
  }
  if (status === 403) {
    return serverMessage || 'delegate_manager.error_no_access';
  }
  if (status === 400) {
    return serverMessage || 'delegate_manager.error_already_assigned';
  }
  return serverMessage || 'delegate_manager.error_generic';
}

const DelegateManager: React.FC<DelegateManagerProps> = ({
  order,
  currentUserEmail,
  onDelegateChange,
}) => {
  const { t } = useTranslation('eventBooking');
  const toast = useToast();
  const [email, setEmail] = useState('');
  const [isInviting, setIsInviting] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Delegate state from order
  const delegates = order.delegates;
  const primaryEmail = delegates?.primary || '';
  const secondaryEmail = delegates?.secondary || null;
  const secondaryMemberId = delegates?.secondary_member_id || null;
  const pendingEmail = delegates?.pending_secondary_email || null;

  // Determine if current user is the primary delegate
  const isPrimary = primaryEmail
    ? currentUserEmail.toLowerCase() === primaryEmail.toLowerCase()
    : true; // If no delegate info, assume current user is primary

  // Draft status check for revoke/remove actions (Req 5.7)
  const isDraft = order.status === 'draft';

  // Whether a secondary delegate is present (linked or pending)
  const hasLinkedSecondary = !!secondaryMemberId;
  const hasPendingInvitation = !!pendingEmail;
  const hasSecondary = hasLinkedSecondary || hasPendingInvitation;

  /**
   * Handle version conflict (409): show toast with reload action (Req 5.6)
   */
  const handleVersionConflict = (err: any) => {
    toast({
      title: t('delegate_manager.conflict_title'),
      description: t('delegate_manager.conflict_description'),
      status: 'warning',
      duration: null,
      isClosable: true,
      render: ({ onClose }) => (
        <Alert status="warning" borderRadius="md" boxShadow="lg">
          <AlertIcon />
          <Box flex={1}>
            <Text fontWeight="bold">{t('delegate_manager.conflict_title')}</Text>
            <Text fontSize="sm">{t('delegate_manager.conflict_description')}</Text>
          </Box>
          <Button
            size="sm"
            colorScheme="orange"
            ml={3}
            onClick={() => {
              onClose();
              onDelegateChange();
            }}
          >
            {t('delegate_manager.reload_button')}
          </Button>
        </Alert>
      ),
    });
  };

  /**
   * Handle inviting a secondary delegate by email (Req 5.1, 5.2, 5.3)
   */
  const handleInvite = async () => {
    const trimmedEmail = email.trim();
    if (!trimmedEmail) return;

    // Client-side: reject self-invitation (Req 5.2)
    if (trimmedEmail.toLowerCase() === currentUserEmail.toLowerCase()) {
      setError(t('delegate_manager.error_self_invite'));
      return;
    }

    setError(null);
    setIsInviting(true);

    try {
      await manageDelegates(order.order_id, {
        action: 'invite',
        email: trimmedEmail,
      });
      setEmail('');
      onDelegateChange();
    } catch (err: any) {
      if (isVersionConflict(err)) {
        handleVersionConflict(err);
      } else {
        setError(getDelegateErrorKey(err));
      }
    } finally {
      setIsInviting(false);
    }
  };

  /**
   * Handle revoking a pending invitation or removing a linked secondary (Req 5.7)
   */
  const handleRevoke = async () => {
    setError(null);
    setIsRevoking(true);

    try {
      await manageDelegates(order.order_id, { action: 'revoke' });
      onDelegateChange();
    } catch (err: any) {
      if (isVersionConflict(err)) {
        handleVersionConflict(err);
      } else {
        setError(getDelegateErrorKey(err));
      }
    } finally {
      setIsRevoking(false);
    }
  };

  /**
   * Handle resending the invitation email to the pending secondary delegate.
   */
  const handleResend = async () => {
    setError(null);
    setIsResending(true);

    try {
      await resendDelegateInvitation(order.order_id);
      toast({
        title: t('delegate_manager.resend_success'),
        status: 'success',
        duration: 4000,
        isClosable: true,
      });
    } catch (err: any) {
      const status = err?.response?.status;
      const serverMessage = err?.response?.data?.message;
      setError(serverMessage || t('delegate_manager.resend_error'));
      if (status !== 400 && status !== 403 && status !== 404) {
        toast({
          title: t('delegate_manager.resend_error'),
          status: 'error',
          duration: 4000,
          isClosable: true,
        });
      }
    } finally {
      setIsResending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && email.trim()) {
      handleInvite();
    }
  };

  // Don't render for orders without delegates structure
  if (!delegates) {
    return null;
  }

  return (
    <Box p={4} borderWidth={1} borderRadius="md">
      <VStack spacing={4} align="stretch">
        <Heading size="sm">{t('delegate_manager.title')}</Heading>

        {/* Primary delegate info */}
        <HStack spacing={2}>
          <Badge colorScheme="orange" fontSize="xs">
            {t('delegate_manager.primary')}
          </Badge>
          <Text fontSize="sm">
            {primaryEmail}
            {isPrimary && (
              <Text as="span" color="gray.500" ml={1}>
                {t('delegate_manager.you')}
              </Text>
            )}
          </Text>
        </HStack>

        {/* Secondary delegate info */}
        <HStack spacing={2}>
          <Badge colorScheme="gray" fontSize="xs">
            {t('delegate_manager.secondary')}
          </Badge>

          {hasLinkedSecondary ? (
            /* Linked secondary delegate */
            <HStack spacing={2} flex={1} justify="space-between">
              <Text fontSize="sm">{secondaryEmail}</Text>
              {isPrimary && isDraft && (
                <Button
                  size="xs"
                  colorScheme="red"
                  variant="ghost"
                  leftIcon={<DeleteIcon />}
                  onClick={handleRevoke}
                  isLoading={isRevoking}
                  loadingText={t('delegate_manager.removing')}
                >
                  {t('delegate_manager.remove_button')}
                </Button>
              )}
            </HStack>
          ) : hasPendingInvitation ? (
            /* Pending invitation state (Req 5.3) */
            <HStack spacing={2} flex={1} justify="space-between">
              <HStack spacing={2}>
                <Text fontSize="sm">{pendingEmail}</Text>
                <Badge colorScheme="yellow" fontSize="xs">
                  {t('delegate_manager.pending')}
                </Badge>
              </HStack>
              <HStack spacing={1}>
                {isPrimary && (
                  <Button
                    size="xs"
                    colorScheme="blue"
                    variant="ghost"
                    leftIcon={<RepeatIcon />}
                    onClick={handleResend}
                    isLoading={isResending}
                    loadingText={t('delegate_manager.resending')}
                  >
                    {t('delegate_manager.resend_button')}
                  </Button>
                )}
                {isPrimary && isDraft && (
                  <Button
                    size="xs"
                    colorScheme="red"
                    variant="ghost"
                    leftIcon={<DeleteIcon />}
                    onClick={handleRevoke}
                    isLoading={isRevoking}
                    loadingText={t('delegate_manager.revoking')}
                  >
                    {t('delegate_manager.revoke_button')}
                  </Button>
                )}
              </HStack>
            </HStack>
          ) : (
            /* No secondary delegate */
            <Text fontSize="sm" color="gray.500">
              {t('delegate_manager.no_secondary')}
            </Text>
          )}
        </HStack>

        {/* Invite form: only primary delegate, no existing secondary (Req 5.1) */}
        {isPrimary && !hasSecondary && (
          <Box>
            <Text fontSize="xs" color="gray.500" mb={2}>
              {t('delegate_manager.add_description')}
            </Text>
            <InputGroup size="sm">
              <Input
                placeholder={t('delegate_manager.email_placeholder')}
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (error) setError(null);
                }}
                onKeyDown={handleKeyDown}
                type="email"
                isDisabled={isInviting}
              />
              <InputRightElement width="5rem">
                <Button
                  size="xs"
                  colorScheme="orange"
                  onClick={handleInvite}
                  isLoading={isInviting}
                  isDisabled={!email.trim()}
                >
                  {t('delegate_manager.invite_button')}
                </Button>
              </InputRightElement>
            </InputGroup>
          </Box>
        )}

        {/* Error display */}
        {error && (
          <Alert status="error" size="sm" borderRadius="md">
            <AlertIcon />
            <AlertDescription fontSize="sm">{error}</AlertDescription>
          </Alert>
        )}
      </VStack>
    </Box>
  );
};

export default DelegateManager;

/**
 * DelegateManager — Manage primary and secondary delegates for a PresMeet order.
 *
 * - Shows current delegates (primary = current user label, secondary = email or empty)
 * - Primary delegate can add a secondary delegate by email (validated via API)
 * - Primary delegate can remove the secondary delegate
 * - Non-primary users see a read-only view of delegate info
 *
 * Validates: Requirements 12.6, 12.7, 12.8
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
} from '@chakra-ui/react';
import { DeleteIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { Order } from '../types/presmeet.types';
import { manageDelegates } from '../services/presmeetApi';

export interface DelegateManagerProps {
  /** The current order containing delegates info */
  order: Order;
  /** Email of the currently logged-in user */
  currentUserEmail: string;
  /** Callback to refresh the order after delegate changes */
  onDelegateChange: () => void;
}

/**
 * Maps API error status codes to user-friendly messages.
 */
function getDelegateErrorMessage(error: any): string {
  const status = error?.response?.status;
  const serverMessage = error?.response?.data?.message;

  if (status === 404) {
    return serverMessage || 'User not found. Please check the email address.';
  }
  if (status === 403) {
    return serverMessage || 'This user does not have PresMeet access.';
  }
  if (status === 400) {
    return serverMessage || 'This user is already assigned as a delegate.';
  }
  return serverMessage || 'An unexpected error occurred. Please try again.';
}

const DelegateManager: React.FC<DelegateManagerProps> = ({
  order,
  currentUserEmail,
  onDelegateChange,
}) => {
  const { t } = useTranslation('eventBooking');
  const [email, setEmail] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [isRemoving, setIsRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isPrimary =
    currentUserEmail.toLowerCase() === order.delegates.primary.toLowerCase();

  const handleAddDelegate = async () => {
    const trimmedEmail = email.trim();
    if (!trimmedEmail) return;

    setError(null);
    setIsAdding(true);

    try {
      await manageDelegates(order.order_id, {
        action: 'add',
        email: trimmedEmail,
      });
      setEmail('');
      onDelegateChange();
    } catch (err: any) {
      setError(getDelegateErrorMessage(err));
    } finally {
      setIsAdding(false);
    }
  };

  const handleRemoveDelegate = async () => {
    setError(null);
    setIsRemoving(true);

    try {
      await manageDelegates(order.order_id, { action: 'remove' });
      onDelegateChange();
    } catch (err: any) {
      setError(getDelegateErrorMessage(err));
    } finally {
      setIsRemoving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && email.trim()) {
      handleAddDelegate();
    }
  };

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
            {order.delegates.primary}
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
          {order.delegates.secondary ? (
            <HStack spacing={2} flex={1} justify="space-between">
              <Text fontSize="sm">{order.delegates.secondary}</Text>
              {isPrimary && (
                <Button
                  size="xs"
                  colorScheme="red"
                  variant="ghost"
                  leftIcon={<DeleteIcon />}
                  onClick={handleRemoveDelegate}
                  isLoading={isRemoving}
                  loadingText={t('delegate_manager.removing')}
                >
                  {t('delegate_manager.remove_button')}
                </Button>
              )}
            </HStack>
          ) : (
            <Text fontSize="sm" color="gray.500">
              {t('delegate_manager.no_secondary')}
            </Text>
          )}
        </HStack>

        {/* Add secondary delegate (primary only) */}
        {isPrimary && !order.delegates.secondary && (
          <Box>
            <Text fontSize="xs" color="gray.500" mb={2}>
              {t('delegate_manager.add_description')}
            </Text>
            <InputGroup size="sm">
              <Input
                placeholder={t('delegate_manager.email_placeholder')}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={handleKeyDown}
                type="email"
                isDisabled={isAdding}
              />
              <InputRightElement width="4rem">
                <Button
                  size="xs"
                  colorScheme="orange"
                  onClick={handleAddDelegate}
                  isLoading={isAdding}
                  isDisabled={!email.trim()}
                >
                  {t('delegate_manager.add_button')}
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

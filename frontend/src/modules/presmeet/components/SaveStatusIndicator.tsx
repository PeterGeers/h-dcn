/**
 * SaveStatusIndicator — Visual indicator for auto-save status.
 *
 * Displays one of three states:
 * - saving: spinner + "Saving..."
 * - saved: check icon + "Last saved: {time}"
 * - failed: warning icon + "Save failed" (orange)
 *
 * Validates: Requirement 8.4
 */

import React from 'react';
import { HStack, Spinner, Text, Icon } from '@chakra-ui/react';
import { CheckIcon, WarningIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { SaveStatus } from '../hooks/useAutoSave';

export interface SaveStatusIndicatorProps {
  /** Current save status */
  status: SaveStatus;
  /** Last successful save timestamp */
  lastSavedAt: Date | null;
}

const SaveStatusIndicator: React.FC<SaveStatusIndicatorProps> = ({
  status,
  lastSavedAt,
}) => {
  const { t } = useTranslation('eventBooking');

  if (status === 'idle' && !lastSavedAt) {
    return null;
  }

  return (
    <HStack spacing={2} fontSize="xs" color={status === 'failed' ? 'orange.500' : 'gray.500'}>
      {status === 'saving' && (
        <>
          <Spinner size="xs" color="gray.500" />
          <Text>{t('booking.saving')}</Text>
        </>
      )}
      {status === 'saved' && lastSavedAt && (
        <>
          <Icon as={CheckIcon} boxSize={3} color="green.500" />
          <Text color="green.600">
            {t('booking.last_saved', {
              time: lastSavedAt.toLocaleTimeString('nl-NL', {
                hour: '2-digit',
                minute: '2-digit',
              }),
            })}
          </Text>
        </>
      )}
      {status === 'failed' && (
        <>
          <Icon as={WarningIcon} boxSize={3} color="orange.500" />
          <Text>{t('booking.save_failed')}</Text>
        </>
      )}
      {status === 'idle' && lastSavedAt && (
        <>
          <Icon as={CheckIcon} boxSize={3} color="green.500" />
          <Text color="green.600">
            {t('booking.last_saved', {
              time: lastSavedAt.toLocaleTimeString('nl-NL', {
                hour: '2-digit',
                minute: '2-digit',
              }),
            })}
          </Text>
        </>
      )}
    </HStack>
  );
};

export default SaveStatusIndicator;

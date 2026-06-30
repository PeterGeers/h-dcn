/**
 * RowCard — Individual registry row display card.
 *
 * Shows: logo (or placeholder), label, availability status.
 * If taken: masked claimant email, disabled state.
 * If available + email_restricted + non-matching: disabled with tooltip.
 * If available + (first_come or email match): clickable.
 *
 * Validates: Requirements 2.2, 2.3, 2.5
 */

import React from 'react';
import {
  Badge,
  Box,
  HStack,
  Image,
  Text,
  Tooltip,
  VStack,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';

export interface RegistryRowData {
  row_id: string;
  label: string;
  available: boolean;
  logo_url: string | null;
  claimed_contact: string | null;
  allowed_emails?: string[];
}

export interface RowCardProps {
  /** The registry row data to display */
  row: RegistryRowData;
  /** Whether email_restricted mode is active */
  emailRestricted: boolean;
  /** The current user's email (for email_restricted matching) */
  userEmail?: string;
  /** Whether the card is currently being selected (loading) */
  isSelecting?: boolean;
  /** Called when the user clicks an available, enabled row */
  onSelect: (rowId: string) => void;
}

/**
 * Determines whether this row is enabled for the current user.
 * - Taken rows are always disabled.
 * - In email_restricted mode, only rows matching the user's email are enabled.
 * - In first_come_first_served mode, all available rows are enabled.
 */
function isRowEnabled(
  row: RegistryRowData,
  emailRestricted: boolean,
  userEmail?: string
): boolean {
  if (!row.available) return false;
  if (!emailRestricted) return true;

  // email_restricted mode: check if user's email matches allowed_emails
  if (!userEmail || !row.allowed_emails || row.allowed_emails.length === 0) {
    return false;
  }
  const lowerEmail = userEmail.toLowerCase();
  return row.allowed_emails.some(
    (allowed) => allowed.toLowerCase() === lowerEmail
  );
}

const RowCard: React.FC<RowCardProps> = ({
  row,
  emailRestricted,
  userEmail,
  isSelecting,
  onSelect,
}) => {
  const { t } = useTranslation('eventBooking');
  const enabled = isRowEnabled(row, emailRestricted, userEmail);
  const disabled = !enabled;

  const handleClick = () => {
    if (enabled && !isSelecting) {
      onSelect(row.row_id);
    }
  };

  // Tooltip for email-restricted disabled rows
  const tooltipLabel =
    disabled && row.available && emailRestricted
      ? t('registry.email_restricted_tooltip')
      : '';

  const cardContent = (
    <Box
      borderWidth="2px"
      borderColor={disabled ? 'gray.600' : 'gray.500'}
      borderRadius="lg"
      p={4}
      cursor={disabled || isSelecting ? 'not-allowed' : 'pointer'}
      opacity={disabled ? 0.6 : 1}
      bg={disabled ? 'gray.900' : 'gray.800'}
      _hover={
        !disabled && !isSelecting
          ? { borderColor: 'orange.400', shadow: 'md' }
          : undefined
      }
      transition="all 0.2s"
      onClick={handleClick}
      role="button"
      aria-disabled={disabled}
      aria-label={`${row.label} - ${row.available ? t('registry.status_available') : t('registry.status_taken')}`}
    >
      <HStack spacing={4} align="center">
        {/* Logo or placeholder */}
        {row.logo_url ? (
          <Image
            src={row.logo_url}
            alt={`${row.label} logo`}
            boxSize="48px"
            objectFit="contain"
            borderRadius="md"
            fallback={
              <Box
                boxSize="48px"
                bg="gray.700"
                borderRadius="md"
                display="flex"
                alignItems="center"
                justifyContent="center"
              >
                <Text fontSize="xs" color="gray.400">
                  {row.label.substring(0, 2).toUpperCase()}
                </Text>
              </Box>
            }
          />
        ) : (
          <Box
            boxSize="48px"
            bg="gray.700"
            borderRadius="md"
            display="flex"
            alignItems="center"
            justifyContent="center"
            flexShrink={0}
          >
            <Text fontSize="sm" fontWeight="bold" color="gray.400">
              {row.label.substring(0, 2).toUpperCase()}
            </Text>
          </Box>
        )}

        {/* Label and status */}
        <VStack align="start" spacing={0} flex={1} minW={0}>
          <Text fontWeight="semibold" fontSize="md" color="white" noOfLines={1}>
            {row.label}
          </Text>
          {!row.available && row.claimed_contact && (
            <Text fontSize="xs" color="gray.400" noOfLines={1}>
              {row.claimed_contact}
            </Text>
          )}
        </VStack>

        {/* Availability badge */}
        <Badge
          colorScheme={row.available ? 'green' : 'red'}
          fontSize="xs"
          px={2}
          py={1}
          borderRadius="md"
          flexShrink={0}
        >
          {row.available
            ? t('registry.status_available')
            : t('registry.status_taken')}
        </Badge>
      </HStack>
    </Box>
  );

  // Wrap with tooltip for email-restricted disabled rows
  if (tooltipLabel) {
    return (
      <Tooltip label={tooltipLabel} hasArrow placement="top">
        {cardContent}
      </Tooltip>
    );
  }

  return cardContent;
};

export default RowCard;

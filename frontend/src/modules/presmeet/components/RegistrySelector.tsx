/**
 * RegistrySelector — Second step of the Landing Page Flow.
 *
 * Fetches registry data from GET /events/{event_id}/registry using the session token.
 * Displays all Registry_Rows sorted alphabetically with availability status.
 * Handles loading, error (with retry), and empty states.
 *
 * Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 17.1
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  Center,
  Heading,
  Spinner,
  Text,
  VStack,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import axios, { AxiosError } from 'axios';
import RowCard, { RegistryRowData } from './RowCard';

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

export interface RegistryResponse {
  rows: RegistryRowData[];
  row_label: string;
  claim_mode: 'first_come_first_served' | 'email_restricted';
}

export interface RegistrySelectorProps {
  /** Event ID to fetch registry for */
  eventId: string;
  /** Session token from password verification step */
  sessionToken: string;
  /** Row label from registry_config (e.g., "club", "team") */
  rowLabel?: string;
  /** Claim mode from registry_config */
  claimMode?: 'first_come_first_served' | 'email_restricted';
  /** Current user's email (for email_restricted matching) */
  userEmail?: string;
  /** Called when user selects an available row */
  onSelectRow: (rowId: string, rowLabel: string) => void;
}

const RegistrySelector: React.FC<RegistrySelectorProps> = ({
  eventId,
  sessionToken,
  rowLabel: propRowLabel,
  claimMode: propClaimMode,
  userEmail,
  onSelectRow,
}) => {
  const { t } = useTranslation('eventBooking');

  const [rows, setRows] = useState<RegistryRowData[]>([]);
  const [rowLabel, setRowLabel] = useState(propRowLabel || '');
  const [claimMode, setClaimMode] = useState(propClaimMode || 'first_come_first_served');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectingRowId, setSelectingRowId] = useState<string | null>(null);

  const fetchRegistry = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.get<RegistryResponse>(
        `${BASE_URL}/events/${encodeURIComponent(eventId)}/registry`,
        {
          headers: {
            'X-Session-Token': sessionToken,
          },
        }
      );

      const data = response.data;
      setRows(data.rows);
      setRowLabel(data.row_label || propRowLabel || '');
      setClaimMode(data.claim_mode || propClaimMode || 'first_come_first_served');
    } catch (err) {
      const axiosError = err as AxiosError;
      if (axiosError.response?.status === 401) {
        setError(t('registry.session_expired'));
      } else {
        // Requirement 2.6: show localized error on S3/API failure
        setError(t('registry.load_failed'));
      }
    } finally {
      setLoading(false);
    }
  }, [eventId, sessionToken, propRowLabel, propClaimMode, t]);

  useEffect(() => {
    fetchRegistry();
  }, [fetchRegistry]);

  const handleSelectRow = (rowId: string) => {
    const selectedRow = rows.find((r) => r.row_id === rowId);
    if (selectedRow) {
      setSelectingRowId(rowId);
      onSelectRow(rowId, selectedRow.label);
    }
  };

  // --- Loading state ---
  if (loading) {
    return (
      <Center py={12}>
        <VStack spacing={4}>
          <Spinner size="xl" color="blue.500" />
          <Text color="gray.600">{t('registry.loading')}</Text>
        </VStack>
      </Center>
    );
  }

  // --- Error state with retry (Requirement 2.6) ---
  if (error) {
    return (
      <Box maxW="lg" mx="auto" py={8} px={4}>
        <Alert
          status="error"
          borderRadius="md"
          flexDirection="column"
          textAlign="center"
          py={6}
        >
          <AlertIcon boxSize="32px" mr={0} mb={3} />
          <AlertTitle mb={2}>{t('registry.error_title')}</AlertTitle>
          <AlertDescription mb={4}>{error}</AlertDescription>
          <Button size="sm" colorScheme="red" variant="outline" onClick={fetchRegistry}>
            {t('registry.retry')}
          </Button>
        </Alert>
      </Box>
    );
  }

  // --- Empty state ---
  if (rows.length === 0) {
    return (
      <Box maxW="lg" mx="auto" py={8} px={4} textAlign="center">
        <Alert status="info" borderRadius="md">
          <AlertIcon />
          <Text>{t('registry.no_rows')}</Text>
        </Alert>
      </Box>
    );
  }

  const emailRestricted = claimMode === 'email_restricted';
  // Requirement 2.4: Use Row_Label from registry_config for UI labels
  const selectorTitle = t('registry.select_title', { rowLabel });

  return (
    <Box maxW="2xl" mx="auto" py={8} px={4}>
      <VStack spacing={6} align="stretch">
        <Box textAlign="center">
          <Heading size="lg" mb={2}>
            {selectorTitle}
          </Heading>
          <Text color="gray.600">
            {t('registry.select_description', { rowLabel })}
          </Text>
        </Box>

        <VStack spacing={3} align="stretch">
          {rows.map((row) => (
            <RowCard
              key={row.row_id}
              row={row}
              emailRestricted={emailRestricted}
              userEmail={userEmail}
              isSelecting={selectingRowId === row.row_id}
              onSelect={handleSelectRow}
            />
          ))}
        </VStack>
      </VStack>
    </Box>
  );
};

export default RegistrySelector;

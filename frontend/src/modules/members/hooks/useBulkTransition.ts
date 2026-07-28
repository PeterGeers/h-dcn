/**
 * useBulkTransition Hook
 *
 * Handles calling POST /members/bulk-transition to execute a workflow
 * state transition for multiple members at once. Manages loading state,
 * stores results for display by BulkResultSummary, and shows toast for
 * overall outcome (success / partial / all failed).
 *
 * Validates: Requirements 3.2
 */

import { useState, useCallback } from 'react';
import { useToast } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { ApiService } from '../../../services/apiService';
import { API_CONFIG } from '../../../config/api';

// ============================================================================
// TYPES
// ============================================================================

export interface BulkTransitionMemberResult {
  member_id: string;
  success: boolean;
  new_status?: string;
  error?: string;
}

export interface BulkTransitionResponse {
  total: number;
  succeeded: number;
  failed: number;
  results: BulkTransitionMemberResult[];
}

export interface UseBulkTransitionResult {
  /** Execute a bulk transition for multiple members */
  mutate: (
    event: string,
    memberIds: string[],
    context?: Record<string, string>
  ) => Promise<BulkTransitionResponse | null>;
  /** Whether a bulk transition is currently in progress */
  isLoading: boolean;
  /** Results from the last bulk transition, or null */
  results: BulkTransitionResponse | null;
  /** Clear the results state */
  reset: () => void;
}

// ============================================================================
// HOOK
// ============================================================================

export function useBulkTransition(): UseBulkTransitionResult {
  const { t } = useTranslation('workflows');
  const toast = useToast();

  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<BulkTransitionResponse | null>(null);

  const reset = useCallback(() => {
    setResults(null);
  }, []);

  const mutate = useCallback(
    async (
      event: string,
      memberIds: string[],
      context: Record<string, string> = {}
    ): Promise<BulkTransitionResponse | null> => {
      setIsLoading(true);
      setResults(null);

      try {
        const endpoint = `${API_CONFIG.ENDPOINTS.MEMBERS}/bulk-transition`;

        const response = await ApiService.post<BulkTransitionResponse>(endpoint, {
          event,
          member_ids: memberIds,
          context,
        });

        if (response.success && response.data) {
          const data = response.data;
          setResults(data);

          // Show toast based on outcome
          if (data.failed === 0) {
            // All succeeded
            toast({
              title: t('membership.bulk.title', { defaultValue: 'Bulk action' }),
              description: t('membership.bulk.result', {
                succeeded: data.succeeded,
                total: data.total,
                defaultValue: `${data.succeeded} of ${data.total} members successfully processed`,
              }),
              status: 'success',
              duration: 5000,
              isClosable: true,
            });
          } else if (data.succeeded === 0) {
            // All failed
            toast({
              title: t('membership.bulk.title', { defaultValue: 'Bulk action' }),
              description: t('membership.bulk.failed', {
                failed: data.failed,
                defaultValue: `${data.failed} failed`,
              }),
              status: 'error',
              duration: 7000,
              isClosable: true,
            });
          } else {
            // Partial success
            toast({
              title: t('membership.bulk.title', { defaultValue: 'Bulk action' }),
              description: t('membership.bulk.result', {
                succeeded: data.succeeded,
                total: data.total,
                defaultValue: `${data.succeeded} of ${data.total} members successfully processed`,
              }),
              status: 'warning',
              duration: 7000,
              isClosable: true,
            });
          }

          return data;
        }

        // API call failed at HTTP level
        const errorMessage =
          response.error ||
          t('membership.errors.transitionFailed', {
            error: 'Unknown error',
            defaultValue: 'Status change failed',
          });

        toast({
          title: t('membership.bulk.title', { defaultValue: 'Bulk action' }),
          description: errorMessage,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });

        return null;
      } catch (err) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : t('membership.errors.transitionFailed', {
                error: 'Network error',
                defaultValue: 'Connection failed, try again',
              });

        toast({
          title: t('membership.bulk.title', { defaultValue: 'Bulk action' }),
          description: errorMessage,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });

        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [toast, t]
  );

  return { mutate, isLoading, results, reset };
}

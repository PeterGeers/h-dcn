/**
 * useMemberTransition Hook
 *
 * Handles calling POST /members/{id}/transition to execute a workflow
 * state transition for a single member. Manages loading/error state,
 * shows toast on error, and supports an onSuccess callback for refreshing
 * member data after a successful transition.
 *
 * Validates: Requirements 3.1
 */

import { useState, useCallback } from 'react';
import { useToast } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { ApiService } from '../../../services/apiService';
import { API_CONFIG } from '../../../config/api';

// ============================================================================
// TYPES
// ============================================================================

export interface TransitionResponse {
  success: boolean;
  old_status?: string;
  new_status?: string;
  actions_executed?: string[];
  side_effects_executed?: string[];
  error?: string;
}

export interface UseMemberTransitionOptions {
  /** Called after a successful transition — use to refresh member data */
  onSuccess?: (result: TransitionResponse) => void;
}

export interface UseMemberTransitionResult {
  /** Execute a transition for the member */
  mutate: (event: string, context?: Record<string, string>) => Promise<TransitionResponse | null>;
  /** Whether a transition is currently in progress */
  isLoading: boolean;
  /** Error message from the last failed transition, or null */
  error: string | null;
  /** Clear the error state */
  reset: () => void;
}

// ============================================================================
// HOOK
// ============================================================================

export function useMemberTransition(
  memberId: string,
  options?: UseMemberTransitionOptions
): UseMemberTransitionResult {
  const { t } = useTranslation('workflows');
  const toast = useToast();

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setError(null);
  }, []);

  const mutate = useCallback(
    async (
      event: string,
      context: Record<string, string> = {}
    ): Promise<TransitionResponse | null> => {
      setIsLoading(true);
      setError(null);

      try {
        const endpoint = `${API_CONFIG.ENDPOINTS.MEMBERS}/${memberId}/transition`;

        const response = await ApiService.post<TransitionResponse>(endpoint, {
          event,
          context,
        });

        if (response.success && response.data?.success) {
          // Transition succeeded
          options?.onSuccess?.(response.data);
          return response.data;
        }

        // Backend returned an error response
        const errorMessage =
          response.data?.error ||
          response.error ||
          t('errors.transitionFailed', { defaultValue: 'Transition failed' });

        setError(errorMessage);

        toast({
          title: t('errors.transitionErrorTitle', { defaultValue: 'Action failed' }),
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
            : t('errors.networkError', { defaultValue: 'Connection failed, try again' });

        setError(errorMessage);

        toast({
          title: t('errors.transitionErrorTitle', { defaultValue: 'Action failed' }),
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
    [memberId, options, toast, t]
  );

  return { mutate, isLoading, error, reset };
}

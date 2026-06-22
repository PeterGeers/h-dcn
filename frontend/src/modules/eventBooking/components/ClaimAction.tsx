/**
 * ClaimAction — Account creation form + onboard API call.
 *
 * This component handles the final step of the Landing_Page_Flow:
 * - Displays an account creation form (name, email, password) for new users
 * - If user is already authenticated, pre-fills name/email and hides password
 * - Calls POST /events/{event_id}/onboard to atomically claim a row
 * - Handles error responses: 409 (row claimed / duplicate claim), 403 (email not authorized)
 * - Redirects to /events/{eventId}/booking on success
 *
 * Validates: Requirements 3.1, 3.2, 3.3, 3.4, 4.1, 4.6
 */

import React, { useCallback, useState } from 'react';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Heading,
  Input,
  Text,
  VStack,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import axios, { AxiosError } from 'axios';

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

// --- Types ---

interface OnboardResponse {
  member_id: string;
  message: string;
  is_new_user: boolean;
}

interface OnboardErrorResponse {
  error?: string;
  contact?: string; // Masked email of existing claimant (409)
  detail?: string;
}

interface FieldErrors {
  name?: string;
  email?: string;
  password?: string;
}

export interface ClaimActionProps {
  /** Event ID for the onboard endpoint. */
  eventId: string;
  /** Session token from verify-password step. */
  sessionToken: string;
  /** The selected registry row ID to claim. */
  selectedRowId: string;
  /** Display label for the selected row (e.g., club name). */
  rowLabel: string;
  /** Whether the user is already authenticated. */
  isAuthenticated?: boolean;
  /** Pre-filled user name (for authenticated users). */
  userName?: string;
  /** Pre-filled user email (for authenticated users). */
  userEmail?: string;
  /** Optional callback on successful claim (in addition to redirect). */
  onSuccess?: (memberId: string) => void;
}

const ClaimAction: React.FC<ClaimActionProps> = ({
  eventId,
  sessionToken,
  selectedRowId,
  rowLabel,
  isAuthenticated = false,
  userName = '',
  userEmail = '',
  onSuccess,
}) => {
  const { t } = useTranslation('eventBooking');
  const navigate = useNavigate();

  // Form state
  const [name, setName] = useState(userName);
  const [email, setEmail] = useState(userEmail);
  const [password, setPassword] = useState('');

  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [conflictContact, setConflictContact] = useState<string | null>(null);

  /**
   * Client-side validation before API call.
   * Returns true if valid, false otherwise (and sets field errors).
   */
  const validateForm = useCallback((): boolean => {
    const errors: FieldErrors = {};

    const trimmedName = name.trim();
    if (!trimmedName) {
      errors.name = t('claim.error_name_required');
    } else if (trimmedName.length > 100) {
      errors.name = t('claim.error_name_too_long');
    }

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      errors.email = t('claim.error_email_required');
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errors.email = t('claim.error_email_invalid');
    }

    // Password required only for new users (not authenticated)
    if (!isAuthenticated && !password) {
      errors.password = t('claim.error_password_required');
    } else if (!isAuthenticated && password.length < 8) {
      errors.password = t('claim.error_password_too_short');
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }, [name, email, password, isAuthenticated, t]);

  /**
   * Submit the onboard request to claim the selected row.
   */
  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (isSubmitting) return;

      // Clear previous errors
      setGeneralError(null);
      setConflictContact(null);

      if (!validateForm()) return;

      setIsSubmitting(true);

      try {
        const payload: Record<string, string> = {
          row_id: selectedRowId,
          email: email.trim().toLowerCase(),
          name: name.trim(),
          session_token: sessionToken,
        };

        // Only include password for new users
        if (!isAuthenticated && password) {
          payload.password = password;
        }

        const response = await axios.post<OnboardResponse>(
          `${BASE_URL}/events/${encodeURIComponent(eventId)}/onboard`,
          payload
        );

        const { member_id } = response.data;

        // Requirement 4.6: Redirect to booking on success
        if (onSuccess) {
          onSuccess(member_id);
        }
        navigate(`/events/${encodeURIComponent(eventId)}/booking`, { replace: true });
      } catch (err) {
        const axiosError = err as AxiosError<OnboardErrorResponse>;
        const status = axiosError.response?.status;
        const data = axiosError.response?.data;

        if (status === 409) {
          // Requirement 3.2: Row already claimed OR user already holds a claim
          const contact = data?.contact;
          if (contact) {
            setConflictContact(contact);
            setGeneralError(t('claim.error_row_taken'));
          } else {
            setGeneralError(data?.error || t('claim.error_already_claimed'));
          }
        } else if (status === 403) {
          // Requirement 3.3/3.4: Email not authorized in email_restricted mode
          setGeneralError(data?.error || t('claim.error_email_not_authorized'));
        } else if (status === 400) {
          // Validation error from backend — show field-specific if possible
          const detail = data?.error || data?.detail;
          if (detail) {
            setGeneralError(detail);
          } else {
            setGeneralError(t('claim.error_validation'));
          }
        } else {
          // 500 or network error
          setGeneralError(t('claim.error_generic'));
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [
      isSubmitting,
      validateForm,
      selectedRowId,
      email,
      name,
      sessionToken,
      isAuthenticated,
      password,
      eventId,
      onSuccess,
      navigate,
      t,
    ]
  );

  return (
    <Box maxW="md" mx="auto" py={8} px={4}>
      <VStack spacing={6} align="stretch">
        <Box textAlign="center">
          <Heading size="lg" mb={2}>
            {t('claim.title')}
          </Heading>
          <Text color="gray.600">
            {t('claim.description', { rowLabel })}
          </Text>
        </Box>

        {/* Conflict alert: row already claimed with masked contact */}
        {conflictContact && (
          <Alert status="warning" borderRadius="md">
            <AlertIcon />
            <Box>
              <AlertTitle>{t('claim.conflict_title')}</AlertTitle>
              <AlertDescription>
                {t('claim.conflict_description', { contact: conflictContact })}
              </AlertDescription>
            </Box>
          </Alert>
        )}

        {/* General error alert (non-conflict) */}
        {generalError && !conflictContact && (
          <Alert status="error" borderRadius="md">
            <AlertIcon />
            <AlertDescription>{generalError}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <VStack spacing={4}>
            {/* Name field */}
            <FormControl isInvalid={!!fieldErrors.name} isRequired>
              <FormLabel>{t('claim.label_name')}</FormLabel>
              <Input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (fieldErrors.name) {
                    setFieldErrors((prev) => ({ ...prev, name: undefined }));
                  }
                }}
                placeholder={t('claim.placeholder_name')}
                size="lg"
                aria-label={t('claim.label_name')}
              />
              {fieldErrors.name && (
                <FormErrorMessage>{fieldErrors.name}</FormErrorMessage>
              )}
            </FormControl>

            {/* Email field */}
            <FormControl isInvalid={!!fieldErrors.email} isRequired>
              <FormLabel>{t('claim.label_email')}</FormLabel>
              <Input
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (fieldErrors.email) {
                    setFieldErrors((prev) => ({ ...prev, email: undefined }));
                  }
                }}
                placeholder={t('claim.placeholder_email')}
                size="lg"
                isReadOnly={isAuthenticated}
                aria-label={t('claim.label_email')}
              />
              {fieldErrors.email && (
                <FormErrorMessage>{fieldErrors.email}</FormErrorMessage>
              )}
            </FormControl>

            {/* Password field — only for new (unauthenticated) users */}
            {!isAuthenticated && (
              <FormControl isInvalid={!!fieldErrors.password} isRequired>
                <FormLabel>{t('claim.label_password')}</FormLabel>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (fieldErrors.password) {
                      setFieldErrors((prev) => ({ ...prev, password: undefined }));
                    }
                  }}
                  placeholder={t('claim.placeholder_password')}
                  size="lg"
                  aria-label={t('claim.label_password')}
                />
                {fieldErrors.password && (
                  <FormErrorMessage>{fieldErrors.password}</FormErrorMessage>
                )}
              </FormControl>
            )}

            {/* Submit button */}
            <Button
              type="submit"
              colorScheme="blue"
              size="lg"
              width="full"
              isLoading={isSubmitting}
              loadingText={t('claim.claiming')}
              isDisabled={isSubmitting}
            >
              {t('claim.submit_button', { rowLabel })}
            </Button>
          </VStack>
        </form>
      </VStack>
    </Box>
  );
};

export default ClaimAction;

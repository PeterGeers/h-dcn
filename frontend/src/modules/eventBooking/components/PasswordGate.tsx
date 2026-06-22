import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormErrorMessage,
  Heading,
  Input,
  Text,
  VStack,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { useTranslation } from 'react-i18next';
import axios, { AxiosError } from 'axios';

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

/** Shake animation for incorrect password feedback. */
const shakeKeyframes = keyframes`
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-6px); }
  40% { transform: translateX(6px); }
  60% { transform: translateX(-4px); }
  80% { transform: translateX(4px); }
`;

const shakeAnimation = `${shakeKeyframes} 0.4s ease-in-out`;

export interface RegistryConfig {
  s3_path: string;
  row_label: string;
  claim_mode: 'first_come_first_served' | 'email_restricted';
  max_delegates_per_row: number;
  allow_logo_upload: boolean;
}

export interface VerifyPasswordResult {
  valid: boolean;
  event_name?: string;
  registry_config?: RegistryConfig;
  session_token?: string;
}

export interface PasswordGateProps {
  /** Event ID to verify the password against. */
  eventId: string;
  /** Whether the landing page is enabled for this event. */
  landingPageEnabled: boolean;
  /** Whether the event has a password configured. */
  hasEventPassword: boolean;
  /** Called on successful password verification with event metadata. */
  onSuccess: (result: VerifyPasswordResult) => void;
  /** Called when the password gate should be skipped entirely. */
  onSkip: () => void;
}

/**
 * PasswordGate — first step of the Landing Page Flow.
 *
 * Verifies the shared event password via POST /events/{event_id}/verify-password.
 * On success, passes the session_token and event metadata to the parent.
 * Handles rate limiting (429) with a countdown timer.
 * Skips entirely if landing_page_enabled is false or no event_password is set.
 *
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 17.1
 */
const PasswordGate: React.FC<PasswordGateProps> = ({
  eventId,
  landingPageEnabled,
  hasEventPassword,
  onSuccess,
  onSkip,
}) => {
  const { t } = useTranslation('eventBooking');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [shaking, setShaking] = useState(false);
  const [rateLimitSeconds, setRateLimitSeconds] = useState(0);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const skippedRef = useRef(false);

  // Requirement 1.5: Skip if no password or landing page disabled
  useEffect(() => {
    if ((!landingPageEnabled || !hasEventPassword) && !skippedRef.current) {
      skippedRef.current = true;
      onSkip();
    }
  }, [landingPageEnabled, hasEventPassword, onSkip]);

  // Cleanup countdown on unmount
  useEffect(() => {
    return () => {
      if (countdownRef.current) {
        clearInterval(countdownRef.current);
      }
    };
  }, []);

  const startCountdown = useCallback((seconds: number) => {
    setRateLimitSeconds(seconds);
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
    }
    countdownRef.current = setInterval(() => {
      setRateLimitSeconds((prev) => {
        if (prev <= 1) {
          if (countdownRef.current) {
            clearInterval(countdownRef.current);
            countdownRef.current = null;
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!password.trim() || isSubmitting || rateLimitSeconds > 0) {
        return;
      }

      setError(null);
      setIsSubmitting(true);

      try {
        const response = await axios.post<VerifyPasswordResult>(
          `${BASE_URL}/events/${encodeURIComponent(eventId)}/verify-password`,
          { password }
        );

        const result = response.data;

        if (result.valid) {
          // Requirement 1.3: On success, pass event metadata
          onSuccess(result);
        } else {
          // Requirement 1.2: Same error for wrong password or non-existent event
          setError(t('landing.password_incorrect'));
          setShaking(true);
          setTimeout(() => setShaking(false), 400);
        }
      } catch (err) {
        const axiosError = err as AxiosError<{ error?: string; retry_after?: number }>;

        if (axiosError.response?.status === 429) {
          // Requirement 1.4: Rate limit handling
          const retryAfter = axiosError.response.data?.retry_after || 60;
          startCountdown(retryAfter);
          setError(t('landing.rate_limited'));
        } else {
          // Requirement 1.2: Generic error (no info leak)
          setError(t('landing.password_incorrect'));
          setShaking(true);
          setTimeout(() => setShaking(false), 400);
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [password, isSubmitting, rateLimitSeconds, eventId, onSuccess, startCountdown, t]
  );

  // Don't render if we should skip
  if (!landingPageEnabled || !hasEventPassword) {
    return null;
  }

  const isButtonDisabled = isSubmitting || rateLimitSeconds > 0 || !password.trim();

  return (
    <Box maxW="md" mx="auto" py={12} px={4}>
      <VStack spacing={6} align="stretch">
        <Box textAlign="center">
          <Heading size="lg" mb={2}>
            {t('landing.password_title')}
          </Heading>
          <Text color="gray.600">
            {t('landing.password_description')}
          </Text>
        </Box>

        <form onSubmit={handleSubmit}>
          <VStack spacing={4}>
            <FormControl isInvalid={!!error}>
              <Box animation={shaking ? shakeAnimation : undefined}>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder={t('landing.password_placeholder')}
                  size="lg"
                  autoFocus
                  aria-label={t('landing.password_placeholder')}
                  disabled={rateLimitSeconds > 0}
                />
              </Box>
              {error && <FormErrorMessage>{error}</FormErrorMessage>}
            </FormControl>

            <Button
              type="submit"
              colorScheme="blue"
              size="lg"
              width="full"
              isLoading={isSubmitting}
              isDisabled={isButtonDisabled}
              loadingText={t('landing.verifying')}
            >
              {rateLimitSeconds > 0
                ? t('landing.wait_seconds', { seconds: rateLimitSeconds })
                : t('landing.verify_button')}
            </Button>
          </VStack>
        </form>
      </VStack>
    </Box>
  );
};

export default PasswordGate;

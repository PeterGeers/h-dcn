import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  Input,
  VStack,
  Text,
  Heading,
} from '@chakra-ui/react';

interface EmailRecoveryProps {
  onSuccess: (result: { tokens: { AccessToken: string }; user: { email: string } }) => void;
  onCancel: () => void;
  onError: (error: string) => void;
}

/**
 * EmailRecovery component — allows users to recover their account via email verification.
 * Used as a fallback when passkey authentication is not available.
 */
export function EmailRecovery({ onSuccess, onCancel, onError }: EmailRecoveryProps) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'email' | 'code'>('email');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const handleSendRecoveryEmail = async () => {
    if (!email) return;
    setLoading(true);
    setErrorMessage('');

    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_BASE_URL}/auth/recovery/send`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email }),
        }
      );

      if (!response.ok) {
        const data = await response.json();
        setErrorMessage(data.error || 'Failed to send recovery email');
        return;
      }

      setStep('code');
    } catch (err: any) {
      setErrorMessage('Network error. Please check your connection.');
      onError(err.message || 'Recovery failed');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    if (!recoveryCode) return;
    setLoading(true);
    setErrorMessage('');

    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_BASE_URL}/auth/recovery/verify`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, code: recoveryCode }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        if (data.code === 'INVALID_CODE') {
          setErrorMessage('Invalid recovery code. Please check the code and try again.');
        } else if (data.code === 'EXPIRED_CODE') {
          setErrorMessage('Recovery code has expired. Please request a new recovery email.');
          setStep('email');
        } else {
          setErrorMessage(data.error || 'Verification failed');
        }
        return;
      }

      onSuccess({
        tokens: { AccessToken: data.accessToken || '' },
        user: { email },
      });
    } catch (err: any) {
      setErrorMessage('Network error. Please check your connection.');
      onError(err.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box p={4}>
      <Heading size="md" mb={4}>Account Recovery</Heading>

      {errorMessage && (
        <Text color="red.300" mb={3}>{errorMessage}</Text>
      )}

      {step === 'email' ? (
        <VStack spacing={4}>
          <Text>Enter your email address to receive recovery instructions</Text>
          <FormControl>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email address"
            />
          </FormControl>
          <Button
            onClick={handleSendRecoveryEmail}
            isLoading={loading}
            colorScheme="orange"
            width="full"
          >
            Send Recovery Email
          </Button>
          <Button variant="ghost" onClick={onCancel} width="full">
            Cancel
          </Button>
        </VStack>
      ) : (
        <VStack spacing={4}>
          <Text>Recovery Code</Text>
          <Text fontSize="sm">Enter the 6-digit code sent to your email</Text>
          <FormControl>
            <Input
              value={recoveryCode}
              onChange={(e) => setRecoveryCode(e.target.value)}
              placeholder="Enter recovery code"
              maxLength={6}
            />
          </FormControl>
          <Text fontSize="sm" color="gray.400">
            Set up a new passkey for your account
          </Text>
          <Button
            onClick={handleVerifyCode}
            isLoading={loading}
            colorScheme="orange"
            width="full"
          >
            Verify Recovery Code
          </Button>
          <Button variant="ghost" onClick={() => setStep('email')} width="full">
            Back
          </Button>
        </VStack>
      )}
    </Box>
  );
}

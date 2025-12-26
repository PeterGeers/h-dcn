import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  Text,
  Alert,
  AlertIcon,
  Heading,
  PinInput,
  PinInputField,
  HStack,
  useToast,
  Divider
} from '@chakra-ui/react';
import { PasskeySetup } from './PasskeySetup';

interface EmailRecoveryProps {
  onSuccess: (authData?: any) => void;
  onCancel: () => void;
  onError: (error: string) => void;
}

type RecoveryStep = 'email' | 'code' | 'passkey_setup' | 'complete';

export function EmailRecovery({ onSuccess, onCancel, onError }: EmailRecoveryProps) {
  const [step, setStep] = useState<RecoveryStep>('email');
  const [email, setEmail] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const toast = useToast();

  const handleInitiateRecovery = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/recovery/initiate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        setStep('code');
        toast({
          title: 'Recovery email sent',
          description: 'Check your email for recovery instructions.',
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
      } else {
        setError(data.error || 'Failed to send recovery email');
      }
    } catch (err) {
      console.error('Recovery initiation error:', err);
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    if (recoveryCode.length !== 6) {
      setError('Please enter the complete 6-digit recovery code');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/recovery/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          recoveryCode,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setStep('passkey_setup');
        toast({
          title: 'Recovery code verified',
          description: 'Now set up a new passkey for your account.',
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
      } else {
        if (data.code === 'INVALID_CODE') {
          setError('Invalid recovery code. Please check the code and try again.');
        } else if (data.code === 'EXPIRED_CODE') {
          setError('Recovery code has expired. Please request a new recovery email.');
          setStep('email');
        } else {
          setError(data.error || 'Failed to verify recovery code');
        }
      }
    } catch (err) {
      console.error('Code verification error:', err);
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handlePasskeySetupSuccess = async (credential: any) => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/recovery/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          credential,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setStep('complete');
        toast({
          title: 'Account recovery completed',
          description: 'Your new passkey has been set up successfully.',
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
        
        // Wait a moment then call success with auth data
        setTimeout(() => {
          onSuccess(data);
        }, 2000);
      } else {
        setError(data.error || 'Failed to complete recovery');
      }
    } catch (err) {
      console.error('Recovery completion error:', err);
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handlePasskeySetupError = (error: string) => {
    setError(error);
  };

  const handleRequestNewCode = () => {
    setStep('email');
    setRecoveryCode('');
    setError('');
  };

  if (step === 'passkey_setup') {
    return (
      <Box maxW="md" w="full" p={6}>
        <VStack spacing={6}>
          <Box textAlign="center">
            <Heading color="orange.400" size="md">Account Recovery</Heading>
            <Text color="gray.400" mt={2}>
              Set up a new passkey for your account
            </Text>
          </Box>

          <PasskeySetup
            userEmail={email}
            onSuccess={handlePasskeySetupSuccess}
            onError={handlePasskeySetupError}
            onSkip={() => {
              // For recovery, we don't allow skipping passkey setup
              setError('Passkey setup is required to complete account recovery');
            }}
            isRecovery={true}
          />

          {error && (
            <Alert status="error" bg="red.900" borderColor="red.500" border="1px solid">
              <AlertIcon color="red.300" />
              <Text color="red.100">{error}</Text>
            </Alert>
          )}

          <Button
            variant="outline"
            colorScheme="gray"
            onClick={onCancel}
            isDisabled={loading}
          >
            Cancel Recovery
          </Button>
        </VStack>
      </Box>
    );
  }

  if (step === 'complete') {
    return (
      <Box maxW="md" w="full" p={6}>
        <VStack spacing={6}>
          <Box textAlign="center">
            <Heading color="green.400" size="md">Recovery Complete!</Heading>
            <Text color="gray.400" mt={2}>
              Your account has been recovered successfully.
            </Text>
            <Text color="green.300" mt={4} fontSize="sm">
              You can now use your new passkey to sign in.
            </Text>
          </Box>

          <Button
            colorScheme="green"
            size="lg"
            width="full"
            onClick={() => onSuccess()}
          >
            Continue to Sign In
          </Button>
        </VStack>
      </Box>
    );
  }

  return (
    <Box maxW="md" w="full" p={6}>
      <VStack spacing={6}>
        <Box textAlign="center">
          <Heading color="orange.400" size="md">Account Recovery</Heading>
          <Text color="gray.400" mt={2}>
            {step === 'email' 
              ? 'Enter your email address to receive recovery instructions'
              : 'Enter the 6-digit code sent to your email'
            }
          </Text>
        </Box>

        {error && (
          <Alert status="error" bg="red.900" borderColor="red.500" border="1px solid">
            <AlertIcon color="red.300" />
            <Text color="red.100">{error}</Text>
          </Alert>
        )}

        {step === 'email' && (
          <form onSubmit={handleInitiateRecovery} style={{ width: '100%' }}>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel color="gray.300">Email Address</FormLabel>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email address"
                  bg="gray.700"
                  border="1px solid"
                  borderColor="gray.600"
                  color="white"
                  _placeholder={{ color: 'gray.400' }}
                  _focus={{ borderColor: 'orange.400' }}
                />
              </FormControl>

              <Button
                type="submit"
                colorScheme="orange"
                size="lg"
                width="full"
                isLoading={loading}
                loadingText="Sending recovery email..."
                isDisabled={!email}
              >
                Send Recovery Email
              </Button>
            </VStack>
          </form>
        )}

        {step === 'code' && (
          <VStack spacing={4} width="full">
            <FormControl>
              <FormLabel color="gray.300" textAlign="center">
                Recovery Code
              </FormLabel>
              <HStack justify="center">
                <PinInput
                  value={recoveryCode}
                  onChange={setRecoveryCode}
                  size="lg"
                  placeholder=""
                  onComplete={handleVerifyCode}
                >
                  <PinInputField bg="gray.700" borderColor="gray.600" color="white" _focus={{ borderColor: 'orange.400' }} />
                  <PinInputField bg="gray.700" borderColor="gray.600" color="white" _focus={{ borderColor: 'orange.400' }} />
                  <PinInputField bg="gray.700" borderColor="gray.600" color="white" _focus={{ borderColor: 'orange.400' }} />
                  <PinInputField bg="gray.700" borderColor="gray.600" color="white" _focus={{ borderColor: 'orange.400' }} />
                  <PinInputField bg="gray.700" borderColor="gray.600" color="white" _focus={{ borderColor: 'orange.400' }} />
                  <PinInputField bg="gray.700" borderColor="gray.600" color="white" _focus={{ borderColor: 'orange.400' }} />
                </PinInput>
              </HStack>
            </FormControl>

            <Button
              colorScheme="orange"
              size="lg"
              width="full"
              onClick={handleVerifyCode}
              isLoading={loading}
              loadingText="Verifying code..."
              isDisabled={recoveryCode.length !== 6}
            >
              Verify Recovery Code
            </Button>

            <Divider />

            <VStack spacing={2}>
              <Text color="gray.400" fontSize="sm" textAlign="center">
                Didn't receive the code?
              </Text>
              <Button
                variant="link"
                colorScheme="orange"
                size="sm"
                onClick={handleRequestNewCode}
                isDisabled={loading}
              >
                Request new recovery email
              </Button>
            </VStack>
          </VStack>
        )}

        <Divider />

        <Button
          variant="outline"
          colorScheme="gray"
          onClick={onCancel}
          isDisabled={loading}
        >
          Back to Sign In
        </Button>
      </VStack>
    </Box>
  );
}
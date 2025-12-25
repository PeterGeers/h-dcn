import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  VStack,
  Text,
  Alert,
  AlertIcon,
  Heading,
  Progress,
  Icon,
  HStack,
  useToast,
} from '@chakra-ui/react';
import { InfoIcon, CheckIcon } from '@chakra-ui/icons';
import { WebAuthnService } from '../../services/webAuthnService';

interface CrossDeviceAuthProps {
  userEmail: string;
  onSuccess: (credential: any) => void;
  onCancel: () => void;
  onError?: (error: string) => void;
}

export function CrossDeviceAuth({ userEmail, onSuccess, onCancel, onError }: CrossDeviceAuthProps) {
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'instructions' | 'waiting' | 'success'>('instructions');
  const [error, setError] = useState('');
  const [timeRemaining, setTimeRemaining] = useState(300); // 5 minutes
  const toast = useToast();

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (step === 'waiting' && timeRemaining > 0) {
      interval = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            setError('Tijd verlopen. Probeer opnieuw.');
            setStep('instructions');
            return 300;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [step, timeRemaining]);

  const startCrossDeviceAuth = async () => {
    setLoading(true);
    setError('');

    try {
      // Step 1: Get authentication options from the server
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/passkey/authenticate/begin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: userEmail,
          crossDevice: true,
        }),
      });

      if (!response.ok) {
        throw new Error('Kon cross-device authenticatie niet starten');
      }

      const authOptions = await response.json();
      setStep('waiting');
      setTimeRemaining(300);

      // Step 2: Start WebAuthn authentication with cross-device options
      const crossDeviceOptions = WebAuthnService.createCrossDeviceAuthOptions(authOptions.challenge);
      
      const credential = await WebAuthnService.authenticateWithPasskey(crossDeviceOptions);

      // Step 3: Verify the credential with the server
      const credentialJSON = WebAuthnService.credentialToJSON(credential);
      
      const verificationResponse = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/passkey/authenticate/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: userEmail,
          credential: credentialJSON,
          crossDevice: true,
        }),
      });

      if (!verificationResponse.ok) {
        throw new Error('Cross-device authenticatie verificatie mislukt');
      }

      const result = await verificationResponse.json();
      setStep('success');
      
      toast({
        title: 'Cross-device authenticatie succesvol!',
        description: 'Je bent ingelogd met je passkey van een ander apparaat',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });

      setTimeout(() => {
        onSuccess(result);
      }, 2000);

    } catch (err: any) {
      console.error('Cross-device authentication error:', err);
      const errorMessage = err.message || 'Cross-device authenticatie mislukt';
      setError(errorMessage);
      if (onError) onError(errorMessage);
      setStep('instructions');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const renderInstructions = () => (
    <VStack spacing={6}>
      <Box textAlign="center">
        <Heading color="orange.400" size="md">Inloggen met Ander Apparaat</Heading>
        <Text color="gray.400" mt={2}>
          Gebruik een passkey die je op een ander apparaat hebt ingesteld
        </Text>
      </Box>

      <Alert status="info" bg="blue.900" borderColor="blue.500" border="1px solid">
        <AlertIcon color="blue.300" />
        <Box>
          <Text color="blue.100" fontWeight="bold">Cross-Device Authenticatie</Text>
          <Text color="blue.200" fontSize="sm" mt={1}>
            Je kunt inloggen met een passkey die je op je telefoon, tablet, of ander apparaat hebt ingesteld.
          </Text>
        </Box>
      </Alert>

      <Box w="full">
        <Text color="gray.300" mb={4} fontWeight="bold">Hoe werkt het:</Text>
        <VStack spacing={3} align="start">
          <HStack>
            <Icon as={InfoIcon} color="orange.400" />
            <Text color="gray.300">
              Klik op "Start Cross-Device Authenticatie"
            </Text>
          </HStack>
          <HStack>
            <Icon as={InfoIcon} color="orange.400" />
            <Text color="gray.300">
              Je browser toont een QR-code of andere instructies
            </Text>
          </HStack>
          <HStack>
            <Icon as={InfoIcon} color="orange.400" />
            <Text color="gray.300">
              Gebruik je telefoon of ander apparaat om de authenticatie te voltooien
            </Text>
          </HStack>
          <HStack>
            <Icon as={InfoIcon} color="orange.400" />
            <Text color="gray.300">
              Je wordt automatisch ingelogd na succesvolle authenticatie
            </Text>
          </HStack>
        </VStack>
      </Box>

      {error && (
        <Alert status="error" bg="red.900" borderColor="red.500" border="1px solid">
          <AlertIcon color="red.300" />
          <Text color="red.100">{error}</Text>
        </Alert>
      )}

      <VStack spacing={3} w="full">
        <Button
          colorScheme="orange"
          size="lg"
          width="full"
          onClick={startCrossDeviceAuth}
          isLoading={loading}
          loadingText="Starten..."
        >
          Start Cross-Device Authenticatie
        </Button>
        
        <Button
          variant="ghost"
          colorScheme="gray"
          size="md"
          onClick={onCancel}
          isDisabled={loading}
        >
          Annuleren
        </Button>
      </VStack>
    </VStack>
  );

  const renderWaiting = () => (
    <VStack spacing={6}>
      <Box textAlign="center">
        <Heading color="orange.400" size="md">Wachten op Authenticatie</Heading>
        <Text color="gray.400" mt={2}>
          Volg de instructies van je browser om in te loggen met je andere apparaat
        </Text>
      </Box>

      <Box w="full" textAlign="center">
        <Text color="orange.300" fontSize="2xl" fontWeight="bold" mb={2}>
          {formatTime(timeRemaining)}
        </Text>
        <Progress 
          value={(300 - timeRemaining) / 300 * 100} 
          colorScheme="orange" 
          size="lg" 
          w="full" 
        />
        <Text color="gray.400" fontSize="sm" mt={2}>
          Tijd resterend voor authenticatie
        </Text>
      </Box>

      <Alert status="info" bg="blue.900" borderColor="blue.500" border="1px solid">
        <AlertIcon color="blue.300" />
        <Box>
          <Text color="blue.100" fontWeight="bold">Authenticatie in uitvoering...</Text>
          <Text color="blue.200" fontSize="sm" mt={1}>
            Gebruik je telefoon, tablet, of ander apparaat om de authenticatie te voltooien.
            Je browser kan een QR-code tonen of andere instructies geven.
          </Text>
        </Box>
      </Alert>

      <Button
        variant="outline"
        colorScheme="gray"
        size="md"
        onClick={() => {
          setStep('instructions');
          setTimeRemaining(300);
        }}
      >
        Annuleren
      </Button>
    </VStack>
  );

  const renderSuccess = () => (
    <VStack spacing={6}>
      <Box textAlign="center">
        <Heading color="green.400" size="md">Authenticatie Succesvol!</Heading>
        <Text color="gray.400" mt={2}>
          Je bent ingelogd met je passkey van een ander apparaat
        </Text>
      </Box>

      <Progress value={100} colorScheme="green" size="lg" w="full" />

      <Alert status="success" bg="green.900" borderColor="green.500" border="1px solid">
        <AlertIcon color="green.300" />
        <Box>
          <Text color="green.100" fontWeight="bold">Klaar!</Text>
          <Text color="green.200" fontSize="sm" mt={1}>
            Cross-device authenticatie succesvol voltooid. Je wordt doorgestuurd naar het dashboard.
          </Text>
        </Box>
      </Alert>

      <Text color="gray.400" fontSize="sm" textAlign="center">
        Je wordt automatisch doorgestuurd...
      </Text>
    </VStack>
  );

  return (
    <Box maxW="md" mx="auto" p={6}>
      {step === 'instructions' && renderInstructions()}
      {step === 'waiting' && renderWaiting()}
      {step === 'success' && renderSuccess()}
    </Box>
  );
}
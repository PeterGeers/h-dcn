import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  VStack,
  Text,
  Alert,
  AlertIcon,
  Heading,
  Icon,
  Progress,
  List,
  ListItem,
  ListIcon,
  useToast,
} from '@chakra-ui/react';
import { CheckIcon, WarningIcon } from '@chakra-ui/icons';
import { WebAuthnService } from '../../services/webAuthnService';
import { getWebAuthnRPID } from '../../utils/webauthnConfig';

interface PasskeySetupProps {
  userEmail: string;
  onSuccess: (credential?: any) => void;
  onSkip?: () => void;
  onError?: (error: string) => void;
  isRecovery?: boolean;
}

interface BrowserCompatibility {
  webAuthnSupported: boolean;
  platformAuthenticator: boolean;
  browserName: string;
  isMobile: boolean;
  isSupported: boolean;
  recommendedAttachment: 'platform' | 'cross-platform' | undefined;
}

export function PasskeySetup({ userEmail, onSuccess, onSkip, onError, isRecovery = false }: PasskeySetupProps) {
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'check' | 'setup' | 'register' | 'complete'>('check');
  const [error, setError] = useState('');
  const [compatibility, setCompatibility] = useState<BrowserCompatibility | null>(null);
  const toast = useToast();

  useEffect(() => {
    checkBrowserCompatibility();
  }, []);

  const checkBrowserCompatibility = async () => {
    const webAuthnSupported = WebAuthnService.isSupported();
    const platformAuthenticator = await WebAuthnService.isPlatformAuthenticatorAvailable();
    const browserInfo = WebAuthnService.getBrowserInfo();
    
    // Detect browser name from user agent
    const userAgent = browserInfo.userAgent.toLowerCase();
    let browserName = 'Onbekend';
    
    if (userAgent.includes('chrome')) browserName = 'Chrome';
    else if (userAgent.includes('firefox')) browserName = 'Firefox';
    else if (userAgent.includes('safari')) browserName = 'Safari';
    else if (userAgent.includes('edge')) browserName = 'Edge';

    const isMobile = browserInfo.isMobile;
    
    // Mobile devices generally have better WebAuthn support
    const isSupported = webAuthnSupported && (
      platformAuthenticator || 
      isMobile || 
      browserName === 'Chrome' || 
      browserName === 'Edge' ||
      browserName === 'Safari'
    );

    setCompatibility({
      webAuthnSupported,
      platformAuthenticator,
      browserName,
      isMobile,
      isSupported,
      recommendedAttachment: browserInfo.recommendedAttachment,
    });

    if (isSupported) {
      setStep('setup');
    } else {
      setStep('check');
    }
  };

  const handlePasskeyRegistration = async () => {
    if (!compatibility?.isSupported) {
      setError('Passkeys worden niet ondersteund op dit apparaat');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Step 1: Get registration options from the server
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/passkey/register/begin?t=${Date.now()}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: userEmail,
        }),
      });

      if (!response.ok) {
        throw new Error('Kon passkey registratie niet starten');
      }

      const registrationOptions = await response.json();

      setStep('register');

      // Step 2: Create the passkey using WebAuthn
      const credential = await WebAuthnService.registerPasskey({
        challenge: registrationOptions.challenge,
        rp: registrationOptions.rp || {
          // Fallback to client-side RP if server doesn't provide it (for backward compatibility)
          name: 'H-DCN Portal',
          id: getWebAuthnRPID(),
        },
        user: registrationOptions.user || {
          // Fallback to email if server doesn't provide user info
          id: userEmail,
          name: userEmail,
          displayName: userEmail,
        },
        pubKeyCredParams: [
          { type: 'public-key', alg: -7 }, // ES256
          { type: 'public-key', alg: -257 }, // RS256
        ],
        authenticatorSelection: {
          authenticatorAttachment: compatibility?.recommendedAttachment || (WebAuthnService.isMobileDevice() ? 'platform' : 'platform'),
          userVerification: 'preferred',
          requireResidentKey: false,
        },
        timeout: WebAuthnService.isMobileDevice() ? 120000 : 60000, // 2 minutes for mobile, 1 minute for desktop
        attestation: 'none',
      });

      // Step 3: Send the credential to the server for verification
      const credentialJSON = WebAuthnService.credentialToJSON(credential);
      
      const verificationResponse = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/passkey/register/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: userEmail,
          credential: credentialJSON,
        }),
      });

      if (!verificationResponse.ok) {
        throw new Error('Passkey registratie verificatie mislukt');
      }

      setStep('complete');
      
      toast({
        title: 'Passkey succesvol geregistreerd!',
        description: 'Je kunt nu inloggen met je passkey',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });

      setTimeout(() => {
        if (isRecovery) {
          onSuccess(credentialJSON);
        } else {
          onSuccess();
        }
      }, 2000);

    } catch (err: any) {
      console.error('Passkey registration error:', err);
      const errorMessage = err.message || 'Passkey registratie mislukt';
      setError(errorMessage);
      if (onError) onError(errorMessage);
      setStep('setup');
    } finally {
      setLoading(false);
    }
  };

  const renderCompatibilityCheck = () => (
    <VStack spacing={6}>
      <Box textAlign="center">
        <Heading color="orange.400" size="md">Passkey Ondersteuning Controleren</Heading>
        <Text color="gray.400" mt={2}>
          We controleren of je apparaat passkeys ondersteunt
        </Text>
      </Box>

      {compatibility && (
        <Box w="full">
          <List spacing={3}>
            <ListItem color={compatibility.webAuthnSupported ? 'green.300' : 'red.300'}>
              <ListIcon as={compatibility.webAuthnSupported ? CheckIcon : WarningIcon} />
              WebAuthn API: {compatibility.webAuthnSupported ? 'Ondersteund' : 'Niet ondersteund'}
            </ListItem>
            <ListItem color={compatibility.platformAuthenticator ? 'green.300' : 'yellow.300'}>
              <ListIcon as={compatibility.platformAuthenticator ? CheckIcon : WarningIcon} />
              Platform Authenticator: {compatibility.platformAuthenticator ? 'Beschikbaar' : 'Niet beschikbaar'}
            </ListItem>
            <ListItem color="blue.300">
              <ListIcon as={CheckIcon} />
              Browser: {compatibility.browserName}
            </ListItem>
            <ListItem color={compatibility.isMobile ? 'green.300' : 'blue.300'}>
              <ListIcon as={CheckIcon} />
              Apparaat: {compatibility.isMobile ? 'Mobiel' : 'Desktop'}
            </ListItem>
            {compatibility.recommendedAttachment && (
              <ListItem color="orange.300">
                <ListIcon as={CheckIcon} />
                Aanbevolen: {compatibility.recommendedAttachment === 'platform' ? 'Ingebouwde authenticatie' : 'Externe authenticatie'}
              </ListItem>
            )}
          </List>

          {!compatibility.isSupported && (
            <Alert status="warning" mt={4} bg="yellow.900" borderColor="yellow.500" border="1px solid">
              <AlertIcon color="yellow.300" />
              <Box>
                <Text color="yellow.100" fontWeight="bold">Passkeys niet volledig ondersteund</Text>
                <Text color="yellow.200" fontSize="sm" mt={1}>
                  {compatibility.isMobile 
                    ? 'Voor mobiele apparaten: gebruik Safari op iOS 14+ of Chrome op Android 7+.'
                    : 'Voor de beste ervaring gebruik Chrome, Edge, of Safari op een apparaat met biometrische authenticatie.'
                  }
                </Text>
              </Box>
            </Alert>
          )}

          {compatibility.isSupported && (
            <Alert status="success" mt={4} bg="green.900" borderColor="green.500" border="1px solid">
              <AlertIcon color="green.300" />
              <Text color="green.100">
                Je apparaat ondersteunt passkeys! Je kunt doorgaan met de setup.
              </Text>
            </Alert>
          )}
        </Box>
      )}

      <VStack spacing={3} w="full">
        {compatibility?.isSupported && (
          <Button
            colorScheme="orange"
            size="lg"
            width="full"
            onClick={() => setStep('setup')}
          >
            Doorgaan met Passkey Setup
          </Button>
        )}
        
        {onSkip && (
          <Button
            variant="ghost"
            colorScheme="gray"
            size="md"
            onClick={onSkip}
          >
            Overslaan (Email Recovery Gebruiken)
          </Button>
        )}
      </VStack>
    </VStack>
  );

  const renderSetupInstructions = () => (
    <VStack spacing={6}>
      <Box textAlign="center">
        <Heading color="orange.400" size="md">Passkey Instellen</Heading>
        <Text color="gray.400" mt={2}>
          Stel een passkey in voor veilig en gemakkelijk inloggen
        </Text>
      </Box>

      <Box w="full">
        <Text color="gray.300" mb={4} fontWeight="bold">Wat gebeurt er nu:</Text>
        <List spacing={2}>
          <ListItem color="gray.300">
            <ListIcon as={CheckIcon} color="orange.400" />
            Je browser vraagt om een passkey aan te maken
          </ListItem>
          <ListItem color="gray.300">
            <ListIcon as={CheckIcon} color="orange.400" />
            {compatibility?.isMobile 
              ? 'Gebruik je vingerafdruk, gezichtsherkenning, of apparaat-PIN'
              : 'Gebruik je vingerafdruk, gezichtsherkenning, of apparaat-PIN'
            }
          </ListItem>
          <ListItem color="gray.300">
            <ListIcon as={CheckIcon} color="orange.400" />
            Je passkey wordt veilig opgeslagen op dit apparaat
          </ListItem>
          {compatibility?.isMobile && (
            <ListItem color="gray.300">
              <ListIcon as={CheckIcon} color="orange.400" />
              Op mobiele apparaten werkt dit meestal met je schermvergrendeling
            </ListItem>
          )}
        </List>
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
          onClick={handlePasskeyRegistration}
          isLoading={loading}
          loadingText="Passkey aanmaken..."
        >
          Passkey Aanmaken
        </Button>
        
        {onSkip && (
          <Button
            variant="ghost"
            colorScheme="gray"
            size="md"
            onClick={onSkip}
            isDisabled={loading}
          >
            Overslaan (Email Recovery Gebruiken)
          </Button>
        )}
      </VStack>
    </VStack>
  );

  const renderRegistrationProgress = () => (
    <VStack spacing={6}>
      <Box textAlign="center">
        <Heading color="orange.400" size="md">Passkey Registreren</Heading>
        <Text color="gray.400" mt={2}>
          Volg de instructies van je browser om de passkey aan te maken
        </Text>
      </Box>

      <Progress value={75} colorScheme="orange" size="lg" w="full" />

      <Alert status="info" bg="blue.900" borderColor="blue.500" border="1px solid">
        <AlertIcon color="blue.300" />
        <Box>
          <Text color="blue.100" fontWeight="bold">Passkey wordt aangemaakt...</Text>
          <Text color="blue.200" fontSize="sm" mt={1}>
            Gebruik je vingerafdruk, gezichtsherkenning, of apparaat-PIN wanneer je browser daarom vraagt.
          </Text>
        </Box>
      </Alert>
    </VStack>
  );

  const renderComplete = () => (
    <VStack spacing={6}>
      <Box textAlign="center">
        <Heading color="green.400" size="md">Passkey Succesvol Ingesteld!</Heading>
        <Text color="gray.400" mt={2}>
          Je kunt nu inloggen met je passkey
        </Text>
      </Box>

      <Progress value={100} colorScheme="green" size="lg" w="full" />

      <Alert status="success" bg="green.900" borderColor="green.500" border="1px solid">
        <AlertIcon color="green.300" />
        <Box>
          <Text color="green.100" fontWeight="bold">Klaar!</Text>
          <Text color="green.200" fontSize="sm" mt={1}>
            Je passkey is veilig opgeslagen. Bij je volgende bezoek kun je inloggen met biometrische authenticatie.
          </Text>
        </Box>
      </Alert>

      <Text color="gray.400" fontSize="sm" textAlign="center">
        Je wordt automatisch doorgestuurd naar het dashboard...
      </Text>
    </VStack>
  );

  return (
    <Box maxW="md" mx="auto" p={6}>
      {step === 'check' && renderCompatibilityCheck()}
      {step === 'setup' && renderSetupInstructions()}
      {step === 'register' && renderRegistrationProgress()}
      {step === 'complete' && renderComplete()}
    </Box>
  );
}
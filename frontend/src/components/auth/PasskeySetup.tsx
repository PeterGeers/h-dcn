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
  List,
  ListItem,
  ListIcon,
  useToast,
} from '@chakra-ui/react';
import { CheckIcon, WarningIcon } from '@chakra-ui/icons';
import { associateWebAuthnCredential } from 'aws-amplify/auth';
import { fetchUserAttributes } from 'aws-amplify/auth';

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
}

type SetupStep = 'check' | 'verify-email' | 'setup' | 'migration' | 'register' | 'complete';

export function PasskeySetup({ userEmail, onSuccess, onSkip, onError, isRecovery = false }: PasskeySetupProps) {
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<SetupStep>('check');
  const [error, setError] = useState('');
  const [compatibility, setCompatibility] = useState<BrowserCompatibility | null>(null);
  const [emailVerified, setEmailVerified] = useState<boolean | null>(null);
  const [needsMigration, setNeedsMigration] = useState(false);
  const toast = useToast();

  useEffect(() => {
    checkBrowserCompatibility();
    checkEmailVerification();
    checkMigrationStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkBrowserCompatibility = async () => {
    const webAuthnSupported = window.PublicKeyCredential !== undefined;
    let platformAuthenticator = false;
    
    if (webAuthnSupported) {
      try {
        platformAuthenticator = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
      } catch {
        platformAuthenticator = false;
      }
    }

    const userAgent = navigator.userAgent.toLowerCase();
    let browserName = 'Onbekend';
    if (userAgent.includes('chrome')) browserName = 'Chrome';
    else if (userAgent.includes('firefox')) browserName = 'Firefox';
    else if (userAgent.includes('safari')) browserName = 'Safari';
    else if (userAgent.includes('edge')) browserName = 'Edge';

    const isMobile = /android|iphone|ipad|ipod/i.test(navigator.userAgent);
    const isSupported = webAuthnSupported && (
      platformAuthenticator || isMobile || 
      browserName === 'Chrome' || browserName === 'Edge' || browserName === 'Safari'
    );

    setCompatibility({ webAuthnSupported, platformAuthenticator, browserName, isMobile, isSupported });

    if (isSupported) {
      setStep('setup');
    }
  };

  const checkEmailVerification = async () => {
    try {
      const attributes = await fetchUserAttributes();
      const verified = attributes.email_verified === 'true';
      setEmailVerified(verified);
      if (!verified) {
        setStep('verify-email');
      }
    } catch (err) {
      // If we can't fetch attributes, assume not verified
      setEmailVerified(false);
      setStep('verify-email');
    }
  };

  const checkMigrationStatus = async () => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_BASE_URL}/auth/passkey/migrate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: userEmail }),
        }
      );
      if (response.ok) {
        const data = await response.json();
        if (data.needsMigration) {
          setNeedsMigration(true);
        }
      }
    } catch {
      // Migration check is best-effort
    }
  };

  const handlePasskeyRegistration = async () => {
    if (!compatibility?.isSupported) {
      setError('Passkeys worden niet ondersteund op dit apparaat');
      return;
    }

    if (!emailVerified) {
      setError('E-mailverificatie is vereist voordat je een passkey kunt aanmaken');
      setStep('verify-email');
      return;
    }

    setLoading(true);
    setError('');

    try {
      setStep('register');

      // Use Cognito native WebAuthn via Amplify v6
      await associateWebAuthnCredential();

      setStep('complete');
      
      toast({
        title: 'Passkey succesvol geregistreerd!',
        description: 'Je kunt nu inloggen met je passkey',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });

      setTimeout(() => {
        onSuccess();
      }, 2000);

    } catch (err: any) {
      console.error('Passkey registration error:', err);
      
      // Provide specific, actionable error messages
      let errorMessage = 'Passkey registratie mislukt';
      if (err.name === 'NotAllowedError') {
        errorMessage = 'Passkey niet ondersteund op dit apparaat of de actie is geannuleerd';
      } else if (err.message?.includes('email') || err.message?.includes('verified')) {
        errorMessage = 'E-mailverificatie is vereist. Verifieer eerst je e-mailadres.';
        setStep('verify-email');
      } else if (err.message?.includes('not supported')) {
        errorMessage = 'Passkeys worden niet ondersteund op dit apparaat of in deze browser';
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      if (onError) onError(errorMessage);
      if (step === 'register') setStep('setup');
    } finally {
      setLoading(false);
    }
  };

  const renderEmailVerification = () => (
    <VStack spacing={6}>
      <Box textAlign="center">
        <Heading color="orange.400" size="md">E-mail Verificatie Vereist</Heading>
        <Text color="gray.400" mt={2}>
          Je moet eerst je e-mailadres verifiëren voordat je een passkey kunt aanmaken.
        </Text>
      </Box>

      <Alert status="warning" bg="yellow.900" borderColor="yellow.500" border="1px solid">
        <AlertIcon color="yellow.300" />
        <Box>
          <Text color="yellow.100" fontWeight="bold">E-mail niet geverifieerd</Text>
          <Text color="yellow.200" fontSize="sm" mt={1}>
            Controleer je inbox ({userEmail}) voor een verificatiecode en bevestig je e-mailadres.
          </Text>
        </Box>
      </Alert>

      <VStack spacing={3} w="full">
        {onSkip && (
          <Button
            variant="ghost"
            colorScheme="gray"
            size="md"
            onClick={onSkip}
          >
            Overslaan
          </Button>
        )}
      </VStack>
    </VStack>
  );

  const renderMigrationNotice = () => (
    <Alert status="info" bg="blue.900" borderColor="blue.500" border="1px solid" mb={4}>
      <AlertIcon color="blue.300" />
      <Box>
        <Text color="blue.100" fontWeight="bold">Passkey opnieuw instellen</Text>
        <Text color="blue.200" fontSize="sm" mt={1}>
          Je had eerder een passkey ingesteld met het oude systeem. 
          Registreer een nieuwe passkey om weer passwordless in te loggen.
        </Text>
      </Box>
    </Alert>
  );

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
          </List>

          {!compatibility.isSupported && (
            <Alert status="warning" mt={4} bg="yellow.900" borderColor="yellow.500" border="1px solid">
              <AlertIcon color="yellow.300" />
              <Box>
                <Text color="yellow.100" fontWeight="bold">Passkeys niet volledig ondersteund</Text>
                <Text color="yellow.200" fontSize="sm" mt={1}>
                  Gebruik Chrome, Edge, of Safari op een apparaat met biometrische authenticatie.
                </Text>
              </Box>
            </Alert>
          )}
        </Box>
      )}

      {onSkip && (
        <Button variant="ghost" colorScheme="gray" size="md" onClick={onSkip}>
          Overslaan (Email Recovery Gebruiken)
        </Button>
      )}
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

      {needsMigration && renderMigrationNotice()}

      <Box w="full">
        <Text color="gray.300" mb={4} fontWeight="bold">Wat gebeurt er nu:</Text>
        <List spacing={2}>
          <ListItem color="gray.300">
            <ListIcon as={CheckIcon} color="orange.400" />
            Je browser vraagt om een passkey aan te maken
          </ListItem>
          <ListItem color="gray.300">
            <ListIcon as={CheckIcon} color="orange.400" />
            Gebruik je vingerafdruk, gezichtsherkenning, of apparaat-PIN
          </ListItem>
          <ListItem color="gray.300">
            <ListIcon as={CheckIcon} color="orange.400" />
            Je passkey wordt veilig opgeslagen op dit apparaat
          </ListItem>
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
      {step === 'verify-email' && renderEmailVerification()}
      {step === 'setup' && renderSetupInstructions()}
      {step === 'register' && renderRegistrationProgress()}
      {step === 'complete' && renderComplete()}
    </Box>
  );
}

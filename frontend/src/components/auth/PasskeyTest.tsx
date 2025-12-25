import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  VStack,
  Text,
  Alert,
  AlertIcon,
  Heading,
  Code,
  List,
  ListItem,
  ListIcon,
  Badge,
} from '@chakra-ui/react';
import { CheckIcon, WarningIcon, InfoIcon } from '@chakra-ui/icons';
import { WebAuthnService } from '../../services/webAuthnService';

export function PasskeyTest() {
  const [testResults, setTestResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [browserInfo, setBrowserInfo] = useState<any>(null);

  useEffect(() => {
    checkBrowserSupport();
  }, []);

  const checkBrowserSupport = async () => {
    const info = WebAuthnService.getBrowserInfo();
    const platformAuth = await WebAuthnService.isPlatformAuthenticatorAvailable();
    
    setBrowserInfo({
      ...info,
      platformAuthenticator: platformAuth,
    });

    addTestResult('Browser Support Check', {
      webAuthnSupported: info.webAuthnSupported,
      platformAuthenticator: platformAuth,
      userAgent: info.userAgent,
    }, info.webAuthnSupported);
  };

  const addTestResult = (testName: string, data: any, success: boolean) => {
    setTestResults(prev => [...prev, {
      name: testName,
      data,
      success,
      timestamp: new Date().toLocaleTimeString(),
    }]);
  };

  const testPasskeyRegistration = async () => {
    setLoading(true);
    
    try {
      // Test with mock data
      const testEmail = 'test@example.com';
      
      addTestResult('Starting Passkey Registration Test', { email: testEmail }, true);

      // Create mock registration options
      const mockOptions = {
        challenge: 'mock-challenge-' + Date.now(),
        rp: {
          name: 'H-DCN Test',
          id: window.location.hostname,
        },
        user: {
          id: testEmail,
          name: testEmail,
          displayName: testEmail,
        },
        pubKeyCredParams: [
          { type: 'public-key' as const, alg: -7 },
          { type: 'public-key' as const, alg: -257 },
        ],
        authenticatorSelection: {
          authenticatorAttachment: 'platform' as const,
          userVerification: 'preferred' as const,
          requireResidentKey: false,
        },
        timeout: 60000,
        attestation: 'none' as const,
      };

      addTestResult('Mock Registration Options Created', mockOptions, true);

      // Attempt to register passkey
      const credential = await WebAuthnService.registerPasskey(mockOptions);
      
      addTestResult('Passkey Registration Successful', {
        credentialId: credential.id,
        credentialType: credential.type,
      }, true);

      // Convert credential to JSON format
      const credentialJSON = WebAuthnService.credentialToJSON(credential);
      
      addTestResult('Credential Conversion Successful', {
        id: credentialJSON.id,
        type: credentialJSON.type,
        responseType: credentialJSON.response.attestationObject ? 'attestation' : 'assertion',
      }, true);

    } catch (error: any) {
      addTestResult('Passkey Registration Failed', {
        error: error.message,
        name: error.name,
      }, false);
    } finally {
      setLoading(false);
    }
  };

  const testPasskeyAuthentication = async () => {
    setLoading(true);
    
    try {
      const testEmail = 'test@example.com';
      
      addTestResult('Starting Passkey Authentication Test', { email: testEmail }, true);

      // Create mock authentication options
      const mockOptions = {
        challenge: 'mock-auth-challenge-' + Date.now(),
        timeout: 60000,
        userVerification: 'preferred' as const,
        allowCredentials: [], // Empty for resident key
      };

      addTestResult('Mock Authentication Options Created', mockOptions, true);

      // Attempt to authenticate with passkey
      const credential = await WebAuthnService.authenticateWithPasskey(mockOptions);
      
      addTestResult('Passkey Authentication Successful', {
        credentialId: credential.id,
        credentialType: credential.type,
      }, true);

      // Convert credential to JSON format
      const credentialJSON = WebAuthnService.credentialToJSON(credential);
      
      addTestResult('Authentication Credential Conversion Successful', {
        id: credentialJSON.id,
        type: credentialJSON.type,
        responseType: credentialJSON.response.signature ? 'assertion' : 'attestation',
      }, true);

    } catch (error: any) {
      addTestResult('Passkey Authentication Failed', {
        error: error.message,
        name: error.name,
      }, false);
    } finally {
      setLoading(false);
    }
  };

  const clearResults = () => {
    setTestResults([]);
  };

  return (
    <Box maxW="4xl" mx="auto" p={6}>
      <VStack spacing={6}>
        <Box textAlign="center">
          <Heading color="orange.400" size="lg">Passkey Test Suite</Heading>
          <Text color="gray.400" mt={2}>
            Test WebAuthn/Passkey functionality on this device
          </Text>
        </Box>

        {browserInfo && (
          <Box w="full" p={4} bg="gray.800" borderRadius="md">
            <Heading size="md" color="orange.400" mb={3}>Browser Information</Heading>
            <List spacing={2}>
              <ListItem color={browserInfo.webAuthnSupported ? 'green.300' : 'red.300'}>
                <ListIcon as={browserInfo.webAuthnSupported ? CheckIcon : WarningIcon} />
                WebAuthn API: {browserInfo.webAuthnSupported ? 'Supported' : 'Not Supported'}
              </ListItem>
              <ListItem color={browserInfo.platformAuthenticator ? 'green.300' : 'yellow.300'}>
                <ListIcon as={browserInfo.platformAuthenticator ? CheckIcon : InfoIcon} />
                Platform Authenticator: {browserInfo.platformAuthenticator ? 'Available' : 'Not Available'}
              </ListItem>
              <ListItem color="blue.300">
                <ListIcon as={InfoIcon} />
                User Agent: <Code fontSize="xs">{browserInfo.userAgent}</Code>
              </ListItem>
            </List>
          </Box>
        )}

        <VStack spacing={3} w="full">
          <Button
            colorScheme="orange"
            size="lg"
            width="full"
            onClick={testPasskeyRegistration}
            isLoading={loading}
            loadingText="Testing Registration..."
            isDisabled={!browserInfo?.webAuthnSupported}
          >
            Test Passkey Registration
          </Button>
          
          <Button
            colorScheme="blue"
            size="lg"
            width="full"
            onClick={testPasskeyAuthentication}
            isLoading={loading}
            loadingText="Testing Authentication..."
            isDisabled={!browserInfo?.webAuthnSupported}
          >
            Test Passkey Authentication
          </Button>

          <Button
            variant="outline"
            colorScheme="gray"
            size="md"
            onClick={clearResults}
          >
            Clear Results
          </Button>
        </VStack>

        {testResults.length > 0 && (
          <Box w="full" p={4} bg="gray.900" borderRadius="md">
            <Heading size="md" color="orange.400" mb={3}>Test Results</Heading>
            <VStack spacing={3} align="stretch">
              {testResults.map((result, index) => (
                <Box key={index} p={3} bg="gray.800" borderRadius="md">
                  <Box display="flex" alignItems="center" mb={2}>
                    <Badge colorScheme={result.success ? 'green' : 'red'} mr={2}>
                      {result.success ? 'PASS' : 'FAIL'}
                    </Badge>
                    <Text fontWeight="bold" color="white">{result.name}</Text>
                    <Text fontSize="sm" color="gray.400" ml="auto">{result.timestamp}</Text>
                  </Box>
                  <Code display="block" whiteSpace="pre-wrap" fontSize="xs" p={2}>
                    {JSON.stringify(result.data, null, 2)}
                  </Code>
                </Box>
              ))}
            </VStack>
          </Box>
        )}

        {!browserInfo?.webAuthnSupported && (
          <Alert status="error" bg="red.900" borderColor="red.500" border="1px solid">
            <AlertIcon color="red.300" />
            <Box>
              <Text color="red.100" fontWeight="bold">WebAuthn Not Supported</Text>
              <Text color="red.200" fontSize="sm" mt={1}>
                This browser does not support WebAuthn/Passkeys. Please use Chrome, Edge, Firefox, or Safari.
              </Text>
            </Box>
          </Alert>
        )}
      </VStack>
    </Box>
  );
}

export default PasskeyTest;
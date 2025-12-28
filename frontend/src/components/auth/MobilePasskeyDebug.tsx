import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  VStack,
  Text,
  Alert,
  AlertIcon,
  Code,
  Heading,
  Divider
} from '@chakra-ui/react';
import { WebAuthnService } from '../../services/webAuthnService';

interface MobilePasskeyDebugProps {
  userEmail: string;
}

export function MobilePasskeyDebug({ userEmail }: MobilePasskeyDebugProps) {
  const [debugInfo, setDebugInfo] = useState<any>(null);
  const [testResults, setTestResults] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Get browser info on component mount
    const browserInfo = WebAuthnService.getBrowserInfo();
    setDebugInfo(browserInfo);
    
    // Check platform authenticator availability
    WebAuthnService.isPlatformAuthenticatorAvailable().then(available => {
      setDebugInfo(prev => ({ ...prev, platformAuthenticator: available }));
    });
  }, []);

  const addTestResult = (message: string) => {
    setTestResults(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  const testPasskeySupport = async () => {
    setLoading(true);
    addTestResult('🔍 Testing passkey support...');
    
    try {
      // Test 1: Basic WebAuthn support
      const isSupported = WebAuthnService.isSupported();
      addTestResult(`✅ WebAuthn supported: ${isSupported}`);
      
      // Test 2: Platform authenticator availability
      const platformAvailable = await WebAuthnService.isPlatformAuthenticatorAvailable();
      addTestResult(`✅ Platform authenticator available: ${platformAvailable}`);
      
      // Test 3: Check if user has passkey registered
      addTestResult('🔍 Checking if user has passkey registered...');
      
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/passkey/authenticate/begin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: userEmail,
        }),
      });
      
      if (response.ok) {
        addTestResult('✅ User has passkey registered');
        const options = await response.json();
        addTestResult(`📋 Authentication options received: ${JSON.stringify(options, null, 2)}`);
      } else {
        const errorData = await response.json();
        if (errorData.code === 'NO_PASSKEY_REGISTERED') {
          addTestResult('❌ User has NO passkey registered');
          addTestResult('💡 Solution: User needs to set up a passkey first');
        } else {
          addTestResult(`❌ Error checking passkey: ${errorData.message}`);
        }
      }
      
    } catch (error: any) {
      addTestResult(`❌ Test failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const testPasskeyRegistration = async () => {
    setLoading(true);
    addTestResult('🔍 Testing passkey registration...');
    
    try {
      // Try to start passkey registration
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/passkey/register/begin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: userEmail,
        }),
      });
      
      if (response.ok) {
        const options = await response.json();
        addTestResult('✅ Registration options received');
        addTestResult(`📋 Registration options: ${JSON.stringify(options, null, 2)}`);
        
        // Try to create credential
        addTestResult('🔍 Attempting to create passkey...');
        const credential = await WebAuthnService.registerPasskey(options);
        addTestResult('✅ Passkey created successfully!');
        
        // Complete registration
        const credentialJSON = WebAuthnService.credentialToJSON(credential);
        const completeResponse = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/passkey/register/complete`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: userEmail,
            credential: credentialJSON,
          }),
        });
        
        if (completeResponse.ok) {
          addTestResult('✅ Passkey registration completed successfully!');
        } else {
          const errorData = await completeResponse.json();
          addTestResult(`❌ Registration completion failed: ${errorData.message}`);
        }
        
      } else {
        const errorData = await response.json();
        addTestResult(`❌ Registration failed: ${errorData.message}`);
      }
      
    } catch (error: any) {
      addTestResult(`❌ Registration test failed: ${error.message}`);
      
      // Provide specific guidance for common mobile errors
      if (error.name === 'NotAllowedError') {
        addTestResult('💡 This usually means the user cancelled or the browser blocked the request');
        addTestResult('💡 On mobile, make sure you allow biometric authentication when prompted');
      } else if (error.name === 'NotSupportedError') {
        addTestResult('💡 This browser/device does not support passkeys');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box maxW="md" w="full" p={6} bg="gray.900" borderRadius="md">
      <Heading color="orange.400" size="md" mb={4}>
        🔧 Mobile Passkey Debug Tool
      </Heading>
      
      <Text color="gray.300" mb={4}>
        Email: <Code colorScheme="orange">{userEmail}</Code>
      </Text>

      {debugInfo && (
        <Box mb={4}>
          <Text color="gray.300" fontWeight="bold" mb={2}>Browser Info:</Text>
          <Code colorScheme="gray" p={2} fontSize="xs" whiteSpace="pre-wrap">
            {JSON.stringify(debugInfo, null, 2)}
          </Code>
        </Box>
      )}

      <VStack spacing={3} mb={4}>
        <Button
          colorScheme="blue"
          size="sm"
          width="full"
          onClick={testPasskeySupport}
          isLoading={loading}
        >
          🔍 Test Passkey Support
        </Button>
        
        <Button
          colorScheme="green"
          size="sm"
          width="full"
          onClick={testPasskeyRegistration}
          isLoading={loading}
        >
          🔑 Test Passkey Registration
        </Button>
      </VStack>

      <Divider mb={4} />

      <Box>
        <Text color="gray.300" fontWeight="bold" mb={2}>Test Results:</Text>
        <Box
          bg="black"
          p={3}
          borderRadius="md"
          maxH="300px"
          overflowY="auto"
          border="1px solid"
          borderColor="gray.600"
        >
          {testResults.length === 0 ? (
            <Text color="gray.500" fontSize="sm">No tests run yet</Text>
          ) : (
            testResults.map((result, index) => (
              <Text key={index} color="gray.300" fontSize="sm" mb={1}>
                {result}
              </Text>
            ))
          )}
        </Box>
      </Box>

      <Alert status="info" mt={4} bg="blue.900" borderColor="blue.500">
        <AlertIcon color="blue.300" />
        <Box>
          <Text color="blue.100" fontSize="sm">
            This debug tool helps identify mobile passkey issues. 
            Run the tests to see what's happening with your passkey authentication.
          </Text>
        </Box>
      </Alert>
    </Box>
  );
}
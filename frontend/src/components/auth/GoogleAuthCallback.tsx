/**
 * Google Auth Callback Component
 * 
 * This component handles the OAuth callback from Google and processes
 * the authorization code to obtain access tokens.
 */

import React, { useEffect } from 'react';
import {
  Box,
  VStack,
  Spinner,
  Text,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Button
} from '@chakra-ui/react';
import { useGoogleAuthCallback } from '../../hooks/useGoogleMailIntegration';

// ============================================================================
// COMPONENT
// ============================================================================

export const GoogleAuthCallback: React.FC = () => {
  const { isProcessing, result, error, processCallback } = useGoogleAuthCallback();

  useEffect(() => {
    // Extract authorization code from URL
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const errorParam = urlParams.get('error');

    if (errorParam) {
      // Handle OAuth error
      const errorDescription = urlParams.get('error_description') || 'Authentication was cancelled or failed';
      
      if (window.opener) {
        window.opener.postMessage({ 
          type: 'GOOGLE_AUTH_ERROR', 
          error: errorDescription 
        }, '*');
        window.close();
      }
      return;
    }

    if (code) {
      // Process the authorization code
      processCallback(code).catch(console.error);
    } else {
      // No code parameter found
      if (window.opener) {
        window.opener.postMessage({ 
          type: 'GOOGLE_AUTH_ERROR', 
          error: 'No authorization code received' 
        }, '*');
        window.close();
      }
    }
  }, [processCallback]);

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <Box
      minH="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      bg="gray.50"
      p={4}
    >
      <Box
        maxW="md"
        w="full"
        bg="white"
        boxShadow="lg"
        rounded="lg"
        p={6}
      >
        <VStack spacing={6}>
          {isProcessing && (
            <>
              <Spinner size="xl" color="orange.500" thickness="4px" />
              <VStack spacing={2}>
                <Text fontSize="lg" fontWeight="semibold">
                  Completing Authentication
                </Text>
                <Text color="gray.600" textAlign="center">
                  Processing your Google authentication...
                </Text>
              </VStack>
            </>
          )}

          {result && (
            <Alert status="success" flexDirection="column" textAlign="center">
              <AlertIcon boxSize="40px" mr={0} />
              <AlertTitle mt={4} mb={1} fontSize="lg">
                Authentication Successful!
              </AlertTitle>
              <AlertDescription maxWidth="sm">
                You have successfully connected your Google account. 
                This window will close automatically.
              </AlertDescription>
            </Alert>
          )}

          {error && (
            <Alert status="error" flexDirection="column" textAlign="center">
              <AlertIcon boxSize="40px" mr={0} />
              <AlertTitle mt={4} mb={1} fontSize="lg">
                Authentication Failed
              </AlertTitle>
              <AlertDescription maxWidth="sm" mb={4}>
                {error}
              </AlertDescription>
              <Button
                colorScheme="red"
                size="sm"
                onClick={() => window.close()}
              >
                Close Window
              </Button>
            </Alert>
          )}

          {!isProcessing && !result && !error && (
            <Alert status="warning" flexDirection="column" textAlign="center">
              <AlertIcon boxSize="40px" mr={0} />
              <AlertTitle mt={4} mb={1} fontSize="lg">
                Processing Authentication
              </AlertTitle>
              <AlertDescription maxWidth="sm">
                Please wait while we process your authentication...
              </AlertDescription>
            </Alert>
          )}
        </VStack>
      </Box>
    </Box>
  );
};

export default GoogleAuthCallback;
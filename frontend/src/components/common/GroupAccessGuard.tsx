import React, { ReactNode } from 'react';
import { Box, VStack, Heading, Text, Button, Alert, AlertIcon } from '@chakra-ui/react';

interface CognitoUser {
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: string[];
      };
      jwtToken?: string;
    };
  };
  attributes?: {
    email?: string;
  };
  username?: string;
}

interface GroupAccessGuardProps {
  user: CognitoUser;
  children: ReactNode;
  signOut: () => void;
}

function GroupAccessGuard({ user, children, signOut }: GroupAccessGuardProps) {
  // Try to get groups from different possible locations
  let userGroups: string[] = [];
  
  // First, try the standard Amplify location
  const amplifyGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'];
  if (amplifyGroups && Array.isArray(amplifyGroups)) {
    userGroups = amplifyGroups;
  } else {
    // If not found, try to decode the JWT token directly
    const jwtToken = user.signInUserSession?.accessToken?.jwtToken;
    if (jwtToken) {
      try {
        // Decode JWT payload (base64 decode the middle part)
        const parts = jwtToken.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1]));
          userGroups = payload['cognito:groups'] || [];
        }
      } catch (error) {
        console.error('Error decoding JWT token:', error);
      }
    }
  }
  
  const hasGroupAccess = userGroups.length > 0;
  
  if (!hasGroupAccess) {
    return (
      <Box minH="100vh" bg="black" display="flex" alignItems="center" justifyContent="center">
        <VStack spacing={6} maxW="500px" p={8} textAlign="center">
          <Alert status="warning" bg="orange.100" color="black" borderRadius="md">
            <AlertIcon />
            Geen toegang
          </Alert>
          
          <Heading color="orange.400" size="lg">
            Toegang Geweigerd
          </Heading>
          
          <Text color="gray.300" fontSize="lg">
            Je account heeft geen toegang tot deze applicatie. 
            Neem contact op met de beheerder om toegang te krijgen.
          </Text>
          
          <Text color="gray.400" fontSize="sm">
            Account: {user?.attributes?.email || user?.username}
          </Text>
          
          <Button onClick={signOut} colorScheme="orange" size="lg">
            Uitloggen
          </Button>
        </VStack>
      </Box>
    );
  }

  return <>{children}</>;
}

export default GroupAccessGuard;
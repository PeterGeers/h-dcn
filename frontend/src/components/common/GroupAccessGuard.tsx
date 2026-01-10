import React, { ReactNode, useEffect, useState } from 'react';
import { Box, VStack, Heading, Text, Button, Alert, AlertIcon, Spinner, Center } from '@chakra-ui/react';
import { useLocation } from 'react-router-dom';
import { membershipService } from '../../utils/membershipService';

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
  const location = useLocation();
  
  // Routes that applicants (verzoek_lid) can access
  const applicantAllowedRoutes = [
    '/new-member-application',
    '/application-submitted'
  ];
  
  // Routes that users without any groups can access
  const newUserAllowedRoutes = [
    '/',                        // Dashboard (for redirect logic)
    '/new-member-application',
    '/application-submitted'
  ];
  
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
  
  // Check user status
  const isApplicant = userGroups.includes('verzoek_lid');
  const hasFullAccess = userGroups.some(group => 
    group !== 'verzoek_lid' && group.length > 0
  );
  const hasNoGroups = userGroups.length === 0;
  
  // Debug logging
  console.log('GroupAccessGuard - User groups:', userGroups);
  console.log('GroupAccessGuard - Is applicant:', isApplicant);
  console.log('GroupAccessGuard - Has full access:', hasFullAccess);
  console.log('GroupAccessGuard - Current route:', location.pathname);
  
  // Handle applicants (verzoek_lid users)
  if (isApplicant && !hasFullAccess) {
    const isApplicantRoute = applicantAllowedRoutes.includes(location.pathname);
    
    if (!isApplicantRoute) {
      return (
        <Box minH="100vh" bg="black" display="flex" alignItems="center" justifyContent="center">
          <VStack spacing={6} maxW="500px" p={8} textAlign="center">
            <Alert status="info" bg="orange.100" color="black" borderRadius="md">
              <AlertIcon />
              Lidmaatschapsaanvraag in behandeling
            </Alert>
            
            <Heading color="orange.400" size="lg">
              Aanvraag wordt beoordeeld
            </Heading>
            
            <Text color="gray.300" fontSize="lg">
              Je lidmaatschapsaanvraag wordt momenteel beoordeeld door onze administratie.
            </Text>
            
            <Text color="gray.300" fontSize="md">
              Dit proces kan tot een week duren. Je ontvangt een e-mail zodra je aanvraag 
              is goedgekeurd en je toegang hebt tot het volledige portaal.
            </Text>
            
            <Text color="gray.400" fontSize="sm">
              Account: {user?.attributes?.email || user?.username}
            </Text>
            
            <VStack spacing={3}>
              <Button 
                onClick={() => window.location.href = '/new-member-application'} 
                colorScheme="orange" 
                size="lg"
              >
                Bekijk/Wijzig je aanvraag
              </Button>
              <Button onClick={signOut} variant="outline" colorScheme="gray" size="sm">
                Uitloggen
              </Button>
            </VStack>
          </VStack>
        </Box>
      );
    }
  }
  
  // Handle users with no groups
  if (hasNoGroups) {
    const isNewUserRoute = newUserAllowedRoutes.includes(location.pathname);
    
    if (!isNewUserRoute) {
      return (
        <Box minH="100vh" bg="black" display="flex" alignItems="center" justifyContent="center">
          <VStack spacing={6} maxW="500px" p={8} textAlign="center">
            <Alert status="info" bg="orange.100" color="black" borderRadius="md">
              <AlertIcon />
              Account wordt verwerkt
            </Alert>
            
            <Heading color="orange.400" size="lg">
              Account in behandeling
            </Heading>
            
            <Text color="gray.300" fontSize="lg">
              Je account wordt momenteel verwerkt. Dit kan enkele minuten duren.
            </Text>
            
            <Text color="gray.400" fontSize="sm">
              Account: {user?.attributes?.email || user?.username}
            </Text>
            
            <VStack spacing={3}>
              <Button onClick={signOut} colorScheme="orange" size="lg">
                Uitloggen
              </Button>
              <Button 
                onClick={() => window.location.reload()} 
                variant="outline" 
                colorScheme="gray" 
                size="sm"
              >
                Pagina vernieuwen
              </Button>
            </VStack>
          </VStack>
        </Box>
      );
    }
  }

  return <>{children}</>;
}

export default GroupAccessGuard;
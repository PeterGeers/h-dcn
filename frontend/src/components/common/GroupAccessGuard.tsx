/**
 * GroupAccessGuard - Route access control based on Cognito group membership.
 *
 * Uses the useAuth() hook to get user groups from the AuthProvider context.
 * No manual JWT decoding or localStorage reads.
 *
 * Requirements: R8.1, R4.2, R6.6
 */

import React, { ReactNode } from 'react';
import { Box, VStack, Heading, Text, Button, Alert, AlertIcon } from '@chakra-ui/react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

interface GroupAccessGuardProps {
  children: ReactNode;
}

function GroupAccessGuard({ children }: GroupAccessGuardProps) {
  const { user, signOut, isLoading } = useAuth();
  const location = useLocation();

  // While auth state is loading, render nothing (AuthProvider shows loading state)
  if (isLoading) {
    return null;
  }

  // If user is not authenticated, render nothing (AuthProvider/CustomAuthenticator handles login)
  if (!user) {
    return null;
  }

  const userGroups = user.groups;

  // Routes that applicants (verzoek_lid) can access
  const applicantAllowedRoutes = [
    '/',                        // Dashboard (for redirect logic)
    '/new-member-application',
    '/application-submitted',
    '/my-account'  // Allow verzoek_lid users to access MyAccount for self-service application
  ];

  // Routes that users without any groups can access
  const newUserAllowedRoutes = [
    '/',                        // Dashboard (for redirect logic)
    '/new-member-application',
    '/application-submitted'
  ];

  // Check user status
  const isApplicant = userGroups.includes('verzoek_lid');
  const hasFullAccess = userGroups.some(group =>
    group !== 'verzoek_lid' && group.length > 0
  );
  const hasNoGroups = userGroups.length === 0;

  // Note: event_participant users have hasFullAccess = true (they have a valid group)
  // so they pass through the guard and can access all routes including /events/:id/booking

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
              Account: {user.email}
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
              Account: {user.email}
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

import React from 'react';
import { Box, VStack, Heading, Text, Button, Alert, AlertIcon } from '@chakra-ui/react';

function GroupAccessGuard({ user, children, signOut }) {
  const userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
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

  return children;
}

export default GroupAccessGuard;
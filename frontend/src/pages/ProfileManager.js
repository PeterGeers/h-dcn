import React, { useState } from 'react';
import { Box, VStack, Heading, Text, Button, Alert, AlertIcon, useToast } from '@chakra-ui/react';

function ProfileManager({ user }) {
  const toast = useToast();



  return (
    <Box maxW="800px" mx="auto" p={6} bg="black" minH="100vh">
      <VStack spacing={6} align="stretch">
        <Heading color="orange.400">Mijn Profiel</Heading>

        <Box bg="gray.800" p={6} borderRadius="lg" border="1px" borderColor="orange.400">
          <VStack spacing={4} align="stretch">
            <Heading size="md" color="orange.400" mb={4}>Account Informatie</Heading>
            
            <Alert status="info" bg="gray.700" color="orange.200" borderColor="orange.400">
              <AlertIcon color="orange.400" />
              <Box>
                <Text><strong>Voornaam:</strong> {user?.attributes?.given_name || 'Niet beschikbaar'}</Text>
                <Text><strong>Achternaam:</strong> {user?.attributes?.family_name || 'Niet beschikbaar'}</Text>
                <Text><strong>Email:</strong> {user?.attributes?.email || 'Niet beschikbaar'}</Text>
                <Text><strong>Email geverifieerd:</strong> {user?.attributes?.email_verified ? 'Ja' : 'Nee'}</Text>
              </Box>
            </Alert>
            
            <Alert status="warning" bg="gray.700" color="orange.200" borderColor="orange.400">
              <AlertIcon color="orange.400" />
              <Box>
                <Text fontSize="sm">
                  <strong>Uitgebreide profielgegevens beheren:</strong><br/>
                  Voor het bijwerken van adres, telefoon, lidmaatschapsgegevens en motorinformatie, 
                  ga naar de <strong>Lidmaatschap</strong> pagina.
                </Text>
              </Box>
            </Alert>
            
            <Button 
              colorScheme="orange"
              onClick={() => {
                window.location.href = '/membership';
              }}
            >
              Ga naar Lidmaatschap Gegevens
            </Button>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}

export default ProfileManager;
import React, { useState, useEffect } from 'react';
import {
  Box, VStack, Tabs, TabList, TabPanels, Tab, TabPanel,
  Heading, useToast, Spinner, Text
} from '@chakra-ui/react';
import UserManagement from './components/UserManagement';
import GroupManagement from './components/GroupManagement';
import PoolSettings from './components/PoolSettings';

function CognitoAdminPage({ user }) {
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  return (
    <Box p={6} bg="black" minH="100vh">
      <VStack spacing={6} align="stretch">
        <Heading color="orange.400">Cognito Gebruikersbeheer</Heading>
        
        <Tabs colorScheme="orange" variant="enclosed">
          <TabList>
            <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
              Gebruikers
            </Tab>
            <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
              Groepen
            </Tab>
            <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
              Pool Instellingen
            </Tab>
          </TabList>

          <TabPanels>
            <TabPanel p={0} pt={6}>
              <UserManagement user={user} />
            </TabPanel>
            <TabPanel p={0} pt={6}>
              <GroupManagement user={user} />
            </TabPanel>
            <TabPanel p={0} pt={6}>
              <PoolSettings user={user} />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>
    </Box>
  );
}

export default CognitoAdminPage;
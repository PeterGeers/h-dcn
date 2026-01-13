import React from 'react';
import { Button, VStack, Text, Box } from '@chakra-ui/react';
import { showMaintenanceScreen, hideMaintenanceScreen } from '../utils/errorHandler';

export const MaintenanceTest: React.FC = () => {
  const handleShow503Error = () => {
    const mockError = {
      status: 503,
      message: 'Het authenticatiesysteem is tijdelijk niet beschikbaar voor onderhoud.',
      details: 'Test 503 error simulation',
      isMaintenanceMode: true
    };
    showMaintenanceScreen(mockError);
  };

  const handleHideMaintenanceScreen = () => {
    hideMaintenanceScreen();
  };

  return (
    <Box p={6} bg="white" borderRadius="md" boxShadow="md">
      <VStack spacing={4}>
        <Text fontSize="lg" fontWeight="bold" color="black">
          Maintenance Screen Test
        </Text>
        <Text color="gray.600">
          Test the centralized 503 error handling and maintenance screen functionality.
        </Text>
        <Button colorScheme="red" onClick={handleShow503Error}>
          Simulate 503 Maintenance Error
        </Button>
        <Button colorScheme="green" onClick={handleHideMaintenanceScreen}>
          Hide Maintenance Screen
        </Button>
      </VStack>
    </Box>
  );
};

export default MaintenanceTest;
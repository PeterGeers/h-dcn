import React from 'react';
import {
  Box,
  VStack,
  Heading,
  Text,
  Button,
  Container,
  useColorModeValue,
} from '@chakra-ui/react';
import { SettingsIcon, EmailIcon, RepeatIcon } from '@chakra-ui/icons';

interface MaintenanceScreenProps {
  message?: string;
  contactEmail?: string;
  onRetry?: () => void;
  showRetry?: boolean;
}

export const MaintenanceScreen: React.FC<MaintenanceScreenProps> = ({
  message = "Het authenticatiesysteem is tijdelijk niet beschikbaar voor onderhoud.",
  contactEmail = "webmaster@h-dcn.nl",
  onRetry,
  showRetry = true
}) => {
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');
  const textColor = useColorModeValue('gray.600', 'gray.300');

  const handleRetry = () => {
    if (onRetry) {
      try {
        onRetry();
      } catch (error) {
        // Silently handle errors from custom retry handlers
        console.error('Error in custom retry handler:', error);
      }
    } else {
      // Default retry behavior - reload the page
      try {
        window.location.reload();
      } catch (error) {
        // Silently handle cases where reload is not available (e.g., in tests)
        console.error('Error reloading page:', error);
      }
    }
  };

  return (
    <Box
      minH="100vh"
      bg={bgColor}
      display="flex"
      alignItems="center"
      justifyContent="center"
      p={4}
    >
      <Container maxW="md">
        <Box
          bg={cardBg}
          p={8}
          borderRadius="lg"
          boxShadow="lg"
          textAlign="center"
        >
          <VStack spacing={6}>
            <SettingsIcon w={16} h={16} color="orange.500" />
            
            <Heading size="lg" color="orange.500">
              Systeem Onderhoud
            </Heading>
            
            <Text color={textColor} fontSize="md" lineHeight="tall">
              {message}
            </Text>
            
            <Text color={textColor} fontSize="sm">
              We werken hard om het systeem zo snel mogelijk weer beschikbaar te maken.
              Probeer het over een paar minuten opnieuw.
            </Text>
            
            {showRetry && (
              <Button
                leftIcon={<RepeatIcon />}
                colorScheme="blue"
                onClick={handleRetry}
                size="lg"
              >
                Opnieuw proberen
              </Button>
            )}
            
            <Box pt={4} borderTop="1px" borderColor="gray.200" w="full">
              <Text color={textColor} fontSize="sm" mb={2}>
                Hulp nodig?
              </Text>
              <Button
                as="a"
                href={`mailto:${contactEmail}?subject=H-DCN Systeem Onderhoud`}
                leftIcon={<EmailIcon />}
                variant="outline"
                size="sm"
                colorScheme="blue"
              >
                Contact: {contactEmail}
              </Button>
            </Box>
          </VStack>
        </Box>
      </Container>
    </Box>
  );
};

export default MaintenanceScreen;
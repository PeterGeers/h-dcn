/**
 * Application Submitted Confirmation Page
 * 
 * Shows confirmation after a new member has successfully submitted their application
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  VStack,
  Heading,
  Text,
  Button,
  Card,
  CardBody,
  Icon,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  List,
  ListItem,
  ListIcon
} from '@chakra-ui/react';
import { CheckIcon, EmailIcon } from '@chakra-ui/icons';

const ApplicationSubmitted: React.FC = () => {
  const navigate = useNavigate();

  const handleGoToDashboard = () => {
    navigate('/dashboard');
  };

  const handleGoHome = () => {
    navigate('/');
  };

  return (
    <Box maxW="800px" mx="auto" p={6} bg="black" minH="100vh">
      <VStack spacing={8} align="stretch">
        {/* Success Header */}
        <Box textAlign="center" pt={8}>
          <Icon as={CheckIcon} boxSize={16} color="green.400" mb={4} />
          <Heading size="xl" color="orange.300" mb={2}>
            Aanvraag Succesvol Verzonden!
          </Heading>
          <Text color="gray.300" fontSize="lg">
            Bedankt voor uw interesse in het H-DCN lidmaatschap
          </Text>
        </Box>

        {/* Confirmation Details */}
        <Card bg="gray.800" borderColor="green.400" border="1px" borderRadius="lg">
          <CardBody>
            <Alert status="success" bg="green.900" color="white" borderRadius="md" mb={6}>
              <AlertIcon />
              <Box>
                <AlertTitle>Uw aanvraag is ontvangen</AlertTitle>
                <AlertDescription>
                  Uw lidmaatschapsaanvraag wordt nu beoordeeld door onze administratie.
                </AlertDescription>
              </Box>
            </Alert>

            <VStack spacing={4} align="stretch">
              <Heading size="md" color="orange.300">
                Wat gebeurt er nu?
              </Heading>
              
              <List spacing={3} color="gray.300">
                <ListItem>
                  <ListIcon as={CheckIcon} color="green.400" />
                  <strong>Beoordeling:</strong> Uw aanvraag wordt beoordeeld door de regionale administratie
                </ListItem>
                <ListItem>
                  <ListIcon as={EmailIcon} color="blue.400" />
                  <strong>Bevestiging:</strong> U ontvangt binnen 5-10 werkdagen een e-mail met de uitslag
                </ListItem>
                <ListItem>
                  <ListIcon as={CheckIcon} color="green.400" />
                  <strong>Goedkeuring:</strong> Bij goedkeuring ontvangt u uw lidnummer en toegang tot alle faciliteiten
                </ListItem>
              </List>

              <Box bg="orange.900" p={4} borderRadius="md" mt={6}>
                <Heading size="sm" color="orange.300" mb={2}>
                  Belangrijke informatie:
                </Heading>
                <List spacing={2} color="gray.300" fontSize="sm">
                  <ListItem>
                    • Controleer regelmatig uw e-mail (ook spam/ongewenst)
                  </ListItem>
                  <ListItem>
                    • Bij vragen kunt u contact opnemen met uw regionale afdeling
                  </ListItem>
                  <ListItem>
                    • Uw gegevens worden vertrouwelijk behandeld conform onze privacyverklaring
                  </ListItem>
                </List>
              </Box>
            </VStack>
          </CardBody>
        </Card>

        {/* Contact Information */}
        <Card bg="gray.800" borderColor="orange.400" border="1px" borderRadius="lg">
          <CardBody>
            <Heading size="md" color="orange.300" mb={4}>
              Contact & Ondersteuning
            </Heading>
            <VStack spacing={3} align="stretch" color="gray.300">
              <Text>
                <strong>Website:</strong> www.h-dcn.nl
              </Text>
              <Text>
                <strong>E-mail:</strong> info@h-dcn.nl
              </Text>
              <Text>
                <strong>Telefoon:</strong> Zie contactgegevens op de website per regio
              </Text>
            </VStack>
          </CardBody>
        </Card>

        {/* Action Buttons */}
        <Card bg="gray.800" borderColor="orange.400" border="1px" borderRadius="lg">
          <CardBody>
            <VStack spacing={4}>
              <Text color="gray.300" textAlign="center">
                U kunt nu de website verkennen of uitloggen
              </Text>
              <VStack spacing={3} w="full">
                <Button
                  colorScheme="orange"
                  size="lg"
                  onClick={handleGoToDashboard}
                  w="full"
                  maxW="300px"
                >
                  Ga naar Dashboard
                </Button>
                <Button
                  variant="outline"
                  colorScheme="gray"
                  size="md"
                  onClick={handleGoHome}
                  w="full"
                  maxW="300px"
                >
                  Terug naar Home
                </Button>
              </VStack>
            </VStack>
          </CardBody>
        </Card>

        {/* Footer */}
        <Box textAlign="center" pt={4} pb={8}>
          <Text color="gray.500" fontSize="sm">
            © 2024 Harley-Davidson Club Nederland (H-DCN)
          </Text>
        </Box>
      </VStack>
    </Box>
  );
};

export default ApplicationSubmitted;
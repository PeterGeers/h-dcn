/**
 * Application Submitted Confirmation Page
 * 
 * Shows confirmation after a new member has successfully submitted their application
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation('members');

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
            {t('submitted.title')}
          </Heading>
          <Text color="gray.300" fontSize="lg">
            {t('submitted.subtitle')}
          </Text>
        </Box>

        {/* Confirmation Details */}
        <Card bg="gray.800" borderColor="green.400" border="1px" borderRadius="lg">
          <CardBody>
            <Alert status="success" bg="green.900" color="white" borderRadius="md" mb={6}>
              <AlertIcon />
              <Box>
                <AlertTitle>{t('submitted.received_title')}</AlertTitle>
                <AlertDescription>
                  {t('submitted.received_desc')}
                </AlertDescription>
              </Box>
            </Alert>

            <VStack spacing={4} align="stretch">
              <Heading size="md" color="orange.300">
                {t('submitted.what_next')}
              </Heading>
              
              <List spacing={3} color="gray.300">
                <ListItem>
                  <ListIcon as={CheckIcon} color="green.400" />
                  <strong>{t('submitted.step_review')}:</strong> {t('submitted.step_review_desc')}
                </ListItem>
                <ListItem>
                  <ListIcon as={EmailIcon} color="blue.400" />
                  <strong>{t('submitted.step_confirmation')}:</strong> {t('submitted.step_confirmation_desc')}
                </ListItem>
                <ListItem>
                  <ListIcon as={CheckIcon} color="green.400" />
                  <strong>{t('submitted.step_approval')}:</strong> {t('submitted.step_approval_desc')}
                </ListItem>
              </List>

              <Box bg="orange.900" p={4} borderRadius="md" mt={6}>
                <Heading size="sm" color="orange.300" mb={2}>
                  {t('submitted.important_info')}:
                </Heading>
                <List spacing={2} color="gray.300" fontSize="sm">
                  <ListItem>
                    • {t('submitted.tip_check_email')}
                  </ListItem>
                  <ListItem>
                    • {t('submitted.tip_contact')}
                  </ListItem>
                  <ListItem>
                    • {t('submitted.tip_privacy')}
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
              {t('submitted.contact_title')}
            </Heading>
            <VStack spacing={3} align="stretch" color="gray.300">
              <Text>
                <strong>{t('submitted.website')}:</strong> www.h-dcn.nl
              </Text>
              <Text>
                <strong>{t('submitted.email')}:</strong> info@h-dcn.nl
              </Text>
              <Text>
                <strong>{t('submitted.phone')}:</strong> {t('submitted.phone_desc')}
              </Text>
            </VStack>
          </CardBody>
        </Card>

        {/* Action Buttons */}
        <Card bg="gray.800" borderColor="orange.400" border="1px" borderRadius="lg">
          <CardBody>
            <VStack spacing={4}>
              <Text color="gray.300" textAlign="center">
                {t('submitted.action_prompt')}
              </Text>
              <VStack spacing={3} w="full">
                <Button
                  colorScheme="orange"
                  size="lg"
                  onClick={handleGoToDashboard}
                  w="full"
                  maxW="300px"
                >
                  {t('submitted.go_dashboard')}
                </Button>
                <Button
                  variant="outline"
                  colorScheme="gray"
                  size="md"
                  onClick={handleGoHome}
                  w="full"
                  maxW="300px"
                >
                  {t('submitted.go_home')}
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
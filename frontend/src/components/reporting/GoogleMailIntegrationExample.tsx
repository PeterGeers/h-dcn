/**
 * Google Mail Integration Example Component
 * 
 * This component demonstrates how to use the Google Mail integration
 * in a reporting dashboard or export interface.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  VStack,
  HStack,
  Text,
  Alert,
  AlertIcon,
  useToast,
  Badge,
  Card,
  CardBody,
  CardHeader,
  Heading
} from '@chakra-ui/react';
import { EmailIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import { Member } from '../../types/index';
import { useGoogleMailIntegration } from '../../hooks/useGoogleMailIntegration';
import { EXPORT_VIEWS } from '../../services/MemberExportService';

// ============================================================================
// COMPONENT PROPS
// ============================================================================

interface GoogleMailIntegrationExampleProps {
  members: Member[];
  userRoles: string[];
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export const GoogleMailIntegrationExample: React.FC<GoogleMailIntegrationExampleProps> = ({
  members,
  userRoles
}) => {
  const {
    isAuthenticated,
    isAuthenticating,
    authUser,
    error,
    lastResult,
    authenticate,
    logout,
    createDistributionList,
    clearError,
    availableTemplates
  } = useGoogleMailIntegration(userRoles);

  const [isCreating, setIsCreating] = useState(false);
  const toast = useToast();

  // Clear errors after a delay
  useEffect(() => {
    if (error) {
      const timer = setTimeout(clearError, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, clearError]);

  // Show success toast for successful distribution list creation
  useEffect(() => {
    if (lastResult?.success) {
      toast({
        title: 'Distribution List Created',
        description: `Successfully created "${lastResult.groupName}" with ${lastResult.memberCount} members.`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    }
  }, [lastResult, toast]);

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================

  const handleAuthenticate = async () => {
    try {
      await authenticate();
    } catch (err) {
      toast({
        title: 'Authentication Failed',
        description: 'Failed to authenticate with Google. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleCreateDistributionList = async (templateKey: string) => {
    try {
      setIsCreating(true);
      
      const result = await createDistributionList(templateKey, members);
      
      if (!result.success) {
        toast({
          title: 'Creation Failed',
          description: result.error || 'Failed to create distribution list.',
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    } catch (err) {
      toast({
        title: 'Creation Error',
        description: 'An unexpected error occurred.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsCreating(false);
    }
  };

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  const getFilteredMemberCount = (templateKey: string): number => {
    const view = EXPORT_VIEWS[templateKey];
    if (!view) return 0;
    
    const filteredMembers = view.filter ? members.filter(view.filter) : members;
    return filteredMembers.length;
  };

  // ============================================================================
  // RENDER METHODS
  // ============================================================================

  const renderAuthenticationSection = () => (
    <Card>
      <CardHeader>
        <Heading size="md">Google Account Connection</Heading>
      </CardHeader>
      <CardBody>
        {!isAuthenticated ? (
          <VStack spacing={4} align="stretch">
            <Text color="gray.600">
              Connect your Google account to create distribution lists in Google Contacts.
            </Text>
            <Button
              colorScheme="red"
              onClick={handleAuthenticate}
              isLoading={isAuthenticating}
              loadingText="Authenticating..."
              leftIcon={<ExternalLinkIcon />}
            >
              Connect Google Account
            </Button>
          </VStack>
        ) : (
          <VStack spacing={4} align="stretch">
            <HStack>
              <Text color="green.500">✓</Text>
              <Text>
                Connected as <strong>{authUser?.email || 'authenticated user'}</strong>
              </Text>
            </HStack>
            <Button variant="outline" size="sm" onClick={logout}>
              Disconnect
            </Button>
          </VStack>
        )}
      </CardBody>
    </Card>
  );

  const renderDistributionListTemplates = () => (
    <Card>
      <CardHeader>
        <Heading size="md">Create Distribution Lists</Heading>
      </CardHeader>
      <CardBody>
        <VStack spacing={4} align="stretch">
          {availableTemplates.map((template) => {
            const memberCount = getFilteredMemberCount(template.key);
            
            return (
              <Box
                key={template.key}
                p={4}
                border="1px"
                borderColor="gray.200"
                borderRadius="md"
                _hover={{ borderColor: 'orange.300', bg: 'orange.50' }}
              >
                <HStack justify="space-between" align="start">
                  <VStack align="start" spacing={2} flex={1}>
                    <HStack>
                      <EmailIcon color="orange.500" />
                      <Text fontWeight="semibold">{template.name}</Text>
                      <Badge colorScheme="blue">{memberCount} members</Badge>
                    </HStack>
                    <Text fontSize="sm" color="gray.600">
                      {template.description}
                    </Text>
                    <Text fontSize="xs" color="gray.500">
                      Use case: {template.useCase}
                    </Text>
                  </VStack>
                  <Button
                    size="sm"
                    colorScheme="orange"
                    onClick={() => handleCreateDistributionList(template.key)}
                    isDisabled={!isAuthenticated || memberCount === 0}
                    isLoading={isCreating}
                    loadingText="Creating..."
                  >
                    Create List
                  </Button>
                </HStack>
              </Box>
            );
          })}

          {availableTemplates.length === 0 && (
            <Alert status="info">
              <AlertIcon />
              <Text>No distribution list templates are available for your current permissions.</Text>
            </Alert>
          )}
        </VStack>
      </CardBody>
    </Card>
  );

  const renderUsageInstructions = () => (
    <Card>
      <CardHeader>
        <Heading size="md">How to Use in Gmail</Heading>
      </CardHeader>
      <CardBody>
        <VStack spacing={3} align="stretch">
          <Text color="gray.600">
            After creating a distribution list, you can use it in Gmail:
          </Text>
          
          <VStack spacing={2} align="stretch">
            <Text fontSize="sm">
              <strong>1.</strong> Open Gmail and click "Compose"
            </Text>
            <Text fontSize="sm">
              <strong>2.</strong> In the "To" field, start typing the group name
            </Text>
            <Text fontSize="sm">
              <strong>3.</strong> Select the group from the suggestions
            </Text>
            <Text fontSize="sm">
              <strong>4.</strong> All members will be added automatically
            </Text>
          </VStack>

          <Alert status="info" size="sm">
            <AlertIcon />
            <Text fontSize="sm">
              Distribution lists are private to your Google account and sync across all devices.
            </Text>
          </Alert>
        </VStack>
      </CardBody>
    </Card>
  );

  // ============================================================================
  // MAIN RENDER
  // ============================================================================

  return (
    <Box>
      <VStack spacing={6} align="stretch">
        <Box>
          <Heading size="lg" mb={2}>
            📧 Google Mail Integration
          </Heading>
          <Text color="gray.600">
            Create distribution lists in Google Contacts for easy Gmail communication.
          </Text>
        </Box>

        {error && (
          <Alert status="error">
            <AlertIcon />
            <Text>{error}</Text>
          </Alert>
        )}

        {renderAuthenticationSection()}
        
        {isAuthenticated && (
          <>
            {renderDistributionListTemplates()}
            {renderUsageInstructions()}
          </>
        )}
      </VStack>
    </Box>
  );
};

export default GoogleMailIntegrationExample;
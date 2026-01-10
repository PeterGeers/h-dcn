/**
 * Google Mail Integration Component for H-DCN Reporting
 * 
 * This component provides a user interface for creating distribution lists
 * in Google Contacts that can be used directly in Gmail.
 * 
 * Features:
 * - Google OAuth authentication
 * - Distribution list templates
 * - Member filtering and preview
 * - Progress tracking during creation
 * - Success/error handling
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Text,
  VStack,
  HStack,
  Badge,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Progress,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  Input,
  FormControl,
  FormLabel,
  Select,
  Textarea,
  Divider,
  List,
  ListItem,
  ListIcon,
  useToast,
  Spinner,
  Icon
} from '@chakra-ui/react';
import { 
  EmailIcon, 
  CheckCircleIcon, 
  WarningIcon, 
  ExternalLinkIcon,
  AddIcon,
  ViewIcon
} from '@chakra-ui/icons';
import { Member } from '../../types/index';
import { getMemberFullName } from '../../utils/calculatedFields';
import { googleMailService, DistributionListResult } from '../../services/GoogleMailService';
import { EXPORT_VIEWS } from '../../services/MemberExportService';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface GoogleMailIntegrationProps {
  members: Member[];
  userRoles: string[];
  userRegion?: string;
}

interface DistributionListPreview {
  templateKey: string;
  templateName: string;
  memberCount: number;
  sampleMembers: string[];
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export const GoogleMailIntegration: React.FC<GoogleMailIntegrationProps> = ({
  members,
  userRoles,
  userRegion
}) => {
  // State management
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authUser, setAuthUser] = useState<{ email: string; name?: string } | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [customName, setCustomName] = useState<string>('');
  const [customDescription, setCustomDescription] = useState<string>('');
  const [preview, setPreview] = useState<DistributionListPreview | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [creationProgress, setCreationProgress] = useState(0);
  const [lastResult, setLastResult] = useState<DistributionListResult | null>(null);

  // UI state
  const { isOpen: isPreviewOpen, onOpen: onPreviewOpen, onClose: onPreviewClose } = useDisclosure();
  const { isOpen: isCreateOpen, onOpen: onCreateOpen, onClose: onCreateClose } = useDisclosure();
  const toast = useToast();

  // Check authentication status on mount
  useEffect(() => {
    setIsAuthenticated(googleMailService.isAuthenticated());
  }, []);

  // Get available templates based on user permissions
  const availableTemplates = googleMailService.getDistributionListTemplates().filter(template => {
    const view = EXPORT_VIEWS[template.key];
    return view && view.permissions.view.some(role => userRoles.includes(role));
  });

  // ============================================================================
  // AUTHENTICATION HANDLERS
  // ============================================================================

  const handleGoogleAuth = async () => {
    try {
      setIsAuthenticating(true);
      googleMailService.initiateAuth();
      
      // Listen for auth completion (this would typically be handled by a callback)
      const checkAuth = setInterval(() => {
        if (googleMailService.isAuthenticated()) {
          setIsAuthenticated(true);
          setIsAuthenticating(false);
          clearInterval(checkAuth);
          toast({
            title: 'Google Authentication Successful',
            description: 'You can now create distribution lists in Google Contacts.',
            status: 'success',
            duration: 5000,
            isClosable: true,
          });
        }
      }, 1000);

      // Clear interval after 30 seconds to avoid infinite checking
      setTimeout(() => {
        clearInterval(checkAuth);
        setIsAuthenticating(false);
      }, 30000);
    } catch (error) {
      console.error('Google auth error:', error);
      setIsAuthenticating(false);
      toast({
        title: 'Authentication Failed',
        description: 'Failed to authenticate with Google. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleLogout = () => {
    googleMailService.logout();
    setIsAuthenticated(false);
    setAuthUser(null);
    toast({
      title: 'Logged Out',
      description: 'You have been logged out of Google.',
      status: 'info',
      duration: 3000,
      isClosable: true,
    });
  };

  // ============================================================================
  // PREVIEW HANDLERS
  // ============================================================================

  const handlePreviewTemplate = (templateKey: string) => {
    const template = availableTemplates.find(t => t.key === templateKey);
    if (!template) return;

    const view = EXPORT_VIEWS[templateKey];
    if (!view) return;

    // Apply filters
    let filteredMembers = members;
    if (view.filter) {
      filteredMembers = members.filter(view.filter);
    }

    // Apply regional filtering if required
    if (view.regionalRestricted && userRegion) {
      filteredMembers = filteredMembers.filter(member => member.regio === userRegion);
    }

    // Create preview
    const sampleMembers = filteredMembers
      .slice(0, 5)
      .map(member => `${getMemberFullName(member)} (${member.email || 'No email'})`)
      .filter(Boolean);

    setPreview({
      templateKey,
      templateName: template.name,
      memberCount: filteredMembers.length,
      sampleMembers
    });

    setSelectedTemplate(templateKey);
    onPreviewOpen();
  };

  // ============================================================================
  // CREATION HANDLERS
  // ============================================================================

  const handleCreateDistributionList = async () => {
    if (!selectedTemplate || !isAuthenticated) return;

    try {
      setIsCreating(true);
      setCreationProgress(0);
      onPreviewClose();
      onCreateOpen();

      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setCreationProgress(prev => Math.min(prev + 10, 90));
      }, 500);

      const result = await googleMailService.createDistributionListFromView(
        selectedTemplate,
        members,
        customName || undefined
      );

      clearInterval(progressInterval);
      setCreationProgress(100);
      setLastResult(result);

      if (result.success) {
        toast({
          title: 'Distribution List Created',
          description: `Successfully created "${result.groupName}" with ${result.memberCount} members.`,
          status: 'success',
          duration: 7000,
          isClosable: true,
        });
      } else {
        toast({
          title: 'Creation Failed',
          description: result.error || 'Failed to create distribution list.',
          status: 'error',
          duration: 7000,
          isClosable: true,
        });
      }
    } catch (error) {
      console.error('Distribution list creation error:', error);
      toast({
        title: 'Creation Error',
        description: 'An unexpected error occurred while creating the distribution list.',
        status: 'error',
        duration: 7000,
        isClosable: true,
      });
    } finally {
      setIsCreating(false);
      setTimeout(() => {
        onCreateClose();
        setCreationProgress(0);
      }, 2000);
    }
  };

  // ============================================================================
  // RENDER METHODS
  // ============================================================================

  const renderAuthenticationSection = () => (
    <Card>
      <CardHeader>
        <HStack>
          <ExternalLinkIcon color="red.500" />
          <Heading size="md">Google Account Connection</Heading>
        </HStack>
      </CardHeader>
      <CardBody>
        {!isAuthenticated ? (
          <VStack spacing={4} align="stretch">
            <Text color="gray.600">
              Connect your Google account to create distribution lists in Google Contacts
              that can be used directly in Gmail.
            </Text>
            <Alert status="info">
              <AlertIcon />
              <Box>
                <AlertTitle>Required Permissions:</AlertTitle>
                <AlertDescription>
                  • Access to Google Contacts (to create groups and add members)
                  • Basic profile information (to verify your identity)
                </AlertDescription>
              </Box>
            </Alert>
            <Button
              leftIcon={<ExternalLinkIcon />}
              colorScheme="red"
              onClick={handleGoogleAuth}
              isLoading={isAuthenticating}
              loadingText="Authenticating..."
              size="lg"
            >
              Connect Google Account
            </Button>
          </VStack>
        ) : (
          <VStack spacing={4} align="stretch">
            <HStack>
              <CheckCircleIcon color="green.500" />
              <Text>
                Connected to Google as <strong>{authUser?.email || 'authenticated user'}</strong>
              </Text>
            </HStack>
            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
            >
              Disconnect
            </Button>
          </VStack>
        )}
      </CardBody>
    </Card>
  );

  const renderTemplatesSection = () => (
    <Card>
      <CardHeader>
        <Heading size="md">Distribution List Templates</Heading>
      </CardHeader>
      <CardBody>
        <VStack spacing={4} align="stretch">
          <Text color="gray.600">
            Choose a template to create a distribution list in Google Contacts:
          </Text>
          
          {availableTemplates.map((template) => (
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
                    <Heading size="sm">{template.name}</Heading>
                  </HStack>
                  <Text fontSize="sm" color="gray.600">
                    {template.description}
                  </Text>
                  <Badge colorScheme="blue" fontSize="xs">
                    {template.useCase}
                  </Badge>
                </VStack>
                <VStack spacing={2}>
                  <Button
                    size="sm"
                    leftIcon={<ViewIcon />}
                    onClick={() => handlePreviewTemplate(template.key)}
                    isDisabled={!isAuthenticated}
                  >
                    Preview
                  </Button>
                </VStack>
              </HStack>
            </Box>
          ))}

          {availableTemplates.length === 0 && (
            <Alert status="warning">
              <AlertIcon />
              <AlertDescription>
                No distribution list templates are available for your current permissions.
              </AlertDescription>
            </Alert>
          )}
        </VStack>
      </CardBody>
    </Card>
  );

  const renderUsageInstructions = () => (
    <Card>
      <CardHeader>
        <Heading size="md">How to Use Distribution Lists in Gmail</Heading>
      </CardHeader>
      <CardBody>
        <VStack spacing={3} align="stretch">
          <Text color="gray.600">
            After creating a distribution list, you can use it in Gmail:
          </Text>
          
          <List spacing={2}>
            <ListItem>
              <ListIcon as={CheckCircleIcon} color="green.500" />
              <strong>In Gmail:</strong> Start typing the group name in the "To" field
            </ListItem>
            <ListItem>
              <ListIcon as={CheckCircleIcon} color="green.500" />
              <strong>Google Contacts:</strong> Find the group in your contacts list
            </ListItem>
            <ListItem>
              <ListIcon as={CheckCircleIcon} color="green.500" />
              <strong>Mobile:</strong> Groups sync automatically to Gmail mobile app
            </ListItem>
            <ListItem>
              <ListIcon as={CheckCircleIcon} color="green.500" />
              <strong>Updates:</strong> Re-run the export to update group membership
            </ListItem>
          </List>

          <Alert status="info">
            <AlertIcon />
            <AlertDescription>
              Distribution lists are created in your personal Google Contacts and are private to your account.
            </AlertDescription>
          </Alert>
        </VStack>
      </CardBody>
    </Card>
  );

  // ============================================================================
  // MODAL COMPONENTS
  // ============================================================================

  const PreviewModal = () => (
    <Modal isOpen={isPreviewOpen} onClose={onPreviewClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Preview Distribution List</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {preview && (
            <VStack spacing={4} align="stretch">
              <Box>
                <Text fontWeight="bold">{preview.templateName}</Text>
                <Text color="gray.600" fontSize="sm">
                  {preview.memberCount} members will be added to this list
                </Text>
              </Box>

              <Divider />

              <Box>
                <Text fontWeight="bold" mb={2}>Sample Members:</Text>
                <List spacing={1}>
                  {preview.sampleMembers.map((member, index) => (
                    <ListItem key={index} fontSize="sm">
                      <ListIcon as={CheckCircleIcon} color="green.500" />
                      {member}
                    </ListItem>
                  ))}
                </List>
                {preview.memberCount > 5 && (
                  <Text fontSize="sm" color="gray.500" mt={2}>
                    ... and {preview.memberCount - 5} more members
                  </Text>
                )}
              </Box>

              <Divider />

              <VStack spacing={3} align="stretch">
                <FormControl>
                  <FormLabel>Custom Name (optional)</FormLabel>
                  <Input
                    placeholder={`H-DCN ${preview.templateName}`}
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                  />
                </FormControl>

                <FormControl>
                  <FormLabel>Description (optional)</FormLabel>
                  <Textarea
                    placeholder="Add a custom description for this distribution list..."
                    value={customDescription}
                    onChange={(e) => setCustomDescription(e.target.value)}
                    rows={3}
                  />
                </FormControl>
              </VStack>
            </VStack>
          )}
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onPreviewClose}>
            Cancel
          </Button>
          <Button
            colorScheme="orange"
            leftIcon={<AddIcon />}
            onClick={handleCreateDistributionList}
            isDisabled={!preview || preview.memberCount === 0}
          >
            Create Distribution List
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );

  const CreationModal = () => (
    <Modal isOpen={isCreateOpen} onClose={() => {}} closeOnOverlayClick={false} size="md">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Creating Distribution List</ModalHeader>
        <ModalBody>
          <VStack spacing={4}>
            {isCreating ? (
              <>
                <Spinner size="lg" color="orange.500" />
                <Text>Creating distribution list in Google Contacts...</Text>
                <Progress value={creationProgress} width="100%" colorScheme="orange" />
                <Text fontSize="sm" color="gray.600">
                  This may take a few moments for large lists
                </Text>
              </>
            ) : lastResult ? (
              <>
                {lastResult.success ? (
                  <>
                    <CheckCircleIcon color="green.500" boxSize={12} />
                    <Text textAlign="center">
                      <strong>Success!</strong><br />
                      Created "{lastResult.groupName}" with {lastResult.memberCount} members.
                    </Text>
                    {lastResult.gmailAddress && (
                      <Text fontSize="sm" color="gray.600" textAlign="center">
                        You can now use this group in Gmail by typing the group name.
                      </Text>
                    )}
                  </>
                ) : (
                  <>
                    <WarningIcon color="red.500" boxSize={12} />
                    <Text textAlign="center">
                      <strong>Creation Failed</strong><br />
                      {lastResult.error}
                    </Text>
                  </>
                )}
              </>
            ) : null}
          </VStack>
        </ModalBody>
        {!isCreating && (
          <ModalFooter>
            <Button onClick={onCreateClose}>Close</Button>
          </ModalFooter>
        )}
      </ModalContent>
    </Modal>
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
            Create distribution lists in Google Contacts for easy Gmail communication with H-DCN members.
          </Text>
        </Box>

        {renderAuthenticationSection()}
        
        {isAuthenticated && (
          <>
            {renderTemplatesSection()}
            {renderUsageInstructions()}
          </>
        )}
      </VStack>

      <PreviewModal />
      <CreationModal />
    </Box>
  );
};

export default GoogleMailIntegration;
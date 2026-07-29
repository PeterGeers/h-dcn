/**
 * My Account Page - Member Self-Service
 * 
 * Allows members to view and edit their own data using the field registry system
 * Enhanced to support member application flow for verzoek_lid users
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  VStack,
  Spinner,
  Text,
  Alert,
  AlertIcon,
  Button,
  Heading,
  Badge,
  HStack,
  useToast,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  useDisclosure
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import MemberSelfServiceView from '../components/MemberSelfServiceView';
import NewMemberApplicationForm from '../components/NewMemberApplicationForm';
import { Member } from '../types';
import { ApiService } from '../services/apiService';
import { useErrorHandler } from '../utils/errorHandler';
import { computeCalculatedFields } from '../utils/calculatedFields';

interface User {
  attributes?: {
    given_name?: string;
    family_name?: string;
    email?: string;
  };
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: string[];
      };
    };
  };
}

interface MyAccountProps {
  user: User;
}

function MyAccount({ user }: MyAccountProps) {
  const [member, setMember] = useState<Member | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showApplicationForm, setShowApplicationForm] = useState(false);
  const [isVerzoekLid, setIsVerzoekLid] = useState(false);
  const { t } = useTranslation('members');
  
  const { handleError } = useErrorHandler();
  const toast = useToast();
  const { isOpen: isSubmitDialogOpen, onOpen: onSubmitDialogOpen, onClose: onSubmitDialogClose } = useDisclosure();
  const cancelRef = React.useRef<HTMLButtonElement>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Check if user is verzoek_lid (applicant)
  useEffect(() => {
    let userRoles: string[] = [];
    
    // Try to get roles from JWT token directly
    try {
      const accessToken = (user?.signInUserSession?.accessToken as any)?.jwtToken;
      if (accessToken) {
        const tokenParts = accessToken.split('.');
        if (tokenParts.length === 3) {
          const payload = JSON.parse(atob(tokenParts[1]));
          userRoles = payload['cognito:groups'] || [];
        }
      }
    } catch (jwtError) {
      console.error('MyAccount - Error parsing JWT:', jwtError);
    }

    // Fallback: try the original method
    if (userRoles.length === 0) {
      userRoles = user?.signInUserSession?.accessToken?.payload?.['cognito:groups'] || [];
    }

    const isApplicant = userRoles.includes('verzoek_lid') && !userRoles.includes('hdcnLeden');
    console.log('MyAccount - User roles:', userRoles);
    console.log('MyAccount - Is verzoek_lid:', isApplicant);
    setIsVerzoekLid(isApplicant);
  }, [user]);

  // Load member data
  useEffect(() => {
    const loadMemberData = async () => {
      if (!user?.attributes?.email) {
        setError(t('self_service.no_data_error'));
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        
        // Use the /members/me endpoint for self-lookup
        const response = await ApiService.get('/members/me');
        
        if (response.success && response.data) {
          // Backend returns member data directly when it exists
          // Or { member: null, message: "...", email: "..." } when it doesn't
          let memberData = response.data;
          
          // Check if response has a 'member' property (null case)
          if ('member' in response.data) {
            memberData = response.data.member;
          }
          
          // Only set member if it's not null and has actual member data
          if (memberData && memberData !== null && typeof memberData === 'object' && memberData.member_id) {
            // Compute calculated fields for the member data
            const memberWithCalculatedFields = computeCalculatedFields(memberData);
            setMember(memberWithCalculatedFields);
            console.log('Member data loaded successfully:', memberWithCalculatedFields);
          } else {
            // No member record found - this is normal for verzoek_lid users
            console.log('No member record found - user may need to create application');
            setMember(null);
          }
        } else {
          // No member record found - this is normal for verzoek_lid users
          console.log('No member record found - user may need to create application');
          setMember(null);
        }
      } catch (error) {
        console.error('Error loading member data:', error);
        // For verzoek_lid users, not having a record is expected
        if (isVerzoekLid) {
          console.log('verzoek_lid user without member record - this is expected');
          setMember(null);
        } else {
          setError(t('self_service.load_error'));
        }
      } finally {
        setLoading(false);
      }
    };

    loadMemberData();
  }, [user, isVerzoekLid, t]);

  // Handle member data update (for existing members)
  const handleMemberUpdate = async (memberData: any) => {
    try {
      // Use /members/me PUT endpoint for self-service updates
      const response = await ApiService.put('/members/me', {
        ...memberData,
        updated_at: new Date().toISOString()
      });
      
      if (response.success) {
        // Compute calculated fields for the updated member data
        const updatedMemberWithCalculatedFields = computeCalculatedFields(response.data.member || response.data);
        setMember(updatedMemberWithCalculatedFields);
        console.log('Member data updated successfully');
      } else {
        throw new Error(response.error || 'Failed to update member data');
      }
    } catch (error) {
      handleError(error, t('self_service.update_api_error'));
      throw error; // Re-throw so the component can handle it
    }
  };

  // Handle new member application creation
  const handleMemberApplicationSubmit = async (applicationData: any) => {
    try {
      console.log('MyAccount - Received application data:', applicationData);
      
      let response;
      
      if (member) {
        // Member record exists - use PUT to update
        console.log('Updating existing member record');
        response = await ApiService.put('/members/me', applicationData);
      } else {
        // No member record - use POST to create
        console.log('Creating new member record');
        response = await ApiService.post('/members/me', applicationData);
      }
      
      if (response.success) {
        // Compute calculated fields for the member data
        const updatedMember = computeCalculatedFields(response.data.member || response.data);
        setMember(updatedMember);
        setShowApplicationForm(false);
        console.log('Member application processed successfully:', response.data);
        
        toast({
          title: t('application.saved_title'),
          description: t('application.saved_message'),
          status: 'success',
          duration: 3000,
        });
      } else {
        throw new Error(response.error || 'Failed to process member application');
      }
    } catch (error) {
      console.error('Error creating member application:', error);
      throw error; // Let the form handle the error display
    }
  };

  // Handle formal submission via workflow engine (SUBMIT transition)
  const handleSubmitApplication = useCallback(async () => {
    if (!member?.member_id) return;
    
    setIsSubmitting(true);
    onSubmitDialogClose();
    
    try {
      // First save the latest data
      // Then call the transition endpoint
      const transitionResponse = await ApiService.post(
        `/members/${member.member_id}/transition`,
        { event: 'SUBMIT', context: {} }
      );
      
      if (transitionResponse.success && transitionResponse.data?.success) {
        // Refresh member data to get updated status
        const refreshResponse = await ApiService.get('/members/me');
        if (refreshResponse.success && refreshResponse.data) {
          const memberData = 'member' in refreshResponse.data 
            ? refreshResponse.data.member 
            : refreshResponse.data;
          if (memberData?.member_id) {
            setMember(computeCalculatedFields(memberData));
          }
        }
        
        toast({
          title: t('application.submitted_success_title'),
          description: t('application.submitted_success_message'),
          status: 'success',
          duration: 5000,
        });
      } else {
        const errorMsg = transitionResponse.data?.error || transitionResponse.error || 'Submission failed';
        toast({
          title: t('application.submit_error_title'),
          description: errorMsg,
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error: any) {
      toast({
        title: t('application.submit_error_title'),
        description: error.message || 'Network error',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [member, toast, t, onSubmitDialogClose]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minH="400px">
        <VStack spacing={4}>
          <Spinner size="xl" color="orange.500" />
          <Text>{t('self_service.loading')}</Text>
        </VStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={6}>
        <Alert status="error">
          <AlertIcon />
          <VStack align="start" spacing={1}>
            <Text fontWeight="semibold">{t('self_service.load_error_title')}</Text>
            <Text fontSize="sm">{error}</Text>
          </VStack>
        </Alert>
      </Box>
    );
  }

  // Show application form for verzoek_lid users who want to create/edit their application
  // OR for verzoek_lid users with existing applications that are still pending (status: 'Aangemeld')
  // Check if member has actual application data (not just member_id and email)
  const hasApplicationData = member && (member.voornaam || member.achternaam || member.straat);
  const isDraft = member && !member.status;
  const isSubmitted = member && !!member.status;
  
  if (showApplicationForm || (isVerzoekLid && !hasApplicationData && !isSubmitted)) {
    return (
      <NewMemberApplicationForm
        userEmail={user?.attributes?.email || ''}
        onSubmit={handleMemberApplicationSubmit}
        onCancel={() => setShowApplicationForm(false)}
      />
    );
  }

  // Submitted state: show read-only with status badge
  if (isVerzoekLid && isSubmitted && member) {
    const statusColor = member.status === 'Actief' ? 'green' : member.status === 'Aangemeld' ? 'blue' : 'orange';
    const statusMessage = member.status === 'Actief'
      ? t('application.status_active')
      : member.status === 'Aangemeld'
        ? t('application.submitted_info')
        : t('application.status_in_progress');

    return (
      <Box maxW="800px" mx="auto" p={6}>
        <VStack spacing={6} align="stretch">
          <Box p={4} bg={`${statusColor}.900`} borderRadius="md" border="1px" borderColor={`${statusColor}.400`}>
            <VStack align="start" spacing={2}>
              <HStack>
                <Heading size="sm" color={`${statusColor}.300`}>{t('application.status_title')}</Heading>
                <Badge colorScheme={statusColor} fontSize="sm">{member.status}</Badge>
              </HStack>
              <Text fontSize="sm" color={`${statusColor}.200`}>
                {statusMessage}
              </Text>
            </VStack>
          </Box>
          
          <MemberSelfServiceView 
            member={member}
            onUpdate={handleMemberUpdate}
            readOnly={true}
          />
        </VStack>
      </Box>
    );
  }

  // Draft state: show form with save + submit buttons
  if (isVerzoekLid && isDraft && hasApplicationData && member) {
    return (
      <Box maxW="800px" mx="auto" p={6}>
        <VStack spacing={6} align="stretch">
          <Box p={4} bg="yellow.900" borderRadius="md" border="1px" borderColor="yellow.400">
            <VStack align="start" spacing={2}>
              <HStack>
                <Heading size="sm" color="yellow.300">{t('application.draft_title')}</Heading>
                <Badge colorScheme="yellow" fontSize="sm">{t('application.draft_badge')}</Badge>
              </HStack>
              <Text fontSize="sm" color="yellow.200">
                {t('application.draft_info')}
              </Text>
              <HStack spacing={3} pt={2}>
                <Button
                  size="sm"
                  colorScheme="orange"
                  variant="outline"
                  onClick={() => setShowApplicationForm(true)}
                >
                  {t('application.edit_data')}
                </Button>
                <Button
                  size="sm"
                  colorScheme="green"
                  onClick={onSubmitDialogOpen}
                  isLoading={isSubmitting}
                >
                  {t('application.submit_button')}
                </Button>
              </HStack>
            </VStack>
          </Box>
          
          <MemberSelfServiceView 
            member={member}
            onUpdate={handleMemberUpdate}
          />

          {/* Submit confirmation dialog */}
          <AlertDialog
            isOpen={isSubmitDialogOpen}
            leastDestructiveRef={cancelRef}
            onClose={onSubmitDialogClose}
          >
            <AlertDialogOverlay>
              <AlertDialogContent bg="gray.800" color="white">
                <AlertDialogHeader fontSize="lg" fontWeight="bold" color="orange.300">
                  {t('application.confirm_submit_title')}
                </AlertDialogHeader>
                <AlertDialogBody>
                  {t('application.confirm_submit_message')}
                </AlertDialogBody>
                <AlertDialogFooter>
                  <Button ref={cancelRef} onClick={onSubmitDialogClose} variant="ghost">
                    {t('application.confirm_cancel')}
                  </Button>
                  <Button colorScheme="green" onClick={handleSubmitApplication} ml={3}>
                    {t('application.confirm_submit')}
                  </Button>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialogOverlay>
          </AlertDialog>
        </VStack>
      </Box>
    );
  }

  // Show member data for regular members (hdcnLeden)
  if (member && hasApplicationData) {
    return (
      <MemberSelfServiceView 
        member={member}
        onUpdate={handleMemberUpdate}
      />
    );
  }

  // Show application prompt for verzoek_lid users without member record
  if (isVerzoekLid) {
    return (
      <Box p={6}>
        <Alert status="info">
          <AlertIcon />
          <VStack align="start" spacing={3}>
            <Text fontWeight="semibold">{t('application.welcome_title')}</Text>
            <Text fontSize="sm">
              {t('application.welcome_message')}
            </Text>
            <Button
              colorScheme="orange"
              onClick={() => setShowApplicationForm(true)}
            >
              {t('application.submit_button')}
            </Button>
          </VStack>
        </Alert>
      </Box>
    );
  }

  // Default state for regular users without member record
  return (
    <Box p={6}>
      <Alert status="info">
        <AlertIcon />
        <VStack align="start" spacing={1}>
          <Text fontWeight="semibold">{t('no_member.title')}</Text>
          <Text fontSize="sm">
            {t('no_member.message')}
          </Text>
        </VStack>
      </Alert>
    </Box>
  );
}

export default MyAccount;
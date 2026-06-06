/**
 * New Member Application Page
 * 
 * This page handles member applications for different user types:
 * - verzoek_lid users: Show application form directly
 * - Existing members: Redirect to dashboard
 * - Unauthenticated users: Show information about membership and login
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ApiService } from '../services/apiService';
import NewMemberApplicationForm from '../components/NewMemberApplicationForm';
import {
  Box,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  VStack,
  Text,
  Heading,
  Button
} from '@chakra-ui/react';

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

interface NewMemberApplicationProps {
  user: User;
}

const NewMemberApplication: React.FC<NewMemberApplicationProps> = ({ user }) => {
  const navigate = useNavigate();
  const { t } = useTranslation('members');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [showApplicationForm, setShowApplicationForm] = useState(false);

  useEffect(() => {
    const handleUserStatus = async () => {
      try {
        // Debug: Log user object to understand its structure
        console.log('NewMemberApplication - User object:', user);
        console.log('NewMemberApplication - User email:', user?.attributes?.email);
        console.log('NewMemberApplication - User roles:', user?.signInUserSession?.accessToken?.payload?.['cognito:groups']);

        // Check if user is authenticated (multiple ways to verify)
        const userEmail = user?.attributes?.email;
        
        // Get user roles using the same method as authHeaders.ts
        let userRoles: string[] = [];
        
        // Try to get roles from JWT token directly
        try {
          const accessToken = (user?.signInUserSession?.accessToken as any)?.jwtToken;
          if (accessToken) {
            // Decode JWT token to get roles
            const tokenParts = accessToken.split('.');
            if (tokenParts.length === 3) {
              const payload = JSON.parse(atob(tokenParts[1]));
              userRoles = payload['cognito:groups'] || [];
            }
          }
        } catch (jwtError) {
          console.error('NewMemberApplication - Error parsing JWT:', jwtError);
        }

        // Fallback: try the original method
        if (userRoles.length === 0) {
          userRoles = user?.signInUserSession?.accessToken?.payload?.['cognito:groups'] || [];
        }
        
        const isAuthenticated = userEmail || userRoles.length > 0;

        if (!isAuthenticated) {
          // User not authenticated - show information page
          console.log('NewMemberApplication - User not authenticated, showing info page');
          setIsLoading(false);
          return;
        }

        const isVerzoekLid = userRoles.includes('verzoek_lid');
        const isHdcnLeden = userRoles.includes('hdcnLeden');

        console.log('NewMemberApplication - User email:', userEmail);
        console.log('NewMemberApplication - User roles (corrected):', userRoles);
        console.log('NewMemberApplication - Is verzoek_lid:', isVerzoekLid);
        console.log('NewMemberApplication - Is hdcnLeden:', isHdcnLeden);
        console.log('NewMemberApplication - Is hdcnLeden:', isHdcnLeden);

        // For verzoek_lid users, redirect to MyAccount for self-service application
        if (isVerzoekLid) {
          console.log('NewMemberApplication - verzoek_lid user, redirecting to MyAccount');
          navigate('/my-account');
          return;
        }

        // For other authenticated users, check if they have a member record
        try {
          const response = await ApiService.get('/members/me');
          
          if (response.success && response.data) {
            // User has member record - redirect to dashboard
            console.log('NewMemberApplication - User has existing member record, redirecting to dashboard');
            navigate('/');
            return;
          }
        } catch (memberCheckError) {
          console.log('NewMemberApplication - Error checking member record (this may be normal):', memberCheckError);
        }

        // User is authenticated but has no specific role or member record
        setIsLoading(false);

      } catch (error) {
        console.error('NewMemberApplication - Error checking user status:', error);
        setError(t('new_application.check_error'));
        setIsLoading(false);
      }
    };

    handleUserStatus();
  }, [user, navigate, t]);

  // Handle application submission
  const handleSubmitApplication = async (applicationData: any) => {
    try {
      // Use /members/me POST endpoint to create new member record
      const response = await ApiService.post('/members/me', {
        ...applicationData,
        email: user?.attributes?.email, // Ensure email matches Cognito
        status: 'Aangemeld',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
      
      if (response.success) {
        console.log('NewMemberApplication - Member application created successfully:', response.data);
        // Redirect to confirmation page
        navigate('/application-submitted');
      } else {
        throw new Error(response.error || 'Failed to create member application');
      }
    } catch (error) {
      console.error('NewMemberApplication - Error creating member application:', error);
      throw error; // Let the form handle the error display
    }
  };

  const handleCancel = () => {
    // Redirect back to dashboard
    navigate('/');
  };

  if (isLoading) {
    return (
      <Box 
        display="flex" 
        justifyContent="center" 
        alignItems="center" 
        minH="100vh" 
        bg="black"
      >
        <VStack spacing={4}>
          <Spinner size="xl" color="orange.500" thickness="4px" />
          <Text color="gray.300">{t('new_application.checking')}</Text>
        </VStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box maxW="600px" mx="auto" p={6} bg="black" minH="100vh">
        <Alert status="error" bg="red.900" color="white" borderRadius="lg">
          <AlertIcon />
          <Box>
            <AlertTitle>{t('new_application.error_title')}</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Box>
        </Alert>
      </Box>
    );
  }

  // Show application form for verzoek_lid users
  if (showApplicationForm && user?.attributes?.email) {
    return (
      <NewMemberApplicationForm
        userEmail={user.attributes.email}
        onSubmit={handleSubmitApplication}
        onCancel={handleCancel}
      />
    );
  }

  // Show information page for unauthenticated users or users without proper roles
  return (
    <Box maxW="800px" mx="auto" p={6} bg="black" minH="100vh">
      <VStack spacing={6} align="stretch">
        <Box textAlign="center">
          <Heading size="xl" color="orange.300" mb={4}>
            {t('new_application.page_title')}
          </Heading>
          <Text color="gray.300" fontSize="lg" mb={6}>
            {t('new_application.page_subtitle')}
          </Text>
        </Box>

        <Alert status="info" bg="blue.900" color="white" borderRadius="lg">
          <AlertIcon />
          <Box>
            <AlertTitle>{t('new_application.info_title')}</AlertTitle>
            <AlertDescription>
              {t('new_application.info_desc')}
            </AlertDescription>
          </Box>
        </Alert>

        <VStack spacing={4}>
          <Text color="gray.300" textAlign="center">
            {t('new_application.login_prompt')}
          </Text>
          
          <Button
            colorScheme="orange"
            size="lg"
            onClick={() => navigate('/')}
          >
            {t('new_application.to_login')}
          </Button>
        </VStack>

        <Box bg="gray.800" p={6} borderRadius="lg" border="1px" borderColor="orange.400">
          <Heading size="md" color="orange.300" mb={4}>
            {t('new_application.about_title')}
          </Heading>
          <VStack align="start" spacing={3} color="gray.300">
            <Text>• {t('new_application.benefit_events')}</Text>
            <Text>• {t('new_application.benefit_magazine')}</Text>
            <Text>• {t('new_application.benefit_webshop')}</Text>
            <Text>• {t('new_application.benefit_network')}</Text>
            <Text>• {t('new_application.benefit_regional')}</Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
};

export default NewMemberApplication;
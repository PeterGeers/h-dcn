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
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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
        setError('Er is een fout opgetreden bij het controleren van uw gegevens.');
        setIsLoading(false);
      }
    };

    handleUserStatus();
  }, [user, navigate]);

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
          <Text color="gray.300">Gegevens controleren...</Text>
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
            <AlertTitle>Fout opgetreden</AlertTitle>
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
            Lid worden van H-DCN
          </Heading>
          <Text color="gray.300" fontSize="lg" mb={6}>
            Welkom bij de Harley-Davidson Club Nederland
          </Text>
        </Box>

        <Alert status="info" bg="blue.900" color="white" borderRadius="lg">
          <AlertIcon />
          <Box>
            <AlertTitle>Lidmaatschap aanvragen</AlertTitle>
            <AlertDescription>
              Om lid te worden van de H-DCN moet u eerst inloggen of een account aanmaken.
              Na het inloggen kunt u uw lidmaatschapsaanvraag indienen.
            </AlertDescription>
          </Box>
        </Alert>

        <VStack spacing={4}>
          <Text color="gray.300" textAlign="center">
            Heeft u al een account? Log dan in om uw aanvraag in te dienen.
          </Text>
          
          <Button
            colorScheme="orange"
            size="lg"
            onClick={() => navigate('/')}
          >
            Naar Inlogpagina
          </Button>
        </VStack>

        <Box bg="gray.800" p={6} borderRadius="lg" border="1px" borderColor="orange.400">
          <Heading size="md" color="orange.300" mb={4}>
            Over het lidmaatschap
          </Heading>
          <VStack align="start" spacing={3} color="gray.300">
            <Text>• Toegang tot alle H-DCN evenementen en ritten</Text>
            <Text>• Maandelijks clubblad (digitaal of papier)</Text>
            <Text>• Toegang tot de webshop met exclusieve producten</Text>
            <Text>• Netwerk van Harley-Davidson liefhebbers</Text>
            <Text>• Regionale activiteiten en bijeenkomsten</Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
};

export default NewMemberApplication;
/**
 * New Member Application Page
 * 
 * This page is shown to users who have successfully logged in via Cognito
 * but don't exist in the member database yet. It guides them through the
 * membership application process using the field registry system.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { membershipService } from '../utils/membershipService';
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
  Heading
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
  const [userExists, setUserExists] = useState<boolean | null>(null);

  useEffect(() => {
    const checkUserExists = async () => {
      if (!user?.attributes?.email) {
        setError('Geen gebruiker ingelogd');
        setIsLoading(false);
        return;
      }

      try {
        // Check if user already exists in member database
        const existingMember = await membershipService.getMemberByEmail(user.attributes.email);
        
        if (existingMember) {
          // User exists, redirect to dashboard
          setUserExists(true);
          navigate('/dashboard');
        } else {
          // User doesn't exist, show application form
          setUserExists(false);
        }
      } catch (error) {
        console.error('Error checking user existence:', error);
        // If error checking, assume user doesn't exist and show form
        setUserExists(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkUserExists();
  }, [user, navigate]);

  const handleSubmitApplication = async (applicationData: any) => {
    try {
      // Submit the membership application
      await membershipService.submitMembershipApplication({
        ...applicationData,
        email: user?.attributes?.email,
        cognito_user_id: user?.attributes?.email, // Use email as Cognito user ID
        application_date: new Date().toISOString(),
        status: 'Aangemeld'
      });

      // Redirect to a confirmation page or dashboard
      navigate('/application-submitted');
    } catch (error) {
      console.error('Error submitting application:', error);
      throw error; // Let the form handle the error display
    }
  };

  const handleCancel = () => {
    // Redirect back to login or home page
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

  if (userExists === true) {
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
          <Text color="gray.300">Doorverwijzen naar dashboard...</Text>
        </VStack>
      </Box>
    );
  }

  if (userExists === false && user?.attributes?.email) {
    return (
      <NewMemberApplicationForm
        userEmail={user.attributes.email}
        onSubmit={handleSubmitApplication}
        onCancel={handleCancel}
      />
    );
  }

  return (
    <Box maxW="600px" mx="auto" p={6} bg="black" minH="100vh">
      <Alert status="warning" bg="yellow.900" color="white" borderRadius="lg">
        <AlertIcon />
        <Box>
          <AlertTitle>Onbekende status</AlertTitle>
          <AlertDescription>
            Er kon niet worden bepaald of u al lid bent. Probeer opnieuw in te loggen.
          </AlertDescription>
        </Box>
      </Alert>
    </Box>
  );
};

export default NewMemberApplication;
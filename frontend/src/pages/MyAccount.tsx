/**
 * My Account Page - Member Self-Service
 * 
 * Allows members to view and edit their own data using the field registry system
 * Enhanced to support member application flow for verzoek_lid users
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  Spinner,
  Text,
  Alert,
  AlertIcon,
  Button,
  Heading
} from '@chakra-ui/react';
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
  
  const { handleError } = useErrorHandler();

  // Check if user is verzoek_lid (applicant)
  useEffect(() => {
    let userRoles: string[] = [];
    
    // Try to get roles from JWT token directly (same method as NewMemberApplication)
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
        setError('Geen gebruikersgegevens beschikbaar');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        
        // Use the /members/me endpoint for self-lookup
        const response = await ApiService.get('/members/me');
        
        if (response.success && response.data) {
          // Compute calculated fields for the member data
          const memberWithCalculatedFields = computeCalculatedFields(response.data);
          setMember(memberWithCalculatedFields);
          console.log('Member data loaded successfully:', memberWithCalculatedFields);
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
          setError('Fout bij het laden van uw gegevens. Probeer het later opnieuw.');
        }
      } finally {
        setLoading(false);
      }
    };

    loadMemberData();
  }, [user, isVerzoekLid]);

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
      handleError(error, 'Fout bij het bijwerken van uw gegevens');
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
        
        // Don't reload the page - stay in application form for verzoek_lid users
      } else {
        throw new Error(response.error || 'Failed to process member application');
      }
    } catch (error) {
      console.error('Error creating member application:', error);
      throw error; // Let the form handle the error display
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minH="400px">
        <VStack spacing={4}>
          <Spinner size="xl" color="orange.500" />
          <Text>Uw gegevens laden...</Text>
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
            <Text fontWeight="semibold">Fout bij laden gegevens</Text>
            <Text fontSize="sm">{error}</Text>
          </VStack>
        </Alert>
      </Box>
    );
  }

  // Show application form for verzoek_lid users who want to create/edit their application
  // OR for verzoek_lid users with existing applications that are still pending (status: 'Aangemeld')
  if (showApplicationForm || (isVerzoekLid && (!member || member.status === 'Aangemeld'))) {
    return (
      <NewMemberApplicationForm
        userEmail={user?.attributes?.email || ''}
        onSubmit={handleMemberApplicationSubmit}
        onCancel={() => setShowApplicationForm(false)}
      />
    );
  }

  // Show member data if it exists
  if (member) {
    return (
      <VStack spacing={6} align="stretch">
        {/* Show status for verzoek_lid users */}
        {isVerzoekLid && (
          <Box p={4} bg="orange.50" borderRadius="md" border="1px" borderColor="orange.200">
            <VStack align="start" spacing={2}>
              <Heading size="sm" color="orange.700">Aanvraag Status</Heading>
              <Text fontSize="sm" color="orange.600">
                Status: <strong>{member.status || 'Aangemeld'}</strong>
              </Text>
              <Text fontSize="sm" color="orange.600">
                Ingediend: {member.created_at ? new Date(member.created_at).toLocaleDateString('nl-NL') : 'Onbekend'}
              </Text>
              <Button
                size="sm"
                colorScheme="orange"
                variant="outline"
                onClick={() => setShowApplicationForm(true)}
              >
                Gegevens Wijzigen
              </Button>
            </VStack>
          </Box>
        )}
        
        <MemberSelfServiceView 
          member={member}
          onUpdate={handleMemberUpdate}
        />
      </VStack>
    );
  }

  // Show application prompt for verzoek_lid users without member record
  if (isVerzoekLid) {
    return (
      <Box p={6}>
        <Alert status="info">
          <AlertIcon />
          <VStack align="start" spacing={3}>
            <Text fontWeight="semibold">Welkom bij H-DCN!</Text>
            <Text fontSize="sm">
              U bent ingelogd als aanvrager. U kunt nu uw lidmaatschapsaanvraag indienen.
            </Text>
            <Button
              colorScheme="orange"
              onClick={() => setShowApplicationForm(true)}
            >
              Lidmaatschapsaanvraag Indienen
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
          <Text fontWeight="semibold">Geen lidgegevens gevonden</Text>
          <Text fontSize="sm">
            U bent nog geen lid van de H-DCN. 
            <Text as="a" href="/new-member-application" color="orange.500" textDecoration="underline" ml={1}>
              Klik hier om lid te worden
            </Text>
          </Text>
        </VStack>
      </Alert>
    </Box>
  );
}

export default MyAccount;
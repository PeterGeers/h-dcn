/**
 * My Account Page - Member Self-Service
 * 
 * Allows members to view and edit their own data using the field registry system
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  Spinner,
  Text,
  Alert,
  AlertIcon
} from '@chakra-ui/react';
import MemberSelfServiceView from '../components/MemberSelfServiceView';
import { Member } from '../types';
import { getAuthHeaders, getAuthHeadersForGet } from '../utils/authHeaders';
import { API_URLS } from '../config/api';
import { useErrorHandler, apiCall } from '../utils/errorHandler';

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
  
  const { handleError } = useErrorHandler();

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
        
        // First check if member exists by loading all members and finding by email
        const headers = await getAuthHeadersForGet();
        const allMembers = await apiCall<any>(
          fetch(API_URLS.members(), { headers }),
          'laden leden'
        );
        
        const memberData = Array.isArray(allMembers) ? allMembers : (allMembers?.members || []);
        const foundMember = memberData.find((m: any) => m.email === user.attributes.email);
        
        if (foundMember) {
          setMember(foundMember);
        } else {
          setError('Geen lidgegevens gevonden. Bent u al lid van de H-DCN?');
        }
      } catch (error) {
        console.error('Error loading member data:', error);
        setError('Fout bij het laden van uw gegevens. Probeer het later opnieuw.');
      } finally {
        setLoading(false);
      }
    };

    loadMemberData();
  }, [user]);

  // Handle member data update
  const handleMemberUpdate = async (memberData: any) => {
    try {
      const headers = await getAuthHeaders();
      const updatedMember = await apiCall<Member>(
        fetch(API_URLS.member(member?.member_id || ''), {
          method: 'PUT',
          headers,
          body: JSON.stringify({
            ...memberData,
            updated_at: new Date().toISOString()
          })
        }),
        'bijwerken gegevens'
      );
      
      setMember(updatedMember);
    } catch (error) {
      handleError(error, 'Fout bij het bijwerken van uw gegevens');
      throw error; // Re-throw so the component can handle it
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

  if (!member) {
    return (
      <Box p={6}>
        <Alert status="info">
          <AlertIcon />
          <VStack align="start" spacing={1}>
            <Text fontWeight="semibold">Geen lidgegevens gevonden</Text>
            <Text fontSize="sm">
              U bent nog geen lid van de H-DCN. 
              <Text as="a" href="/membership" color="orange.500" textDecoration="underline" ml={1}>
                Klik hier om lid te worden
              </Text>
            </Text>
          </VStack>
        </Alert>
      </Box>
    );
  }

  return (
    <MemberSelfServiceView 
      member={member}
      onUpdate={handleMemberUpdate}
    />
  );
}

export default MyAccount;
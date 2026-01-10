/**
 * Membership Form Page - Using Field Registry System
 * 
 * Progressive disclosure membership application form using membershipApplication context
 */

import React from 'react';
import { Box } from '@chakra-ui/react';
import MemberApplicationForm from '../components/MemberApplicationForm';
import { apiCall } from '../utils/errorHandler';
import { API_URLS } from '../config/api';
import { getAuthHeaders } from '../utils/authHeaders';

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

interface MembershipFormProps {
  user: User;
}

function MembershipForm({ user }: MembershipFormProps) {
  const handleSubmit = async (data: any) => {
    try {
      const headers = await getAuthHeaders();
      await apiCall<any>(
        fetch(API_URLS.members(), {
          method: 'POST',
          headers,
          body: JSON.stringify(data)
        }),
        'verzenden aanmelding'
      );
    } catch (error) {
      console.error('Error submitting membership application:', error);
      throw error;
    }
  };

  const handleCancel = () => {
    window.history.back();
  };

  return (
    <Box minH="100vh" bg="black" py={8}>
      <MemberApplicationForm 
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        userRole={user?.signInUserSession?.accessToken?.payload?.['cognito:groups']?.[0] || 'Members_CRUD'}
      />
    </Box>
  );
}

export default MembershipForm;
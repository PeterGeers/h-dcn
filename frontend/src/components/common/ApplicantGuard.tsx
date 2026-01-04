import React, { ReactNode, useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Box, Spinner, Center } from '@chakra-ui/react';
import { membershipService } from '../../utils/membershipService';

interface CognitoUser {
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: string[];
      };
      jwtToken?: string;
    };
  };
  attributes?: {
    email?: string;
  };
}

interface ApplicantGuardProps {
  user: CognitoUser;
  children: ReactNode;
}

/**
 * ApplicantGuard ensures that users with 'Verzoek_lid' role who haven't 
 * completed their membership application are redirected to the application form.
 */
function ApplicantGuard({ user, children }: ApplicantGuardProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [isChecking, setIsChecking] = useState(true);
  const [shouldRedirect, setShouldRedirect] = useState(false);

  // Routes that applicants can access without completing their application
  const applicantAllowedRoutes = [
    '/new-member-application',
    '/application-submitted'
  ];

  useEffect(() => {
    const checkApplicantStatus = async () => {
      try {
        // Get user groups
        let userGroups: string[] = [];
        const amplifyGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'];
        if (amplifyGroups && Array.isArray(amplifyGroups)) {
          userGroups = amplifyGroups;
        } else {
          // Try to decode JWT token
          const jwtToken = user.signInUserSession?.accessToken?.jwtToken;
          if (jwtToken) {
            try {
              const parts = jwtToken.split('.');
              if (parts.length === 3) {
                const payload = JSON.parse(atob(parts[1]));
                userGroups = payload['cognito:groups'] || [];
              }
            } catch (error) {
              console.error('Error decoding JWT token:', error);
            }
          }
        }

        // Check if user is an applicant
        const isApplicant = userGroups.includes('Verzoek_lid');
        
        if (isApplicant && user.attributes?.email) {
          // Check if they already exist in the member database
          try {
            const existingMember = await membershipService.getMemberByEmail(user.attributes.email);
            
            if (!existingMember) {
              // User is an applicant and doesn't exist in member database
              // They need to complete their application
              const isOnAllowedRoute = applicantAllowedRoutes.includes(location.pathname);
              
              if (!isOnAllowedRoute) {
                setShouldRedirect(true);
              }
            }
          } catch (error) {
            // If we can't check member status, assume they need to complete application
            console.warn('Could not check member status:', error);
            const isOnAllowedRoute = applicantAllowedRoutes.includes(location.pathname);
            
            if (!isOnAllowedRoute) {
              setShouldRedirect(true);
            }
          }
        }
      } catch (error) {
        console.error('Error in ApplicantGuard:', error);
      } finally {
        setIsChecking(false);
      }
    };

    checkApplicantStatus();
  }, [user, location.pathname]);

  useEffect(() => {
    if (shouldRedirect && !isChecking) {
      navigate('/new-member-application', { replace: true });
    }
  }, [shouldRedirect, isChecking, navigate]);

  if (isChecking) {
    return (
      <Box minH="100vh" bg="black">
        <Center h="100vh">
          <Spinner size="xl" color="orange.400" />
        </Center>
      </Box>
    );
  }

  if (shouldRedirect) {
    return (
      <Box minH="100vh" bg="black">
        <Center h="100vh">
          <Spinner size="xl" color="orange.400" />
        </Center>
      </Box>
    );
  }

  return <>{children}</>;
}

export default ApplicantGuard;
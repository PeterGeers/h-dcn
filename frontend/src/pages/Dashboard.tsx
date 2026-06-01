import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, VStack, Heading, Text, SimpleGrid, Spinner, Center } from '@chakra-ui/react';
import AppCard from '../components/AppCard';
import { FunctionGuard } from '../components/common/FunctionGuard';
import { membershipService } from '../utils/membershipService';
import { useAuth } from '../context/AuthProvider';

function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [isCheckingMembership, setIsCheckingMembership] = useState(true);
  const [memberExists, setMemberExists] = useState<boolean | null>(null);

  // Get groups directly from auth context (R4.2 - groups from access token payload)
  const userGroups = user?.groups ?? [];

  // Build a compatibility shim for FunctionGuard which still expects the legacy user shape
  const functionGuardUser = useMemo(() => {
    if (!user) return null;
    return {
      signInUserSession: {
        accessToken: {
          payload: {
            'cognito:groups': user.groups,
          },
          jwtToken: user.accessToken,
        },
      },
      attributes: {
        email: user.email,
        given_name: user.givenName,
        family_name: user.familyName,
      },
    };
  }, [user]);

  // Check if user exists as member and redirect to application if not
  useEffect(() => {
    const checkMembershipStatus = async () => {
      if (!user?.email) {
        setIsCheckingMembership(false);
        return;
      }

      // Check if user has valid member roles (not just verzoek_lid)
      const hasValidMemberRole = userGroups.some(group => 
        group === 'hdcnLeden' || 
        group.includes('Members_') || 
        group.includes('Events_') || 
        group.includes('Products_') || 
        group.includes('System_') || 
        group.includes('Communication_') ||
        group.includes('National_') ||
        group.includes('Regional_') ||
        group.includes('Webmaster') ||
        group.includes('Regio_')
      );

      const isOnlyApplicant = userGroups.length === 1 && userGroups.includes('verzoek_lid');
      const hasNoGroups = userGroups.length === 0;
      const hasHdcnLedenRole = userGroups.includes('hdcnLeden');
      const hasVerzoekLidRole = userGroups.includes('verzoek_lid');

      // If user has valid member roles, allow access immediately
      if (hasValidMemberRole) {
        setMemberExists(true);
        setIsCheckingMembership(false);
        return;
      }

      // Check if user has either verzoek_lid or hdcnLeden role for member lookup
      if (hasHdcnLedenRole || hasVerzoekLidRole) {
        try {
          const existingMember = await membershipService.getMemberByEmail(user.email);
          
          if (hasHdcnLedenRole && !existingMember) {
            // hdcnLeden users should always have data in the members table
            console.error('Dashboard - hdcnLeden user not found in database, this is unexpected');
            // Still allow access but log the issue
            setMemberExists(true);
          } else if (hasVerzoekLidRole && !existingMember) {
            // verzoek_lid users may not have data yet, redirect to application
            navigate('/new-member-application');
            return;
          } else if (hasVerzoekLidRole && existingMember) {
            // verzoek_lid users WITH data should go directly to their application
            navigate('/my-account');
            return;
          } else {
            // User found in database
            setMemberExists(true);
          }
        } catch (error) {
          console.error('Error checking membership status:', error);
          
          if (hasHdcnLedenRole) {
            // For hdcnLeden, assume they exist and show dashboard on error
            setMemberExists(true);
          } else if (hasVerzoekLidRole) {
            // For verzoek_lid, redirect to application on error
            navigate('/new-member-application');
            return;
          }
        }
      } else if (hasNoGroups) {
        // User has no groups at all, redirect to application
        navigate('/new-member-application');
        return;
      } else {
        // User has some other roles but not verzoek_lid or hdcnLeden
        setMemberExists(true);
      }

      setIsCheckingMembership(false);
    };

    checkMembershipStatus();
  }, [user, userGroups, navigate]);

  // Show loading while checking membership status
  if (isCheckingMembership) {
    return (
      <Center h="400px">
        <VStack spacing={4}>
          <Spinner size="xl" color="orange.400" thickness="4px" />
          <Text color="gray.300">Lidmaatschap controleren...</Text>
        </VStack>
      </Center>
    );
  }

  // If member doesn't exist, the redirect should have happened
  if (memberExists === false) {
    return (
      <Center h="400px">
        <VStack spacing={4}>
          <Spinner size="xl" color="orange.400" thickness="4px" />
          <Text color="gray.300">Doorverwijzen naar aanmeldingsformulier...</Text>
        </VStack>
      </Center>
    );
  }

  // Derive permission flags from groups (R4.2 - no manual JWT decoding)
  const isBasicMember = userGroups.includes('hdcnLeden');
  const hasAdminRoles = userGroups.some(group => 
    group.includes('Members_') || 
    group.includes('Events_') || 
    group.includes('Products_') || 
    group.includes('System_') || 
    group.includes('Communication_') ||
    group.includes('National_') ||
    group.includes('Regional_') ||
    group.includes('Webmaster')
  );
  const isLid = userGroups.length > 0;

  return (
    <Box maxW="1200px" mx="auto" px={{ base: 2, md: 0 }}>
      <VStack spacing={{ base: 4, md: 6 }} align="stretch">
        <Box textAlign="center">
          <Heading 
            color="orange.500" 
            mb={2}
            size={{ base: 'lg', md: 'xl' }}
            px={{ base: 2, md: 0 }}
          >
            Welkom, {user?.givenName || 'Gebruiker'} {user?.familyName || ''}!
          </Heading>
          <Text 
            color="gray.600"
            fontSize={{ base: 'sm', md: 'md' }}
            px={{ base: 2, md: 0 }}
          >
            {isLid ? (
              isBasicMember && !hasAdminRoles ? 
                'Als H-DCN lid heb je toegang tot je persoonlijke gegevens en de webshop:' :
                'Kies een applicatie om te starten:'
            ) : 'Meld je aan om lid te worden van de H-DCN:'}
          </Text>
          {isBasicMember && !hasAdminRoles && (
            <Text 
              color="gray.500"
              fontSize={{ base: 'xs', md: 'sm' }}
              px={{ base: 2, md: 0 }}
              mt={2}
            >
              Voor toegang tot beheerfuncties neem contact op met de administratie.
            </Text>
          )}
        </Box>
        
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={{ base: 4, md: 6 }}>
          {/* My Account - Only for existing members */}
          {isLid && (
            <AppCard 
              key="my-account"
              app={{
                id: 'my-account',
                title: 'Mijn Gegevens',
                description: 'Bekijk en bewerk uw persoonlijke gegevens',
                icon: '👤',
                path: '/my-account'
              }}
              onClick={() => navigate('/my-account')}
            />
          )}
          
          {/* Membership Application - Only for non-members */}
          {!isLid && (
            <AppCard 
              key="membership"
              app={{
                id: 'membership',
                title: 'Aanmelden als Lid',
                description: 'Word lid van de H-DCN met ons nieuwe aanmeldingsformulier',
                icon: '📝',
                path: '/membership'
              }}
              onClick={() => navigate('/membership')}
            />
          )}
          
          {/* Webshop - Only for members with hdcnLeden role or higher */}
          <FunctionGuard 
            user={functionGuardUser} 
            functionName="webshop" 
            action="read"
            requiredRoles={['hdcnLeden']}
          >
            <AppCard 
              key="webshop"
              app={{
                id: 'webshop',
                title: 'Webshop',
                description: 'Bestellen en bestellingen bekijken',
                icon: '🛒',
                path: '/webshop'
              }}
              onClick={() => navigate('/webshop')}
            />
          </FunctionGuard>
          
          {/* Administrative modules - Only for users with specific admin roles */}
          
          {/* Members Admin - Only for users with member management roles */}
          <FunctionGuard 
            user={functionGuardUser} 
            functionName="members" 
            action="read"
            requiredRoles={['Members_Read', 'Members_CRUD', 'System_User_Management']}
          >
            <AppCard 
              key="members"
              app={{
                id: 'members',
                title: 'Ledenadministratie',
                description: 'Beheer leden en lidmaatschappen',
                icon: '👥',
                path: '/members'
              }}
              onClick={() => navigate('/members')}
            />
          </FunctionGuard>
          
          {/* Events Admin - Only for users with event management roles */}
          <FunctionGuard 
            user={functionGuardUser} 
            functionName="events" 
            action="read"
            requiredRoles={['Events_Read', 'Events_CRUD', 'System_User_Management']}
          >
            <AppCard 
              key="events"
              app={{
                id: 'events',
                title: 'Evenementenadministratie',
                description: 'Beheer evenementen en financiën',
                icon: '📅',
                path: '/events'
              }}
              onClick={() => navigate('/events')}
            />
          </FunctionGuard>
          
          {/* Products Admin - Only for users with product management roles */}
          <FunctionGuard 
            user={functionGuardUser} 
            functionName="products" 
            action="read"
            requiredRoles={['Products_Read', 'Products_CRUD', 'Webshop_Management', 'System_User_Management']}
          >
            <AppCard 
              key="products"
              app={{
                id: 'products',
                title: 'Product Management',
                description: 'Beheer webshop producten',
                icon: '📦',
                path: '/products'
              }}
              onClick={() => navigate('/products')}
            />
          </FunctionGuard>
          
          {/* Advanced Exports - Only for users with advanced product management roles */}
          <FunctionGuard 
            user={functionGuardUser} 
            functionName="advanced-exports" 
            action="read"
            requiredRoles={['Products_CRUD', 'Webshop_Management', 'System_User_Management']}
          >
            <AppCard 
              key="advanced-exports"
              app={{
                id: 'advanced-exports',
                title: 'Geavanceerde Exports',
                description: 'Bulk exports en analytics',
                icon: '🚀',
                path: '/advanced-exports'
              }}
              onClick={() => navigate('/advanced-exports')}
            />
          </FunctionGuard>
          
          {/* Membership Management - Only for users with full member CRUD access */}
          <FunctionGuard 
            user={functionGuardUser} 
            functionName="memberships" 
            action="read"
            requiredRoles={['Members_CRUD', 'System_User_Management']}
          >
            <AppCard 
              key="memberships"
              app={{
                id: 'memberships',
                title: 'Lidmaatschap Beheer',
                description: 'Beheer lidmaatschapstypen',
                icon: '🎫',
                path: '/memberships'
              }}
              onClick={() => navigate('/memberships')}
            />
          </FunctionGuard>
        </SimpleGrid>
        

      </VStack>
    </Box>
  );
}

export default Dashboard;

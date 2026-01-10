import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, VStack, Heading, Text, SimpleGrid, Alert, AlertIcon, Spinner, Center } from '@chakra-ui/react';
import AppCard from '../components/AppCard';
import { FunctionGuard } from '../components/common/FunctionGuard';
import { initializeFunctionPermissions } from '../utils/initializeFunctionPermissions';
import { membershipService } from '../utils/membershipService';

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
      jwtToken?: string;
    };
  };
}

interface DashboardProps {
  user: User;
}

function Dashboard({ user }: DashboardProps) {
  const navigate = useNavigate();
  const [isCheckingMembership, setIsCheckingMembership] = useState(true);
  const [memberExists, setMemberExists] = useState<boolean | null>(null);
  
  // Check if user exists as member and redirect to application if not
  useEffect(() => {
    const checkMembershipStatus = async () => {
      if (!user?.attributes?.email) {
        setIsCheckingMembership(false);
        return;
      }

      try {
        const existingMember = await membershipService.getMemberByEmail(user.attributes.email);
        
        if (!existingMember) {
          // User doesn't exist in member database, redirect to application
          navigate('/new-member-application');
          return;
        }
        
        setMemberExists(true);
      } catch (error) {
        console.error('Error checking membership status:', error);
        // On error, assume user exists and show dashboard
        setMemberExists(true);
      } finally {
        setIsCheckingMembership(false);
      }
    };

    checkMembershipStatus();
  }, [user, navigate]);
  
  // Initialize function permissions on first load (background task)
  useEffect(() => {
    const init = async () => {
      try {
        await initializeFunctionPermissions();
      } catch (error) {
        console.error('❌ Failed to initialize function permissions:', error);
      }
    };
    init();
  }, []);

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
  
  // Extract user roles from Cognito token - try payload first, then decode JWT
  let userGroups: string[] = [];
  
  // First try the payload
  const payloadGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'];
  if (payloadGroups && Array.isArray(payloadGroups)) {
    userGroups = payloadGroups;
  } else {
    // If payload is empty, decode the JWT token directly
    const jwtToken = user.signInUserSession?.accessToken?.jwtToken;
    if (jwtToken) {
      try {
        const parts = jwtToken.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1]));
          userGroups = payload['cognito:groups'] || [];
        }
      } catch (error) {
        console.error('Error decoding JWT token in Dashboard:', error);
      }
    }
  }
  
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
            Welkom, {user?.attributes?.given_name || 'Gebruiker'} {user?.attributes?.family_name || ''}!
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
            user={user} 
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
            user={user} 
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
            user={user} 
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
            user={user} 
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
            user={user} 
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
          
          {/* Parameters - Only for system administrators */}
          <FunctionGuard 
            user={user} 
            functionName="parameters" 
            action="read"
            requiredRoles={['System_User_Management']}
          >
            <AppCard 
              key="parameters"
              app={{
                id: 'parameters',
                title: 'Parameter Beheer',
                description: 'Beheer functionele variabelen',
                icon: '⚙️',
                path: '/parameters'
              }}
              onClick={() => navigate('/parameters')}
            />
          </FunctionGuard>
          
          {/* Membership Management - Only for users with full member CRUD access */}
          <FunctionGuard 
            user={user} 
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

          {/* Field Registry Test - Only for system administrators and developers */}
          <FunctionGuard 
            user={user} 
            functionName="field-registry-test" 
            action="read"
            requiredRoles={['System_User_Management']}
          >
            <AppCard 
              key="field-registry-test"
              app={{
                id: 'field-registry-test',
                title: '🧪 Field Registry Test',
                description: 'Test field registry system & modal views',
                icon: '🔬',
                path: '/test/field-registry'
              }}
              onClick={() => navigate('/test/field-registry')}
            />
          </FunctionGuard>
        </SimpleGrid>
        

      </VStack>
    </Box>
  );
}

export default Dashboard;
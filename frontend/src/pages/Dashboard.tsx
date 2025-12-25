import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, VStack, Heading, Text, SimpleGrid, Alert, AlertIcon } from '@chakra-ui/react';
import AppCard from '../components/AppCard';
import { FunctionGuard } from '../components/common/FunctionGuard';
import { initializeFunctionPermissions } from '../utils/initializeFunctionPermissions';

interface User {
  attributes?: {
    given_name?: string;
    family_name?: string;
  };
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: string[];
      };
    };
  };
}

interface DashboardProps {
  user: User;
}

function Dashboard({ user }: DashboardProps) {
  const navigate = useNavigate();
  
  // Initialize function permissions on first load (background task)
  useEffect(() => {
    const init = async () => {
      try {
        await initializeFunctionPermissions();
        console.log('✅ Function permissions initialized');
      } catch (error) {
        console.error('❌ Failed to initialize function permissions:', error);
      }
    };
    init();
  }, []);
  
  // Extract user roles from Cognito token
  const userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
  const isBasicMember = userGroups.includes('hdcnLeden');
  const hasAdminRoles = userGroups.some(group => 
    group.includes('Members_') || 
    group.includes('Events_') || 
    group.includes('Products_') || 
    group.includes('System_') || 
    group.includes('Communication_') ||
    group.includes('National_') ||
    group.includes('Regional_') ||
    group.includes('Webmaster') ||
    group.includes('hdcnAdmins')
  );
  const isLid = userGroups.length > 0;
  
  console.log('🔍 Dashboard - User groups:', userGroups);
  console.log('🔍 Dashboard - Is basic member:', isBasicMember);
  console.log('🔍 Dashboard - Has admin roles:', hasAdminRoles);

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
          {/* Membership - Always visible for authenticated users */}
          <AppCard 
            key="membership"
            app={{
              id: 'membership',
              title: isLid ? 'Lidmaatschap Gegevens' : 'Aanmelden als Lid',
              description: isLid ? 'Hier kun je je lidmaatschap gegevens wijzigen' : 'Word lid van de H-DCN',
              icon: '📝',
              path: '/membership'
            }}
            onClick={() => navigate('/membership')}
          />
          
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
            requiredRoles={['Members_Read_All', 'Members_CRUD_All', 'National_Chairman', 'National_Secretary', 'Webmaster', 'Tour_Commissioner', 'Club_Magazine_Editorial']}
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
            requiredRoles={['Events_Read_All', 'Events_CRUD_All', 'National_Chairman', 'National_Secretary', 'Webmaster', 'Tour_Commissioner', 'Club_Magazine_Editorial']}
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
            requiredRoles={['Products_Read_All', 'Products_CRUD_All', 'National_Chairman', 'National_Secretary', 'Webmaster', 'Tour_Commissioner', 'Club_Magazine_Editorial', 'Webshop_Management']}
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
          
          {/* Parameters - Only for system administrators */}
          <FunctionGuard 
            user={user} 
            functionName="parameters" 
            action="read"
            requiredRoles={['System_User_Management', 'System_CRUD_All', 'Webmaster']}
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
            requiredRoles={['Members_CRUD_All', 'Webmaster']}
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
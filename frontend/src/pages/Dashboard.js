import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, VStack, Heading, Text, SimpleGrid, Alert, AlertIcon } from '@chakra-ui/react';
import AppCard from '../components/AppCard';
import { FunctionGuard } from '../components/FunctionGuard';
import { initializeFunctionPermissions } from '../utils/initializeFunctionPermissions';

function Dashboard({ user }) {
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
  
  // Check of gebruiker lid is (heeft groepen)
  const userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
  const isLid = userGroups.length > 0;
  const isAdmin = userGroups.includes('hdcnAdmins');
  
  // Voor leden: normale apps
  const ledenApps = [
    {
      id: 'membership',
      title: 'Lidmaatschap Gegevens',
      description: 'Hier kun je je lidmaatschap gegevens wijzigen',
      icon: '📝',
      path: '/membership'
    },
    {
      id: 'hdcnWinkel',
      title: 'Webshop',
      description: 'Bestellen en bestellingen bekijken',
      icon: '🛒',
      path: '/webshop'
    }
  ];
  
  // Voor admins: extra beheer apps
  const adminApps = [
    {
      id: 'members',
      title: 'Ledenadministratie',
      description: 'Beheer leden en lidmaatschappen',
      icon: '👥',
      path: '/members'
    },
    {
      id: 'events',
      title: 'Evenementenadministratie',
      description: 'Beheer evenementen en financiën',
      icon: '📅',
      path: '/events'
    },
    {
      id: 'hdcnProductManagement',
      title: 'Product Management',
      description: 'Beheer webshop producten',
      icon: '📦',
      path: '/products'
    }
  ];
  
  // Voor niet-leden: alleen aanmelden
  const nietLedenApps = [
    {
      id: 'membership',
      title: 'Aanmelden als Lid',
      description: 'Word lid van de H-DCN',
      icon: '📝',
      path: '/membership'
    }
  ];
  
  const accessibleApps = isLid ? [...ledenApps, ...(isAdmin ? adminApps : [])] : nietLedenApps;

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
            {isLid ? 'Kies een applicatie om te starten:' : 'Meld je aan om lid te worden van de H-DCN:'}
          </Text>
        </Box>
        
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={{ base: 4, md: 6 }}>
          {/* Membership - Always visible */}
          <AppCard 
            key="membership"
            app={{
              id: 'membership',
              title: 'Lidmaatschap Gegevens',
              description: 'Hier kun je je lidmaatschap gegevens wijzigen',
              icon: '📝',
              path: '/membership'
            }}
            onClick={() => navigate('/membership')}
          />
          
          {/* Webshop - Function guarded */}
          <FunctionGuard user={user} functionName="webshop" action="read">
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
          
          {/* Members Admin - Function guarded */}
          <FunctionGuard user={user} functionName="members" action="read">
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
          
          {/* Events Admin - Function guarded */}
          <FunctionGuard user={user} functionName="events" action="read">
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
          
          {/* Products Admin - Function guarded */}
          <FunctionGuard user={user} functionName="products" action="read">
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
          
          {/* Parameters - Function guarded */}
          <FunctionGuard user={user} functionName="parameters" action="read">
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
          
          {/* Membership Management - Function guarded */}
          <FunctionGuard user={user} functionName="memberships" action="read">
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
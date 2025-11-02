import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Box, Flex, Heading, Button, Text, Spacer, HStack, Image } from '@chakra-ui/react';
import { ArrowBackIcon, SettingsIcon } from '@chakra-ui/icons';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { Suspense, lazy } from 'react';
import { Spinner, Center } from '@chakra-ui/react';
import GroupAccessGuard from './components/GroupAccessGuard';

interface User {
  attributes?: {
    given_name?: string;
    family_name?: string;
    email?: string;
  };
}

interface AppProps {
  signOut: () => void;
  user: User;
}

// Lazy load components
const Dashboard = lazy(() => import('./pages/Dashboard')) as any;
const ProfileManager = lazy(() => import('./pages/ProfileManager')) as any;
const MembershipForm = lazy(() => import('./pages/MembershipForm')) as any;
const ParameterManagement = lazy(() => import('./pages/ParameterManagement')) as any;
const WebshopPage = lazy(() => import('./modules/webshop/WebshopPage')) as any;
const ProductManagementPage = lazy(() => import('./modules/products/ProductManagementPage')) as any;
const MemberAdminPage = lazy(() => import('./modules/members/MemberAdminPage')) as any;
const EventAdminPage = lazy(() => import('./modules/events/EventAdminPage')) as any;
const MembershipManagement = lazy(() => import('./pages/MembershipManagement')) as any;

const signUpFields = {
  signUp: {
    username: {
      label: 'E-mailadres',
      placeholder: 'Voer je e-mailadres in',
      isRequired: true,
      order: 1
    },
    given_name: {
      label: 'Voornaam',
      placeholder: 'Voer je voornaam in',
      isRequired: true,
      order: 2
    },
    family_name: {
      label: 'Achternaam', 
      placeholder: 'Voer je achternaam in',
      isRequired: true,
      order: 3
    },
    password: {
      label: 'Wachtwoord',
      placeholder: 'Voer je wachtwoord in',
      isRequired: true,
      order: 4
    },
    confirm_password: {
      label: 'Bevestig wachtwoord',
      placeholder: 'Bevestig je wachtwoord',
      isRequired: true,
      order: 5
    }
  }
};

function NavigationHeader({ signOut, user }: AppProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const isHome = location.pathname === '/';

  return (
    <Flex 
      as="header" 
      bg="black" 
      color="orange.400" 
      p={4} 
      shadow="md" 
      borderBottom="1px" 
      borderColor="orange.400"
      direction={{ base: 'column', md: 'row' }}
      gap={{ base: 3, md: 0 }}
    >
      <Heading size={{ base: 'md', md: 'lg' }}>H-DCN Portal</Heading>
      <Spacer />
      <Flex 
        direction={{ base: 'column', sm: 'row' }}
        gap={{ base: 2, sm: 4 }}
        align={{ base: 'stretch', sm: 'center' }}
        w={{ base: 'full', md: 'auto' }}
      >
        {!isHome && (
          <Button
            leftIcon={<ArrowBackIcon />}
            onClick={() => navigate('/')}
            variant="ghost"
            colorScheme="orange"
            size={{ base: 'sm', md: 'sm' }}
            w={{ base: 'full', sm: 'auto' }}
          >
            Dashboard
          </Button>
        )}
        <Button
          leftIcon={<SettingsIcon />}
          onClick={() => navigate('/profile')}
          variant="ghost"
          colorScheme="orange"
          size={{ base: 'sm', md: 'sm' }}
          w={{ base: 'full', sm: 'auto' }}
        >
          Profiel
        </Button>
        <Text 
          fontSize={{ base: 'xs', md: 'sm' }}
          textAlign={{ base: 'center', sm: 'left' }}
          py={{ base: 1, sm: 0 }}
        >
          Welkom, {user?.attributes?.given_name || 'Gebruiker'}
        </Text>
        <Button 
          onClick={signOut} 
          colorScheme="orange" 
          size={{ base: 'sm', md: 'sm' }}
          w={{ base: 'full', sm: 'auto' }}
        >
          Uitloggen
        </Button>
      </Flex>
    </Flex>
  );
}

function AppContent({ signOut, user }: AppProps) {
  return (
    <Box minH="100vh" bg="black">
      <NavigationHeader signOut={signOut} user={user} />
      <Box as="main" p={{ base: 4, md: 6 }} bg="black">
        <Suspense fallback={
          <Center h="200px">
            <Spinner size="xl" color="orange.400" />
          </Center>
        }>
          <Routes>
            <Route path="/" element={<Dashboard user={user} />} />
            <Route path="/profile" element={<ProfileManager user={user} />} />
            <Route path="/membership" element={<MembershipForm user={user} />} />
            <Route path="/parameters" element={<ParameterManagement user={user} />} />
            <Route path="/webshop" element={<WebshopPage user={user} />} />
            <Route path="/products" element={<ProductManagementPage user={user} />} />
            <Route path="/members" element={<MemberAdminPage user={user} />} />
            <Route path="/events" element={<EventAdminPage user={user} />} />
            <Route path="/memberships" element={<MembershipManagement user={user} />} />
          </Routes>
        </Suspense>
      </Box>
    </Box>
  );
}

const components = {
  Header() {
    return (
      <Box textAlign="center" py={6}>
        <Image 
          src="/hdcn-logo.svg" 
          alt="H-DCN Logo" 
          mx="auto" 
          mb={4}
          maxW="200px"
        />
        <Heading color="orange.400" size="lg">H-DCN Portal</Heading>
        <Text color="gray.400" mt={2}>Welkom bij het H-DCN Dashboard</Text>
      </Box>
    );
  }
};

function App() {
  return (
    <Authenticator
      signUpAttributes={['given_name', 'family_name']}
      formFields={signUpFields}
      components={components}
    >
      {({ signOut, user }) => (
        <GroupAccessGuard user={user} signOut={signOut}>
          <Router>
            <AppContent signOut={signOut} user={user} />
          </Router>
        </GroupAccessGuard>
      )}
    </Authenticator>
  );
}

export default App;
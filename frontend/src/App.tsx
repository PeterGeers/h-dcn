import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Box, Flex, Heading, Button, Text, Spacer, HStack, Image } from '@chakra-ui/react';
import { ArrowBackIcon } from '@chakra-ui/icons';
import { Suspense, lazy } from 'react';
import { Spinner, Center } from '@chakra-ui/react';
import GroupAccessGuard from './components/common/GroupAccessGuard';
import { CustomAuthenticator } from './components/auth/CustomAuthenticator';
import { UserAccountPopup } from './components/common/UserAccountPopup';
import OAuthCallback from './components/auth/OAuthCallback';

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

interface AppProps {
  signOut: () => void;
  user: User;
}

// Lazy load components
const Dashboard = lazy(() => import('./pages/Dashboard')) as any;
const MembershipForm = lazy(() => import('./pages/MembershipForm')) as any;
const ParameterManagement = lazy(() => import('./pages/ParameterManagement')) as any;
const WebshopPage = lazy(() => import('./modules/webshop/WebshopPage')) as any;
const ProductManagementPage = lazy(() => import('./modules/products/ProductManagementPage')) as any;
const MemberAdminPage = lazy(() => import('./modules/members/MemberAdminPage')) as any;
const EventAdminPage = lazy(() => import('./modules/events/EventAdminPage')) as any;
const MembershipManagement = lazy(() => import('./pages/MembershipManagement')) as any;
const PasskeyTest = lazy(() => import('./components/auth/PasskeyTest')) as any;
const BrowserCompatibilityTest = lazy(() => import('./components/auth/BrowserCompatibilityTest')) as any;

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
        
        {/* User Account Popup - Shows email address and role information */}
        <UserAccountPopup user={user} signOut={signOut} />
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
            <Route path="/membership" element={<MembershipForm user={user} />} />
            <Route path="/parameters" element={<ParameterManagement user={user} />} />
            <Route path="/webshop" element={<WebshopPage user={user} />} />
            <Route path="/products" element={<ProductManagementPage user={user} />} />
            <Route path="/members" element={<MemberAdminPage user={user} />} />
            <Route path="/events" element={<EventAdminPage user={user} />} />
            <Route path="/memberships" element={<MembershipManagement user={user} />} />
            <Route path="/test/passkey" element={<PasskeyTest />} />
            <Route path="/test/browser-compatibility" element={<BrowserCompatibilityTest />} />
          </Routes>
        </Suspense>
      </Box>
    </Box>
  );
}

function App() {
  return (
    <CustomAuthenticator>
      {({ signOut, user }) => (
        <GroupAccessGuard user={user} signOut={signOut}>
          <Router>
            <AppContent signOut={signOut} user={user} />
          </Router>
        </GroupAccessGuard>
      )}
    </CustomAuthenticator>
  );
}

export default App;
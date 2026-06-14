import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Box, Flex, Heading, Button, Text, Spacer } from '@chakra-ui/react';
import { ArrowBackIcon } from '@chakra-ui/icons';
import { Suspense, lazy } from 'react';
import { Spinner, Center } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import GroupAccessGuard from './components/common/GroupAccessGuard';
import { FunctionGuard } from './components/common/FunctionGuard';
import { CustomAuthenticator } from './components/auth/CustomAuthenticator';
import { UserAccountPopup } from './components/common/UserAccountPopup';
import { LanguageSelector } from './components/common/LanguageSelector';
import { useIsAdminRoute, useAdminLocaleOverride } from './hooks/useAdminLocale';
import { AuthProvider, useAuth } from './context/AuthProvider';
import MaintenanceProvider from './components/MaintenanceProvider';

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
const WebshopPage = lazy(() => import('./modules/webshop/WebshopPage')) as any;
const ProductManagementPage = lazy(() => import('./modules/products/ProductManagementPage')) as any;
const AdvancedExportsPage = lazy(() => import('./modules/advanced-exports/AdvancedExportsPage')) as any;
const MyAccount = lazy(() => import('./pages/MyAccount')) as any;
const MemberAdminPage = lazy(() => import('./modules/members/MemberAdminPage')) as any;
const EventAdminPage = lazy(() => import('./modules/events/EventAdminPage')) as any;
const MembershipManagement = lazy(() => import('./pages/MembershipManagement')) as any;
const PasskeyTest = lazy(() => import('./components/auth/PasskeyTest')) as any;
const BrowserCompatibilityTest = lazy(() => import('./components/auth/BrowserCompatibilityTest')) as any;
const NewMemberApplication = lazy(() => import('./pages/NewMemberApplication')) as any;
const ApplicationSubmitted = lazy(() => import('./pages/ApplicationSubmitted')) as any;
const PresMeetPage = lazy(() => import('./modules/presmeet/PresMeetPage')) as any;
const EventBookingPage = lazy(() => import('./modules/presmeet/EventBookingPage')) as any;
const WebshopManagementPage = lazy(() => import('./modules/webshop-management/WebshopManagementPage')) as any;

/**
 * Route guard for /webshop_management.
 * Uses FunctionGuard with Products_* roles. Shows 403 if user lacks access.
 * Renders independently of PresMeet onboarding flow (no club_id or OnboardingFlow).
 *
 * Validates: Requirements 1.5, 1.6, 1.7, 7.1, 7.9, 8.1, 8.2
 */
function WebshopManagementGuard() {
  const { user } = useAuth();

  const functionGuardUser = React.useMemo(() => {
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

  return (
    <FunctionGuard
      user={functionGuardUser}
      requiredRoles={['Products_CRUD', 'Products_Read', 'Products_Export']}
      fallback={
        <Box p={8} textAlign="center">
          <Heading size="lg" color="red.400" mb={4}>403 — Geen toegang</Heading>
          <Text color="gray.300">
            Je hebt niet de vereiste rechten om Webshop Beheer te openen.
          </Text>
        </Box>
      }
    >
      <WebshopManagementPage />
    </FunctionGuard>
  );
}

function NavigationHeader({ signOut, user }: AppProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const isHome = location.pathname === '/';
  const { t } = useTranslation('common');
  const isAdminRoute = useIsAdminRoute();

  // Apply admin locale override (switches to Dutch on admin routes, restores on member routes)
  useAdminLocaleOverride();

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
      <Heading size={{ base: 'md', md: 'lg' }}>{t('nav.portal_title')}</Heading>
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
            {t('nav.dashboard')}
          </Button>
        )}

        {/* Language selector - hidden on admin routes per Requirement 9.5 */}
        {!isAdminRoute && <LanguageSelector />}
        
        {/* User Account Popup - Shows email address and role information */}
        <UserAccountPopup user={user} signOut={signOut} />
      </Flex>
    </Flex>
  );
}

function AppContent({ signOut, user }: AppProps) {
  // Removed password manager blocking since we don't use passwords

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
            <Route path="/" element={<Dashboard />} />
            <Route path="/membership" element={<MembershipForm user={user} />} />
            <Route path="/my-account" element={<MyAccount user={user} />} />
            <Route path="/new-member-application" element={<NewMemberApplication user={user} />} />
            <Route path="/application-submitted" element={<ApplicationSubmitted />} />
            <Route path="/webshop" element={<WebshopPage user={user} />} />
            <Route path="/products" element={<ProductManagementPage user={user} />} />
            <Route path="/advanced-exports" element={<AdvancedExportsPage user={user} />} />
            <Route path="/members" element={<MemberAdminPage user={user} />} />
            <Route path="/events" element={<EventAdminPage user={user} />} />
            <Route path="/memberships" element={<MembershipManagement user={user} />} />
            <Route path="/presmeet" element={<PresMeetPage />} />
            <Route path="/events/:eventId/booking" element={<EventBookingPage />} />
            <Route path="/webshop_management" element={<WebshopManagementGuard />} />
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
    <MaintenanceProvider>
      <AuthProvider>
        <CustomAuthenticator>
          {({ signOut, user }) => (
            <Router basename="/">
              <Routes>
                {/* Test route to verify routing works */}
                <Route path="/test-route" element={
                  <div style={{ padding: '20px', backgroundColor: 'white', color: 'black' }}>
                    <h1>Test Route Works!</h1>
                    <p>Current URL: {window.location.href}</p>
                    <p>Hash: {window.location.hash}</p>
                  </div>
                } />
                
                {/* All other routes require group access guard */}
                <Route path="/*" element={
                  <GroupAccessGuard>
                    <AppContent signOut={signOut} user={user} />
                  </GroupAccessGuard>
                } />
              </Routes>
            </Router>
          )}
        </CustomAuthenticator>
      </AuthProvider>
    </MaintenanceProvider>
  );
}

export default App;
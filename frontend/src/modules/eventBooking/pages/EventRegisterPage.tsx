/**
 * EventRegisterPage — Multi-step registration flow for closed community events.
 *
 * State machine: PasswordGate → Auth → RegistrySelector → ClaimAction → Success redirect
 *
 * - Handles returning users: if authenticated and event_id in allowed_events → redirect to booking
 * - Session token is passed from PasswordGate through all subsequent steps
 * - All strings via useTranslation('eventBooking')
 *
 * Route: /events/:slug/register
 *
 * Requirements: 1.3, 4.6, 17.1
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Button,
  FormControl,
  FormLabel,
  Input,
  Alert,
  AlertIcon,
  Spinner,
  Center,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react';
import { API_CONFIG } from '../../../config/api';
import { useAuth } from '../../../context/AuthProvider';
import PasswordGate, { RegistryConfig, VerifyPasswordResult } from '../components/PasswordGate';
import RegistrySelector from '../components/RegistrySelector';
import ClaimAction from '../components/ClaimAction';

// --- Types ---

type RegistrationStep =
  | 'password_gate'
  | 'auth'
  | 'registry_select'
  | 'claiming'
  | 'success';

interface PublicEventData {
  event_id: string;
  name: string;
  event_type: string;
  start_date: string;
  end_date: string;
  location: string;
  registration_status: string;
  has_event_password?: boolean;
  landing_page_enabled?: boolean;
}

interface RegistrationState {
  step: RegistrationStep;
  eventId: string;
  sessionToken: string | null;
  registryConfig: RegistryConfig | null;
  selectedRow: { rowId: string; label: string } | null;
  error: string | null;
}

// --- Component ---

const EventRegisterPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { t: tEvent } = useTranslation('eventBooking');
  const { t: tAuth } = useTranslation('auth');
  const { i18n } = useTranslation();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();

  // Event data state
  const [event, setEvent] = useState<PublicEventData | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Registration state machine
  const [regState, setRegState] = useState<RegistrationState>({
    step: 'password_gate',
    eventId: '',
    sessionToken: null,
    registryConfig: null,
    selectedRow: null,
    error: null,
  });

  // Auth form state (for the auth step)
  const [signUpForm, setSignUpForm] = useState({
    email: '',
    given_name: '',
    family_name: '',
  });
  const [signUpLoading, setSignUpLoading] = useState(false);
  const [signUpError, setSignUpError] = useState('');
  const [signUpSuccess, setSignUpSuccess] = useState('');
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [signInEmail, setSignInEmail] = useState('');
  const [signInLoading, setSignInLoading] = useState(false);
  const [signInError, setSignInError] = useState('');

  // Derived: whether this event has a password gate
  const hasEventPassword = event?.has_event_password ?? true;
  const landingPageEnabled = event?.landing_page_enabled ?? true;

  // --- Fetch event public data ---
  useEffect(() => {
    if (!slug) return;

    const fetchEvent = async () => {
      try {
        setLoading(true);
        setFetchError(null);
        const baseUrl = API_CONFIG.BASE_URL;
        const response = await fetch(`${baseUrl}/events/public/${slug}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data: PublicEventData = await response.json();
        setEvent(data);
        setRegState((prev) => ({ ...prev, eventId: data.event_id }));
      } catch (err) {
        console.error('Failed to fetch event:', err);
        setFetchError(tEvent('page.error_loading'));
      } finally {
        setLoading(false);
      }
    };

    fetchEvent();
  }, [slug, tEvent]);

  // --- Handle returning users ---
  // Requirement 4.6: If user is already authenticated and has event access, skip to booking
  useEffect(() => {
    if (authLoading || !isAuthenticated || !event) return;

    const checkEventAccess = async () => {
      try {
        const { fetchAuthSession } = await import('aws-amplify/auth');
        const session = await fetchAuthSession();
        const accessToken = session.tokens?.accessToken?.toString();
        if (!accessToken) return;

        // Check if user already has access to this event via /members/me
        const baseUrl = API_CONFIG.BASE_URL;
        const meResponse = await fetch(`${baseUrl}/members/me`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });

        if (meResponse.ok) {
          const memberData = await meResponse.json();
          const allowedEvents: string[] = memberData?.allowed_events || [];
          if (allowedEvents.includes(event.event_id)) {
            // Returning user with event access — skip landing flow entirely
            navigate(`/events/${event.event_id}/booking`, { replace: true });
            return;
          }
        }
      } catch (err) {
        // If member check fails, continue with normal registration flow
        console.warn('Could not check event access for returning user:', err);
      }
    };

    checkEventAccess();
  }, [authLoading, isAuthenticated, event, navigate]);

  // --- Step machine transitions ---

  /** Called when PasswordGate succeeds — move to auth step */
  const handlePasswordSuccess = useCallback((result: VerifyPasswordResult) => {
    setRegState((prev) => ({
      ...prev,
      step: 'auth',
      sessionToken: result.session_token || null,
      registryConfig: result.registry_config || null,
    }));
  }, []);

  /** Called when PasswordGate should be skipped (no password or landing disabled) */
  const handlePasswordSkip = useCallback(() => {
    // Skip directly to auth step — no session token needed if no password gate
    setRegState((prev) => ({
      ...prev,
      step: 'auth',
    }));
  }, []);

  /** Called when auth is complete (user is authenticated) — move to registry_select */
  const handleAuthComplete = useCallback(() => {
    setRegState((prev) => ({
      ...prev,
      step: 'registry_select',
    }));
  }, []);

  /** Called when a registry row is selected — move to claiming step */
  const handleRowSelected = useCallback((rowId: string, rowLabel: string) => {
    setRegState((prev) => ({
      ...prev,
      step: 'claiming',
      selectedRow: { rowId, label: rowLabel },
    }));
  }, []);

  /** Called when claim succeeds — redirect to booking */
  const handleClaimSuccess = useCallback(
    (memberId: string) => {
      setRegState((prev) => ({ ...prev, step: 'success' }));
      if (event) {
        navigate(`/events/${event.event_id}/booking`, { replace: true });
      }
    },
    [event, navigate]
  );

  // --- When user becomes authenticated during auth step, advance to registry_select ---
  useEffect(() => {
    if (regState.step === 'auth' && !authLoading && isAuthenticated) {
      handleAuthComplete();
    }
  }, [regState.step, authLoading, isAuthenticated, handleAuthComplete]);

  // --- Sign-up handler ---
  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!event) return;

    setSignUpLoading(true);
    setSignUpError('');
    setSignUpSuccess('');

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: signUpForm.email,
          given_name: signUpForm.given_name,
          family_name: signUpForm.family_name,
          locale: i18n.language,
          event_id: event.event_id,
          source: 'event_landing',
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setSignUpSuccess(tAuth('signup.success'));
        setSignInEmail(signUpForm.email);
        setActiveTabIndex(1);
        setTimeout(() => {
          initiateSignIn(signUpForm.email);
        }, 500);
      } else {
        let errorMessage = data.error || tAuth('signup.generic_error');
        if (response.status === 409) {
          errorMessage = tAuth('signup.existing_account');
          setSignInEmail(signUpForm.email);
          setActiveTabIndex(1);
        }
        setSignUpError(errorMessage);
      }
    } catch (err: any) {
      console.error('Sign up error:', err);
      setSignUpError(tAuth('signup.network_error'));
    } finally {
      setSignUpLoading(false);
    }
  };

  // --- Sign-in logic ---
  const initiateSignIn = async (email: string) => {
    setSignInLoading(true);
    setSignInError('');

    try {
      const { signIn } = await import('aws-amplify/auth');
      await signIn({
        username: email,
        options: {
          authFlowType: 'USER_AUTH',
          preferredChallenge: 'EMAIL_OTP',
          clientMetadata: { locale: i18n.language },
        },
      });
      // Auth state change will be detected by useAuth hook → useEffect advances step
    } catch (err: any) {
      console.error('Sign in error:', err);
      if (err.name === 'UserNotFoundException' || err.message?.includes('not found')) {
        setSignInError(tAuth('errors.credentials_invalid'));
      } else {
        setSignInError(tAuth('errors.login_failed'));
      }
    } finally {
      setSignInLoading(false);
    }
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    await initiateSignIn(signInEmail);
  };

  const handleSignUpInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSignUpForm((prev) => ({ ...prev, [name]: value }));
  };

  // --- Render helpers ---

  /** Render the auth step (sign-up / sign-in tabs) */
  const renderAuthStep = () => (
    <Box
      bg="gray.900"
      borderRadius="lg"
      p={{ base: 4, md: 6 }}
      border="1px solid"
      borderColor="gray.700"
    >
      <Tabs colorScheme="orange" variant="enclosed" index={activeTabIndex} onChange={setActiveTabIndex}>
        <TabList borderBottomColor="gray.700">
          <Tab
            color="gray.400"
            _selected={{ color: 'orange.400', borderColor: 'gray.700', borderBottomColor: 'gray.900' }}
          >
            {tAuth('signup.title')}
          </Tab>
          <Tab
            color="gray.400"
            _selected={{ color: 'orange.400', borderColor: 'gray.700', borderBottomColor: 'gray.900' }}
          >
            {tAuth('login.title')}
          </Tab>
        </TabList>

        <TabPanels>
          {/* Sign Up Panel */}
          <TabPanel px={0} pt={6}>
            <VStack spacing={4} align="stretch">
              <Text color="gray.400" fontSize="sm">
                {tAuth('signup.description')}
              </Text>
              <Text color="orange.300" fontSize="xs">
                {tAuth('signup.passkey_hint')}
              </Text>

              {signUpError && (
                <Alert status="error" bg="red.900" borderColor="red.500" border="1px solid" borderRadius="md">
                  <AlertIcon color="red.300" />
                  <Text color="red.100" fontSize="sm">{signUpError}</Text>
                </Alert>
              )}

              {signUpSuccess && (
                <Alert status="success" bg="green.900" borderColor="green.500" border="1px solid" borderRadius="md">
                  <AlertIcon color="green.300" />
                  <Text color="green.100" fontSize="sm">{signUpSuccess}</Text>
                </Alert>
              )}

              <form onSubmit={handleSignUp}>
                <VStack spacing={4}>
                  <FormControl isRequired>
                    <FormLabel color="gray.300" fontSize="sm">{tAuth('signup.email_label')}</FormLabel>
                    <Input
                      type="email"
                      name="email"
                      value={signUpForm.email}
                      onChange={handleSignUpInputChange}
                      placeholder={tAuth('login.email_placeholder')}
                      bg="gray.700"
                      border="1px solid"
                      borderColor="gray.600"
                      color="white"
                      _placeholder={{ color: 'gray.400' }}
                      _focus={{ borderColor: 'orange.400' }}
                    />
                  </FormControl>

                  <FormControl isRequired>
                    <FormLabel color="gray.300" fontSize="sm">{tAuth('signup.first_name_label')}</FormLabel>
                    <Input
                      type="text"
                      name="given_name"
                      value={signUpForm.given_name}
                      onChange={handleSignUpInputChange}
                      placeholder={tAuth('signup.first_name_placeholder')}
                      bg="gray.700"
                      border="1px solid"
                      borderColor="gray.600"
                      color="white"
                      _placeholder={{ color: 'gray.400' }}
                      _focus={{ borderColor: 'orange.400' }}
                    />
                  </FormControl>

                  <FormControl isRequired>
                    <FormLabel color="gray.300" fontSize="sm">{tAuth('signup.last_name_label')}</FormLabel>
                    <Input
                      type="text"
                      name="family_name"
                      value={signUpForm.family_name}
                      onChange={handleSignUpInputChange}
                      placeholder={tAuth('signup.last_name_placeholder')}
                      bg="gray.700"
                      border="1px solid"
                      borderColor="gray.600"
                      color="white"
                      _placeholder={{ color: 'gray.400' }}
                      _focus={{ borderColor: 'orange.400' }}
                    />
                  </FormControl>

                  <Button
                    type="submit"
                    colorScheme="orange"
                    size="lg"
                    width="full"
                    isLoading={signUpLoading}
                    loadingText={tAuth('signup.loading')}
                  >
                    {tAuth('signup.submit_button')}
                  </Button>
                </VStack>
              </form>
            </VStack>
          </TabPanel>

          {/* Sign In Panel */}
          <TabPanel px={0} pt={6}>
            <VStack spacing={4} align="stretch">
              <Text color="gray.400" fontSize="sm">
                {tEvent('landing.welcomeBack')}
              </Text>

              {signInError && (
                <Alert status="error" bg="red.900" borderColor="red.500" border="1px solid" borderRadius="md">
                  <AlertIcon color="red.300" />
                  <Text color="red.100" fontSize="sm">{signInError}</Text>
                </Alert>
              )}

              <form onSubmit={handleSignIn}>
                <VStack spacing={4}>
                  <FormControl isRequired>
                    <FormLabel color="gray.300" fontSize="sm">{tAuth('signup.email_label')}</FormLabel>
                    <Input
                      type="email"
                      value={signInEmail}
                      onChange={(e) => setSignInEmail(e.target.value)}
                      placeholder={tAuth('login.email_placeholder')}
                      bg="gray.700"
                      border="1px solid"
                      borderColor="gray.600"
                      color="white"
                      _placeholder={{ color: 'gray.400' }}
                      _focus={{ borderColor: 'orange.400' }}
                    />
                  </FormControl>

                  <Button
                    type="submit"
                    colorScheme="orange"
                    size="lg"
                    width="full"
                    isLoading={signInLoading}
                    loadingText={tAuth('login.loading')}
                  >
                    {tAuth('login.passkey_button')}
                  </Button>
                </VStack>
              </form>
            </VStack>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );

  // --- Current step content ---

  const renderCurrentStep = () => {
    if (!event) return null;

    switch (regState.step) {
      case 'password_gate':
        return (
          <PasswordGate
            eventId={event.event_id}
            landingPageEnabled={landingPageEnabled}
            hasEventPassword={hasEventPassword}
            onSuccess={handlePasswordSuccess}
            onSkip={handlePasswordSkip}
          />
        );

      case 'auth':
        // If user is already authenticated, this step auto-advances via useEffect
        if (isAuthenticated) {
          return (
            <Center py={8}>
              <Spinner size="lg" color="orange.400" />
            </Center>
          );
        }
        return (
          <VStack spacing={8} align="stretch">
            <VStack spacing={2} align="center" textAlign="center">
              <Heading as="h1" size="lg" color="orange.400">
                {event.name}
              </Heading>
              <HStack spacing={2} color="gray.400" fontSize="sm">
                <Text>{event.location}</Text>
              </HStack>
              <Text color="gray.300" fontSize="md" mt={2}>
                {tEvent('landing.loginToRegister')}
              </Text>
            </VStack>
            {renderAuthStep()}
          </VStack>
        );

      case 'registry_select':
        return (
          <RegistrySelector
            eventId={event.event_id}
            sessionToken={regState.sessionToken || ''}
            rowLabel={regState.registryConfig?.row_label}
            claimMode={regState.registryConfig?.claim_mode}
            userEmail={user?.email || undefined}
            onSelectRow={handleRowSelected}
          />
        );

      case 'claiming':
        if (!regState.selectedRow) return null;
        return (
          <ClaimAction
            eventId={event.event_id}
            sessionToken={regState.sessionToken || ''}
            selectedRowId={regState.selectedRow.rowId}
            rowLabel={regState.selectedRow.label}
            isAuthenticated={isAuthenticated}
            userName={[user?.givenName, user?.familyName].filter(Boolean).join(' ')}
            userEmail={user?.email || ''}
            onSuccess={handleClaimSuccess}
          />
        );

      case 'success':
        return (
          <Center py={8}>
            <Spinner size="lg" color="orange.400" />
          </Center>
        );

      default:
        return null;
    }
  };

  // --- Render ---

  if (loading || authLoading) {
    return (
      <Center minH="100vh" bg="black">
        <Spinner size="xl" color="orange.400" />
      </Center>
    );
  }

  if (fetchError || !event) {
    return (
      <Box minH="100vh" bg="black" p={8}>
        <Container maxW="container.md">
          <Alert status="error" bg="red.900" color="white" borderRadius="md">
            <AlertIcon />
            {fetchError || tEvent('page.error_loading')}
          </Alert>
        </Container>
      </Box>
    );
  }

  return (
    <Box minH="100vh" bg="black" color="white" py={{ base: 8, md: 16 }}>
      <Container maxW="container.sm">
        {renderCurrentStep()}
      </Container>
    </Box>
  );
};

export default EventRegisterPage;

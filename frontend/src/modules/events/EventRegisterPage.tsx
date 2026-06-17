import React, { useState, useEffect } from 'react';
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
import { API_CONFIG } from '../../config/api';
import { useAuth } from '../../context/AuthProvider';

// --- Types ---

interface PublicEventData {
  event_id: string;
  name: string;
  event_type: string;
  start_date: string;
  end_date: string;
  location: string;
  registration_status: string;
}

// --- Component ---

const EventRegisterPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { t: tEvent } = useTranslation('eventBooking');
  const { t: tAuth } = useTranslation('auth');
  const { i18n } = useTranslation();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  // Event data state
  const [event, setEvent] = useState<PublicEventData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Sign-up form state
  const [signUpForm, setSignUpForm] = useState({
    email: '',
    given_name: '',
    family_name: '',
  });
  const [signUpLoading, setSignUpLoading] = useState(false);
  const [signUpError, setSignUpError] = useState('');
  const [signUpSuccess, setSignUpSuccess] = useState('');

  // Tab control state
  const [activeTabIndex, setActiveTabIndex] = useState(0);

  // Sign-in form state
  const [signInEmail, setSignInEmail] = useState('');
  const [signInLoading, setSignInLoading] = useState(false);
  const [signInError, setSignInError] = useState('');

  // Redirect authenticated users to booking form
  useEffect(() => {
    if (!authLoading && isAuthenticated && event) {
      navigate(`/events/${event.event_id}/booking`, { replace: true });
    }
  }, [authLoading, isAuthenticated, event, navigate]);

  // Fetch event public data
  useEffect(() => {
    if (!slug) return;

    const fetchEvent = async () => {
      try {
        setLoading(true);
        setError(null);
        const baseUrl = API_CONFIG.BASE_URL;
        const response = await fetch(`${baseUrl}/events/public/${slug}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data: PublicEventData = await response.json();
        setEvent(data);
      } catch (err) {
        console.error('Failed to fetch event:', err);
        setError(tEvent('page.error_loading'));
      } finally {
        setLoading(false);
      }
    };

    fetchEvent();
  }, [slug, tEvent]);

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
        // Auto-switch to sign-in tab and trigger sign-in for the user's email
        setSignInEmail(signUpForm.email);
        setActiveTabIndex(1);
        // Auto-initiate sign-in after a brief delay to allow the user to see the success message
        setTimeout(() => {
          initiateSignIn(signUpForm.email);
        }, 500);
      } else {
        let errorMessage = data.error || tAuth('signup.generic_error');
        if (response.status === 409) {
          errorMessage = tAuth('signup.existing_account');
          // Auto-switch to sign-in tab and pre-fill email for convenience
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

  // --- Sign-in logic (reusable) ---
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
      // After successful signIn initiation, the Amplify auth flow handles the rest.
      // The useAuth hook will detect the session change and isAuthenticated will become true,
      // triggering the redirect in the useEffect above.
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

  // --- Sign-in handler ---
  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    await initiateSignIn(signInEmail);
  };

  const handleSignUpInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSignUpForm(prev => ({ ...prev, [name]: value }));
  };

  // --- Render ---

  if (loading || authLoading) {
    return (
      <Center minH="100vh" bg="black">
        <Spinner size="xl" color="orange.400" />
      </Center>
    );
  }

  if (error || !event) {
    return (
      <Box minH="100vh" bg="black" p={8}>
        <Container maxW="container.md">
          <Alert status="error" bg="red.900" color="white" borderRadius="md">
            <AlertIcon />
            {error || tEvent('page.error_loading')}
          </Alert>
        </Container>
      </Box>
    );
  }

  return (
    <Box minH="100vh" bg="black" color="white" py={{ base: 8, md: 16 }}>
      <Container maxW="container.sm">
        <VStack spacing={8} align="stretch">
          {/* Event info header */}
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

          {/* Auth tabs */}
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
        </VStack>
      </Container>
    </Box>
  );
};

export default EventRegisterPage;

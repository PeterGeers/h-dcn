import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  Text,
  Alert,
  AlertIcon,
  Heading,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Image
} from '@chakra-ui/react';
import { getCurrentUser, signIn, signOut } from 'aws-amplify/auth';
import { PasswordlessSignUp } from './PasswordlessSignUp';
import { PasskeySetup } from './PasskeySetup';
import { CrossDeviceAuth } from './CrossDeviceAuth';
import { EmailRecovery } from './EmailRecovery';
import { WebAuthnService } from '../../services/webAuthnService';

interface CustomAuthenticatorProps {
  children: (props: { signOut: () => void; user: any }) => React.ReactNode;
}

export function CustomAuthenticator({ children }: CustomAuthenticatorProps) {
  const [user, setUser] = useState<any>(null);
  const [authState, setAuthState] = useState<'loading' | 'signIn' | 'signUp' | 'passkeySetup' | 'crossDevice' | 'emailRecovery' | 'authenticated'>('loading');
  const [signInData, setSignInData] = useState({ email: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [newUserEmail, setNewUserEmail] = useState('');

  useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setAuthState('authenticated');
    } catch (err) {
      setAuthState('signIn');
    }
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Check if WebAuthn is supported and user has passkey
      if (WebAuthnService.isSupported()) {
        try {
          // Try passkey authentication first
          const authOptions = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/passkey/authenticate/begin`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: signInData.email,
            }),
          });

          if (authOptions.ok) {
            const options = await authOptions.json();
            
            // Attempt passkey authentication
            const credential = await WebAuthnService.authenticateWithPasskey(options);
            const credentialJSON = WebAuthnService.credentialToJSON(credential);

            // Complete authentication with backend
            const authResult = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/passkey/authenticate/complete`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                email: signInData.email,
                credential: credentialJSON,
              }),
            });

            if (authResult.ok) {
              // Passkey authentication successful
              // Now authenticate with Cognito using the verified email
              try {
                const cognitoUser = await signIn({ username: signInData.email });
                setUser(cognitoUser);
                setAuthState('authenticated');
                return;
              } catch (cognitoError) {
                console.log('Cognito authentication after passkey failed:', cognitoError);
                // Fall through to email recovery
              }
            }
          }
        } catch (passkeyError) {
          console.log('Passkey authentication failed, falling back to email recovery:', passkeyError);
          // Fall through to email recovery
        }
      }

      // Fallback to email-based recovery or cross-device authentication
      if (WebAuthnService.shouldOfferCrossDeviceAuth()) {
        setError(
          'Passkey authenticatie niet beschikbaar op dit apparaat. ' +
          'Probeer cross-device authenticatie of gebruik account recovery.'
        );
      } else {
        setError(
          'Passkey authenticatie niet beschikbaar. ' +
          'Gebruik account recovery of neem contact op met de beheerder.'
        );
      }

    } catch (err: any) {
      console.error('Sign in error:', err);
      setError('Inloggen mislukt. Probeer opnieuw of neem contact op met de beheerder.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = async () => {
    try {
      await signOut();
      setUser(null);
      setAuthState('signIn');
    } catch (err) {
      console.error('Sign out error:', err);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSignInData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSignUpSuccess = (email: string) => {
    setNewUserEmail(email);
    setAuthState('passkeySetup');
  };

  const handlePasskeySetupSuccess = () => {
    // After passkey setup, check auth state again
    checkAuthState();
  };

  const handleCrossDeviceAuth = () => {
    setAuthState('crossDevice');
  };

  const handleCrossDeviceSuccess = (result: any) => {
    // Cross-device authentication successful, check auth state
    checkAuthState();
  };

  const handlePasskeySetupSkip = () => {
    // User skipped passkey setup, proceed to authentication
    checkAuthState();
  };

  const handleEmailRecovery = () => {
    setAuthState('emailRecovery');
  };

  const handleEmailRecoverySuccess = () => {
    // After successful recovery, check auth state
    checkAuthState();
  };

  const handleEmailRecoveryCancel = () => {
    setAuthState('signIn');
    setError('');
  };

  if (authState === 'loading') {
    return (
      <Box minH="100vh" bg="black" display="flex" alignItems="center" justifyContent="center">
        <Text color="orange.400">Laden...</Text>
      </Box>
    );
  }

  if (authState === 'authenticated' && user) {
    return <>{children({ signOut: handleSignOut, user })}</>;
  }

  if (authState === 'passkeySetup') {
    return (
      <Box minH="100vh" bg="black" display="flex" alignItems="center" justifyContent="center">
        <PasskeySetup
          userEmail={newUserEmail}
          onSuccess={handlePasskeySetupSuccess}
          onSkip={handlePasskeySetupSkip}
          onError={(error) => {
            console.error('Passkey setup error:', error);
            setError(error);
            setAuthState('signIn');
          }}
        />
      </Box>
    );
  }

  if (authState === 'emailRecovery') {
    return (
      <Box minH="100vh" bg="black" display="flex" alignItems="center" justifyContent="center">
        <EmailRecovery
          onSuccess={handleEmailRecoverySuccess}
          onCancel={handleEmailRecoveryCancel}
          onError={(error) => {
            console.error('Email recovery error:', error);
            setError(error);
          }}
        />
      </Box>
    );
  }

  return (
    <Box minH="100vh" bg="black" display="flex" alignItems="center" justifyContent="center">
      <Box maxW="md" w="full" p={6}>
        <Box textAlign="center" mb={8}>
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

        <Tabs variant="enclosed" colorScheme="orange">
          <TabList>
            <Tab color="gray.400" _selected={{ color: 'orange.400', bg: 'gray.800' }}>
              Inloggen
            </Tab>
            <Tab color="gray.400" _selected={{ color: 'orange.400', bg: 'gray.800' }}>
              Registreren
            </Tab>
          </TabList>

          <TabPanels>
            <TabPanel>
              <VStack spacing={6}>
                <Box textAlign="center">
                  <Heading color="orange.400" size="md">Inloggen</Heading>
                  <Text color="gray.400" mt={2}>
                    Passwordless authenticatie wordt momenteel geconfigureerd.
                  </Text>
                  <Text color="orange.300" mt={2} fontSize="sm">
                    Nieuwe gebruikers kunnen zich registreren via het "Registreren" tabblad.
                    Bestaande gebruikers: neem contact op met de beheerder.
                  </Text>
                </Box>

                {error && (
                  <Alert status="error" bg="red.900" borderColor="red.500" border="1px solid">
                    <AlertIcon color="red.300" />
                    <Text color="red.100">{error}</Text>
                  </Alert>
                )}

                <form onSubmit={handleSignIn} style={{ width: '100%' }}>
                  <VStack spacing={4}>
                    <FormControl isRequired>
                      <FormLabel color="gray.300">E-mailadres</FormLabel>
                      <Input
                        type="email"
                        name="email"
                        value={signInData.email}
                        onChange={handleInputChange}
                        placeholder="Voer je e-mailadres in"
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
                      isLoading={loading}
                      loadingText="Inloggen..."
                    >
                      Inloggen
                    </Button>

                    {WebAuthnService.shouldOfferCrossDeviceAuth() && (
                      <Button
                        colorScheme="blue"
                        variant="outline"
                        size="lg"
                        width="full"
                        onClick={handleCrossDeviceAuth}
                        isDisabled={loading || !signInData.email}
                      >
                        Cross-Device Authenticatie
                      </Button>
                    )}

                    <Button
                      colorScheme="gray"
                      variant="outline"
                      size="lg"
                      width="full"
                      onClick={handleEmailRecovery}
                      isDisabled={loading}
                    >
                      Account Recovery via Email
                    </Button>
                  </VStack>
                </form>

                <Box textAlign="center">
                  <Text color="gray.400" fontSize="sm">
                    Geen account? Gebruik het "Registreren" tabblad om een account aan te maken.
                  </Text>
                </Box>
              </VStack>
            </TabPanel>

            <TabPanel>
              <PasswordlessSignUp 
                onSuccess={() => {
                  // Stay on sign up tab to show success message
                }}
                onError={(error) => {
                  console.error('Sign up error:', error);
                }}
              />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </Box>
    </Box>
  );
}
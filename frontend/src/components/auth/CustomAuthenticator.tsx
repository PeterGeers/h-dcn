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
      // Check if we have stored authentication tokens
      const storedUser = localStorage.getItem('hdcn_auth_user');
      const storedTokens = localStorage.getItem('hdcn_auth_tokens');
      
      if (storedUser && storedTokens) {
        const user = JSON.parse(storedUser);
        const tokens = JSON.parse(storedTokens);
        
        // Verify token is still valid by checking expiration
        if (tokens.AccessTokenPayload && tokens.AccessTokenPayload.exp) {
          const expirationTime = tokens.AccessTokenPayload.exp * 1000; // Convert to milliseconds
          const currentTime = Date.now();
          
          if (currentTime < expirationTime) {
            // Token is still valid
            setUser(user);
            setAuthState('authenticated');
            return;
          } else {
            // Token expired, clear storage
            localStorage.removeItem('hdcn_auth_user');
            localStorage.removeItem('hdcn_auth_tokens');
          }
        }
      }
      
      // No valid authentication found
      setAuthState('signIn');
    } catch (err) {
      console.error('Error checking auth state:', err);
      // Clear any corrupted data
      localStorage.removeItem('hdcn_auth_user');
      localStorage.removeItem('hdcn_auth_tokens');
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
              const authData = await authResult.json();
              
              // Passkey authentication successful - backend returns Cognito tokens
              if (authData.tokens && authData.tokens.AccessToken) {
                // Store tokens and create user object compatible with Amplify
                const user = {
                  username: signInData.email,
                  attributes: {
                    email: signInData.email,
                    given_name: authData.user?.given_name || '',
                    family_name: authData.user?.family_name || ''
                  },
                  signInUserSession: {
                    accessToken: {
                      jwtToken: authData.tokens.AccessToken,
                      payload: authData.tokens.AccessTokenPayload || {}
                    },
                    idToken: {
                      jwtToken: authData.tokens.IdToken,
                      payload: authData.tokens.IdTokenPayload || {}
                    },
                    refreshToken: {
                      token: authData.tokens.RefreshToken
                    }
                  }
                };
                
                // Store authentication data
                localStorage.setItem('hdcn_auth_user', JSON.stringify(user));
                localStorage.setItem('hdcn_auth_tokens', JSON.stringify(authData.tokens));
                
                setUser(user);
                setAuthState('authenticated');
                return;
              } else {
                throw new Error('Authentication successful but no tokens received');
              }
            } else {
              const errorData = await authResult.json();
              throw new Error(errorData.message || 'Passkey authentication failed');
            }
          } else {
            // User doesn't have a passkey registered, offer to set one up
            const errorData = await authOptions.json();
            if (errorData.code === 'NO_PASSKEY_REGISTERED') {
              setNewUserEmail(signInData.email);
              setAuthState('passkeySetup');
              return;
            } else {
              throw new Error(errorData.message || 'Failed to initiate passkey authentication');
            }
          }
        } catch (passkeyError: any) {
          console.log('Passkey authentication failed:', passkeyError);
          
          // Check if this is a "no passkey" error
          if (passkeyError.name === 'NotAllowedError' || passkeyError.message?.includes('no credentials')) {
            // User might not have a passkey set up, offer to create one
            setNewUserEmail(signInData.email);
            setAuthState('passkeySetup');
            return;
          }
          
          // For other errors, show the error message
          setError(passkeyError.message || 'Passkey authenticatie mislukt');
        }
      } else {
        // WebAuthn not supported
        setError('Passkey authenticatie wordt niet ondersteund door deze browser');
      }

      // If we get here, passkey auth failed - offer alternatives
      if (WebAuthnService.shouldOfferCrossDeviceAuth()) {
        setError(prev => prev + '. Probeer cross-device authenticatie of gebruik account recovery via email.');
      } else {
        setError(prev => prev + '. Gebruik account recovery via email hieronder.');
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
      // Clear stored authentication data
      localStorage.removeItem('hdcn_auth_user');
      localStorage.removeItem('hdcn_auth_tokens');
      
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
    // After successful signup, user needs to verify email and set up passkey
    setAuthState('signIn'); // Stay on sign in to show success message
  };

  const handlePasskeySetupSuccess = (authData?: any) => {
    // After passkey setup, user might be authenticated or need to sign in
    if (authData && authData.tokens && authData.tokens.AccessToken) {
      // User is authenticated after passkey setup
      const user = {
        username: authData.user?.email || newUserEmail,
        attributes: {
          email: authData.user?.email || newUserEmail,
          given_name: authData.user?.given_name || '',
          family_name: authData.user?.family_name || ''
        },
        signInUserSession: {
          accessToken: {
            jwtToken: authData.tokens.AccessToken,
            payload: authData.tokens.AccessTokenPayload || {}
          },
          idToken: {
            jwtToken: authData.tokens.IdToken,
            payload: authData.tokens.IdTokenPayload || {}
          },
          refreshToken: {
            token: authData.tokens.RefreshToken
          }
        }
      };
      
      // Store authentication data
      localStorage.setItem('hdcn_auth_user', JSON.stringify(user));
      localStorage.setItem('hdcn_auth_tokens', JSON.stringify(authData.tokens));
      
      setUser(user);
      setAuthState('authenticated');
    } else {
      // Passkey setup complete, return to sign in
      setAuthState('signIn');
      setError(''); // Clear any errors
      // Set the email for convenience
      setSignInData({ email: newUserEmail });
    }
  };

  const handleCrossDeviceAuth = () => {
    if (!signInData.email) {
      setError('Voer eerst je e-mailadres in voor cross-device authenticatie');
      return;
    }
    setAuthState('crossDevice');
    setError(''); // Clear any existing errors
  };

  const handleCrossDeviceSuccess = (authData: any) => {
    // Cross-device authentication successful, set user with tokens
    if (authData.tokens && authData.tokens.AccessToken) {
      const user = {
        username: authData.user?.email || signInData.email,
        attributes: {
          email: authData.user?.email || signInData.email,
          given_name: authData.user?.given_name || '',
          family_name: authData.user?.family_name || ''
        },
        signInUserSession: {
          accessToken: {
            jwtToken: authData.tokens.AccessToken,
            payload: authData.tokens.AccessTokenPayload || {}
          },
          idToken: {
            jwtToken: authData.tokens.IdToken,
            payload: authData.tokens.IdTokenPayload || {}
          },
          refreshToken: {
            token: authData.tokens.RefreshToken
          }
        }
      };
      
      // Store authentication data
      localStorage.setItem('hdcn_auth_user', JSON.stringify(user));
      localStorage.setItem('hdcn_auth_tokens', JSON.stringify(authData.tokens));
      
      setUser(user);
      setAuthState('authenticated');
    } else {
      setError('Authentication successful but no tokens received');
      setAuthState('signIn');
    }
    setError(''); // Clear any errors
  };

  const handlePasskeySetupSkip = () => {
    // User skipped passkey setup, proceed to authentication
    checkAuthState();
  };

  const handleEmailRecovery = () => {
    setAuthState('emailRecovery');
    setError(''); // Clear any existing errors
  };

  const handleEmailRecoverySuccess = (authData: any) => {
    // After successful recovery, set user with tokens
    if (authData.tokens && authData.tokens.AccessToken) {
      const user = {
        username: authData.user?.email || '',
        attributes: {
          email: authData.user?.email || '',
          given_name: authData.user?.given_name || '',
          family_name: authData.user?.family_name || ''
        },
        signInUserSession: {
          accessToken: {
            jwtToken: authData.tokens.AccessToken,
            payload: authData.tokens.AccessTokenPayload || {}
          },
          idToken: {
            jwtToken: authData.tokens.IdToken,
            payload: authData.tokens.IdTokenPayload || {}
          },
          refreshToken: {
            token: authData.tokens.RefreshToken
          }
        }
      };
      
      // Store authentication data
      localStorage.setItem('hdcn_auth_user', JSON.stringify(user));
      localStorage.setItem('hdcn_auth_tokens', JSON.stringify(authData.tokens));
      
      setUser(user);
      setAuthState('authenticated');
    } else {
      setError('Recovery successful but no tokens received');
    }
    setError(''); // Clear any errors
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

  if (authState === 'crossDevice') {
    return (
      <Box minH="100vh" bg="black" display="flex" alignItems="center" justifyContent="center">
        <CrossDeviceAuth
          userEmail={signInData.email}
          onSuccess={handleCrossDeviceSuccess}
          onCancel={() => {
            setAuthState('signIn');
            setError('');
          }}
          onError={(error) => {
            console.error('Cross-device auth error:', error);
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
                    Veilig inloggen met passkey authenticatie
                  </Text>
                  <Text color="orange.300" mt={2} fontSize="sm">
                    Gebruik je vingerafdruk, gezichtsherkenning, of apparaat-PIN om in te loggen
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
                      🔐 Inloggen met Passkey
                    </Button>

                    <Button
                      colorScheme="blue"
                      variant="outline"
                      size="lg"
                      width="full"
                      type="button"
                      onClick={() => {
                        if (signInData.email) {
                          setNewUserEmail(signInData.email);
                          setAuthState('passkeySetup');
                        } else {
                          setError('Voer eerst je e-mailadres in');
                        }
                      }}
                      isDisabled={loading || !signInData.email}
                    >
                      Passkey Instellen
                    </Button>

                    {WebAuthnService.shouldOfferCrossDeviceAuth() && (
                      <Button
                        colorScheme="purple"
                        variant="outline"
                        size="lg"
                        width="full"
                        type="button"
                        onClick={() => {
                          if (signInData.email) {
                            handleCrossDeviceAuth();
                          } else {
                            setError('Voer eerst je e-mailadres in');
                          }
                        }}
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
                      type="button"
                      onClick={handleEmailRecovery}
                      isDisabled={loading}
                    >
                      📧 Account Herstellen via Email
                    </Button>
                  </VStack>
                </form>

                <Box textAlign="center">
                  <Text color="gray.400" fontSize="sm">
                    Geen account? Gebruik het "Registreren" tabblad om een account aan te maken.
                  </Text>
                  <Text color="orange.300" fontSize="sm" mt={2}>
                    Problemen met inloggen? Gebruik "Account Herstellen via Email" hierboven.
                  </Text>
                </Box>
              </VStack>
            </TabPanel>

            <TabPanel>
              <PasswordlessSignUp 
                onSuccess={(email) => {
                  // Show success message and guide user to verify email
                  setNewUserEmail(email);
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
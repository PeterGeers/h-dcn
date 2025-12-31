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
  Image,
  IconButton,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverArrow,
  PopoverCloseButton,
  PopoverHeader,
  PopoverBody,
  HStack
} from '@chakra-ui/react';
import { PasswordlessSignUp } from './PasswordlessSignUp';
import { PasskeySetup } from './PasskeySetup';
import { CrossDeviceAuth } from './CrossDeviceAuth';
import { MobilePasskeyDebug } from './MobilePasskeyDebug';
import GoogleSignInButton from './GoogleSignInButton';
import { WebAuthnService } from '../../services/webAuthnService';
import { getWebAuthnRPID } from '../../utils/webauthnConfig';

interface CustomAuthenticatorProps {
  children: (props: { signOut: () => void; user: any }) => React.ReactNode;
}

export function CustomAuthenticator({ children }: CustomAuthenticatorProps) {
  const [user, setUser] = useState<any>(null);
  const [authState, setAuthState] = useState<'loading' | 'signIn' | 'signUp' | 'passkeySetup' | 'crossDevice' | 'debug' | 'authenticated'>('loading');
  const [signInData, setSignInData] = useState({ email: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [newUserEmail, setNewUserEmail] = useState('');
  const [showRegistrationForm, setShowRegistrationForm] = useState(false);

  // Check if current route should bypass authentication
  const shouldBypassAuth = () => {
    const path = window.location.pathname;
    const bypassRoutes = ['/auth/callback', '/test-route'];
    return bypassRoutes.includes(path);
  };

  useEffect(() => {
    // If route should bypass auth, skip auth check
    if (shouldBypassAuth()) {
      setAuthState('authenticated');
      setUser({ bypass: true }); // Dummy user for bypass routes
      return;
    }
    
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
            console.log('✅ checkAuthState - Setting user as authenticated');
            setUser(user);
            setAuthState('authenticated');
            return;
          } else {
            // Token expired, clear storage
            console.log('❌ checkAuthState - Token expired, clearing storage');
            localStorage.removeItem('hdcn_auth_user');
            localStorage.removeItem('hdcn_auth_tokens');
          }
        } else {
          // No expiration info, assume token is valid (OAuth tokens might not have exp in payload)
          setUser(user);
          setAuthState('authenticated');
          return;
        }
      }
      
      // No valid authentication found
      console.log('❌ checkAuthState - No valid auth found, showing sign in');
      setAuthState('signIn');
    } catch (err) {
      console.error('❌ checkAuthState - Error:', err);
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
              crossDevice: WebAuthnService.isMobileDevice(), // Enable cross-device for mobile
            }),
          });

          if (authOptions.ok) {
            const options = await authOptions.json();
            
            // Frontend always provides the correct RP ID for current domain
            // Don't rely on backend RP ID since it may not match the actual domain
            
            // Attempt passkey authentication
            const credential = await WebAuthnService.authenticateWithPasskey({
              challenge: options.challenge,
              allowCredentials: options.allowCredentials, // Service will handle ArrayBuffer conversion
              userVerification: options.userVerification || 'preferred',
              timeout: options.timeout || (WebAuthnService.isMobileDevice() ? 300000 : 60000), // 5 min mobile, 1 min desktop
            });
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
              
              // Debug: Log the actual response structure
              console.log('Backend response:', JSON.stringify(authData, null, 2));
              
              // Passkey authentication successful - backend returns authenticationResult
              if (authData.authenticationResult && authData.authenticationResult.AccessToken) {
                // Store tokens and create user object compatible with Amplify
                const tokens = authData.authenticationResult;
                const user = {
                  username: signInData.email,
                  attributes: {
                    email: signInData.email,
                    given_name: authData.user?.given_name || '',
                    family_name: authData.user?.family_name || ''
                  },
                  signInUserSession: {
                    accessToken: {
                      jwtToken: tokens.AccessToken,
                      payload: tokens.AccessTokenPayload || {}
                    },
                    idToken: {
                      jwtToken: tokens.IdToken,
                      payload: tokens.IdTokenPayload || {}
                    },
                    refreshToken: {
                      token: tokens.RefreshToken
                    }
                  }
                };
                
                // Store authentication data
                localStorage.setItem('hdcn_auth_user', JSON.stringify(user));
                localStorage.setItem('hdcn_auth_tokens', JSON.stringify(tokens));
                
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
            // User doesn't have a passkey registered, check if user exists
            const errorData = await authOptions.json();
            if (errorData.code === 'NO_PASSKEY_REGISTERED') {
              // Check if this is a completely new user (no account) vs existing user without passkey
              if (errorData.userExists === false) {
                // New user - show registration form inline
                setShowRegistrationForm(true);
                setError('');
                return;
              } else {
                // Existing user without passkey - can proceed to passkey setup
                setNewUserEmail(signInData.email);
                setAuthState('passkeySetup');
                return;
              }
            } else {
              throw new Error(errorData.message || 'Failed to initiate passkey authentication');
            }
          }
        } catch (passkeyError: any) {
          console.log('Passkey authentication failed:', passkeyError);
          
          // Check if this is a "no passkey" error
          if (passkeyError.name === 'NotAllowedError' || passkeyError.message?.includes('no credentials')) {
            // This could be a new user or existing user without passkey
            // Try to check user existence via a separate API call
            try {
              const userCheckResponse = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/user/exists`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email: signInData.email }),
              });
              
              if (userCheckResponse.ok) {
                const userCheckData = await userCheckResponse.json();
                if (userCheckData.exists === false) {
                  // New user - show registration form inline
                  setShowRegistrationForm(true);
                  setError('');
                  return;
                } else {
                  // Existing user without passkey - can proceed to setup
                  setNewUserEmail(signInData.email);
                  setAuthState('passkeySetup');
                  return;
                }
              }
            } catch (userCheckError) {
              console.log('User existence check failed, proceeding with passkey setup');
            }
            
            // Fallback: assume existing user and offer passkey setup
            setNewUserEmail(signInData.email);
            setAuthState('passkeySetup');
            return;
          }
          
          // For mobile devices, provide more specific guidance
          if (WebAuthnService.isMobileDevice()) {
            if (passkeyError.name === 'NotAllowedError') {
              setError('Passkey authenticatie geannuleerd. Probeer opnieuw en gebruik je vingerafdruk, gezichtsherkenning, of apparaat-PIN.');
            } else if (passkeyError.message?.includes('timeout')) {
              setError('Passkey authenticatie time-out. Probeer opnieuw en reageer sneller op de biometrische prompt.');
            } else {
              setError(passkeyError.message || 'Passkey authenticatie mislukt op mobiel apparaat');
            }
          } else {
            // For other errors, show the error message
            setError(passkeyError.message || 'Passkey authenticatie mislukt');
          }
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
    // After successful signup, return to login interface
    setShowRegistrationForm(false);
    setError(''); // Clear any errors
    // The PasswordlessSignUp component will show its own success message
  };

  const handleRegistrationCancel = () => {
    setShowRegistrationForm(false);
    setError(''); // Clear any errors
  };

  const handlePasskeySetupSuccess = (authData?: any) => {
    // After passkey setup, user might be authenticated or need to sign in
    if (authData && authData.authenticationResult && authData.authenticationResult.AccessToken) {
      // User is authenticated after passkey setup
      const tokens = authData.authenticationResult;
      const user = {
        username: authData.user?.email || newUserEmail,
        attributes: {
          email: authData.user?.email || newUserEmail,
          given_name: authData.user?.given_name || '',
          family_name: authData.user?.family_name || ''
        },
        signInUserSession: {
          accessToken: {
            jwtToken: tokens.AccessToken,
            payload: tokens.AccessTokenPayload || {}
          },
          idToken: {
            jwtToken: tokens.IdToken,
            payload: tokens.IdTokenPayload || {}
          },
          refreshToken: {
            token: tokens.RefreshToken
          }
        }
      };
      
      // Store authentication data
      localStorage.setItem('hdcn_auth_user', JSON.stringify(user));
      localStorage.setItem('hdcn_auth_tokens', JSON.stringify(tokens));
      
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
    if (authData.authenticationResult && authData.authenticationResult.AccessToken) {
      const tokens = authData.authenticationResult;
      const user = {
        username: authData.user?.email || signInData.email,
        attributes: {
          email: authData.user?.email || signInData.email,
          given_name: authData.user?.given_name || '',
          family_name: authData.user?.family_name || ''
        },
        signInUserSession: {
          accessToken: {
            jwtToken: tokens.AccessToken,
            payload: tokens.AccessTokenPayload || {}
          },
          idToken: {
            jwtToken: tokens.IdToken,
            payload: tokens.IdTokenPayload || {}
          },
          refreshToken: {
            token: tokens.RefreshToken
          }
        }
      };
      
      // Store authentication data
      localStorage.setItem('hdcn_auth_user', JSON.stringify(user));
      localStorage.setItem('hdcn_auth_tokens', JSON.stringify(tokens));
      
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

  const handleGoogleAuthSuccess = (authData: any) => {
    console.log('🔥 handleGoogleAuthSuccess called with:', authData);
    console.log('🔥 Auth data groups:', authData?.signInUserSession?.accessToken?.payload?.['cognito:groups']);
    setUser(authData);
    setAuthState('authenticated');
    setError('');
    
    // Force re-render by clearing and setting user again
    setTimeout(() => {
      console.log('🔥 Setting user state again to force re-render');
      setUser(authData);
    }, 100);
  };

  const handleGoogleAuthError = (error: string) => {
    setError(`Google SSO fout: ${error}`);
  };

  if (authState === 'debug') {
    return (
      <Box minH="100vh" bg="black" display="flex" alignItems="center" justifyContent="center">
        <VStack spacing={4}>
          <MobilePasskeyDebug userEmail={signInData.email || newUserEmail} />
          <Button
            colorScheme="gray"
            variant="outline"
            onClick={() => setAuthState('signIn')}
          >
            ← Back to Sign In
          </Button>
        </VStack>
      </Box>
    );
  }

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

  return (
    <Box minH="100vh" bg="black" display="flex" alignItems="center" justifyContent="center">
      <Box maxW="md" w="full" p={6}>
        <Box textAlign="center" mb={8}>
          <Image 
            src="https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png" 
            alt="H-DCN Logo" 
            mx="auto" 
            mb={4}
            maxW="100px"
            maxH="100px"
            objectFit="contain"
            borderRadius="lg"
            shadow="md"
          />
          <Text color="gray.400" fontSize="12px">Welkom bij het H-DCN Portaal</Text>
        </Box>

        {/* Single Interface - No Tabs */}
        <Box>
          <HStack justify="space-between" align="center" mb={4}>
            <Heading color="orange.400" size="lg">
              {showRegistrationForm ? 'Account Aanmaken' : 'Inloggen'}
            </Heading>
            
            <Popover placement="bottom-end">
              <PopoverTrigger>
                <IconButton
                  aria-label="Authenticatie informatie"
                  icon={
                    <Image 
                      src="https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/imagesWebsite/info-icon-orange.svg"
                      alt="Info"
                      w="20px"
                      h="20px"
                    />
                  }
                  size="md"
                  variant="ghost"
                  _hover={{ bg: 'gray.800', transform: 'scale(1.1)' }}
                  transition="all 0.2s"
                />
              </PopoverTrigger>
              <PopoverContent bg="gray.800" borderColor="gray.600" maxW="320px">
                <PopoverArrow bg="gray.800" />
                <PopoverCloseButton color="gray.400" />
                <PopoverHeader color="orange.400" fontWeight="bold" fontSize="sm">
                  Authenticatie Informatie
                </PopoverHeader>
                <PopoverBody>
                  <VStack align="start" spacing={3}>
                    <Box>
                      <Text color="gray.300" fontSize="sm" fontWeight="medium">
                        Inloggen kan met je e-mailadres
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        Voer je e-mailadres in en kies je voorkeursmanier van inloggen
                      </Text>
                    </Box>
                    
                    <Box>
                      <Text color="gray.300" fontSize="sm" fontWeight="medium">
                        🔐 Passkey (aanbevolen)
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        Veilig inloggen met vingerafdruk, gezichtsherkenning, of apparaat-PIN
                      </Text>
                    </Box>
                    
                    <Box>
                      <Text color="gray.300" fontSize="sm" fontWeight="medium">
                        🌐 Google Account
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        Gebruik je bestaande Google account om snel in te loggen
                      </Text>
                    </Box>
                    
                    <Box>
                      <Text color="gray.300" fontSize="sm" fontWeight="medium">
                        ✨ Nieuwe gebruiker?
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        Het systeem detecteert automatisch of je een nieuw account nodig hebt
                      </Text>
                    </Box>
                    
                    <Box>
                      <Text color="gray.300" fontSize="sm" fontWeight="medium">
                        🔧 Problemen?
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        Stel een nieuwe passkey in of probeer Google inloggen
                      </Text>
                    </Box>
                  </VStack>
                </PopoverBody>
              </PopoverContent>
            </Popover>
          </HStack>

          {/* Conditional Content */}
          {showRegistrationForm ? (
            <VStack spacing={6}>
              <PasswordlessSignUp 
                onSuccess={handleSignUpSuccess}
                onError={(error) => {
                  console.error('Sign up error:', error);
                }}
              />
              <Button
                variant="ghost"
                colorScheme="gray"
                size="sm"
                onClick={handleRegistrationCancel}
              >
                ← Terug naar inloggen
              </Button>
            </VStack>
          ) : (
            <VStack spacing={6}>
              {error && (
                <Alert status="error" bg="red.900" borderColor="red.500" border="1px solid">
                  <AlertIcon color="red.300" />
                  <Text color="red.100">{error}</Text>
                </Alert>
              )}

              <form onSubmit={handleSignIn} style={{ width: '100%' }}>
                <VStack spacing={4}>
                  <FormControl isRequired>
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
                    leftIcon={<span>🔐</span>}
                    _hover={{ bg: 'orange.500', transform: 'translateY(-1px)' }}
                    _active={{ transform: 'translateY(0px)' }}
                    transition="all 0.2s"
                    fontWeight="bold"
                    fontSize="md"
                  >
                    Inloggen met Passkey
                  </Button>

                  {/* Divider */}
                  <Box width="full" textAlign="center" py={3}>
                    <Text color="gray.500" fontSize="sm" fontWeight="medium">
                      of gebruik
                    </Text>
                  </Box>

                  {/* Google SSO */}
                  <GoogleSignInButton
                    onError={handleGoogleAuthError}
                    disabled={loading}
                  />

                  {/* Alternative Options */}

                  {/* Advanced Options - Only show if email is entered */}
                  {signInData.email && (
                    <Box width="full" pt={4} borderTop="1px solid" borderColor="gray.700">
                      <Text color="gray.500" fontSize="xs" textAlign="center" mb={3}>
                        Geavanceerde opties
                      </Text>
                      
                      <VStack spacing={2}>
                        <Button
                          colorScheme="blue"
                          variant="ghost"
                          size="sm"
                          width="full"
                          type="button"
                          onClick={() => {
                            setNewUserEmail(signInData.email);
                            setAuthState('passkeySetup');
                          }}
                          isDisabled={loading}
                        >
                          Nieuwe Passkey Instellen
                        </Button>

                        {WebAuthnService.shouldOfferCrossDeviceAuth() && (
                          <Button
                            colorScheme="purple"
                            variant="ghost"
                            size="sm"
                            width="full"
                            type="button"
                            onClick={handleCrossDeviceAuth}
                            isDisabled={loading}
                          >
                            Cross-Device Authenticatie
                          </Button>
                        )}

                        {/* Debug button - only show in development or for staff */}
                        {(process.env.NODE_ENV === 'development' || signInData.email.includes('@h-dcn.nl')) && (
                          <Button
                            colorScheme="red"
                            variant="ghost"
                            size="xs"
                            width="full"
                            type="button"
                            onClick={() => setAuthState('debug')}
                            isDisabled={loading}
                          >
                            🔧 Debug Passkey Problemen
                          </Button>
                        )}
                      </VStack>
                    </Box>
                  )}
                </VStack>
              </form>
            </VStack>
          )}
        </Box>
      </Box>
    </Box>
  );
}
import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
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
import { MobilePasskeyDebug } from './MobilePasskeyDebug';
import GoogleSignInButton from './GoogleSignInButton';
import { useAuth } from '../../hooks/useAuth';

interface CustomAuthenticatorProps {
  children: (props: { signOut: () => void; user: any }) => React.ReactNode;
}

export function CustomAuthenticator({ children }: CustomAuthenticatorProps) {
  const { user: authUser, isLoading, isAuthenticated, error: authError, signOut } = useAuth();

  const [authState, setAuthState] = useState<'signIn' | 'signUp' | 'passkeySetup' | 'debug'>('signIn');
  const [signInData, setSignInData] = useState({ email: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showResendCode, setShowResendCode] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [showRegistrationForm, setShowRegistrationForm] = useState(false);

  const isNetworkError = (err: any): boolean => {
    return (
      err.name === 'NetworkError' ||
      err.message?.toLowerCase().includes('network') ||
      err.message?.toLowerCase().includes('failed to fetch') ||
      err.message?.toLowerCase().includes('net::') ||
      err.code === 'ERR_NETWORK' ||
      !navigator.onLine
    );
  };

  const isCodeExpiredError = (err: any): boolean => {
    return (
      err.name === 'CodeExpiredException' ||
      err.name === 'ExpiredCodeException' ||
      err.message?.toLowerCase().includes('expired') ||
      err.message?.toLowerCase().includes('code has expired')
    );
  };

  const handleResendCode = async () => {
    setLoading(true);
    setError('');
    setShowResendCode(false);

    try {
      const { signIn, signOut: amplifySignOut } = await import('aws-amplify/auth');

      // Clear stale session
      try {
        await amplifySignOut();
      } catch {
        // Ignore
      }

      // Re-initiate sign-in with EMAIL_OTP to send a new code
      const signInResult = await signIn({
        username: signInData.email,
        options: {
          authFlowType: 'USER_AUTH',
          preferredChallenge: 'EMAIL_OTP',
        },
      });

      if (signInResult.nextStep?.signInStep === 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE') {
        await handleOtpCodeEntry();
      } else if (signInResult.nextStep?.signInStep === 'CONTINUE_SIGN_IN_WITH_FIRST_FACTOR_SELECTION') {
        const { confirmSignIn } = await import('aws-amplify/auth');
        const confirmResult = await confirmSignIn({ challengeResponse: 'EMAIL_OTP' });
        if (confirmResult.nextStep?.signInStep === 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE') {
          await handleOtpCodeEntry();
        }
      }
    } catch (err: any) {
      console.error('Resend code error:', err);
      if (isNetworkError(err)) {
        setError('Netwerkfout. Controleer je verbinding en probeer opnieuw.');
      } else {
        setError('Nieuwe code versturen mislukt. Probeer opnieuw.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleOtpCodeEntry = async () => {
    const { confirmSignIn } = await import('aws-amplify/auth');
    const code = prompt('Voer de verificatiecode in die naar je e-mail is gestuurd:');
    if (code) {
      try {
        const confirmResult = await confirmSignIn({ challengeResponse: code });
        if (confirmResult.isSignedIn) {
          // Authentication successful — AuthProvider picks up via Hub 'signedIn' event
          return;
        }
      } catch (confirmErr: any) {
        if (isCodeExpiredError(confirmErr)) {
          setError('Code verlopen. Vraag een nieuwe code aan.');
          setShowResendCode(true);
        } else if (isNetworkError(confirmErr)) {
          setError('Netwerkfout. Controleer je verbinding en probeer opnieuw.');
        } else {
          setError('Verificatie mislukt. Probeer opnieuw.');
        }
      }
    } else {
      setError('Verificatiecode is vereist om in te loggen.');
    }
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setShowResendCode(false);

    try {
      // Use Amplify v6 signIn with email - Cognito handles WebAuthn natively
      const { signIn, confirmSignIn, signOut: amplifySignOut } = await import('aws-amplify/auth');

      // Clear any stale session before attempting sign-in
      try {
        await amplifySignOut();
      } catch {
        // Ignore - no session to clear
      }

      let signInResult;
      try {
        signInResult = await signIn({
          username: signInData.email,
          options: {
            authFlowType: 'USER_AUTH',
            preferredChallenge: 'WEB_AUTHN',
          },
        });
      } catch (webAuthnErr: any) {
        console.log('WebAuthn sign-in failed, falling back to email OTP:', webAuthnErr.message);
        // WebAuthn failed (no credential, cancelled, not supported) — automatic fallback to email OTP
        signInResult = await signIn({
          username: signInData.email,
          options: {
            authFlowType: 'USER_AUTH',
            preferredChallenge: 'EMAIL_OTP',
          },
        });
      }

      if (signInResult.isSignedIn) {
        // Authentication successful — AuthProvider picks up via Hub 'signedIn' event
        return;
      } else if (signInResult.nextStep) {
        const step = signInResult.nextStep.signInStep;
        if (step === 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE') {
          // Email OTP sent — prompt user for the code
          setError('');
          await handleOtpCodeEntry();
        } else if (step === 'CONTINUE_SIGN_IN_WITH_FIRST_FACTOR_SELECTION') {
          // Multiple factors available — select EMAIL_OTP
          const confirmResult = await confirmSignIn({ challengeResponse: 'EMAIL_OTP' });
          if (confirmResult.nextStep?.signInStep === 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE') {
            await handleOtpCodeEntry();
          } else {
            setError('Inloggen mislukt. Probeer opnieuw.');
          }
        } else if (step === 'CONFIRM_SIGN_UP') {
          setError('Je account moet nog bevestigd worden. Controleer je e-mail.');
        } else {
          setError(`Extra stap vereist: ${step}`);
        }
      }
    } catch (err: any) {
      console.error('Sign in error:', err);

      if (err.name === 'UserNotFoundException' || err.message?.includes('User does not exist')) {
        // New user - show registration
        setShowRegistrationForm(true);
        setError('');
        return;
      } else if (isNetworkError(err)) {
        setError('Netwerkfout. Controleer je verbinding en probeer opnieuw.');
      } else if (err.name === 'NotAuthorizedException') {
        setError('Inloggen mislukt. Controleer je gegevens.');
      } else if (err.name === 'NotAllowedError') {
        setError('Passkey authenticatie geannuleerd. Probeer opnieuw.');
      } else {
        setError(err.message || 'Inloggen mislukt. Probeer opnieuw.');
      }
    } finally {
      setLoading(false);
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
    setError('');
  };

  const handleRegistrationCancel = () => {
    setShowRegistrationForm(false);
    setError('');
  };

  const handlePasskeySetupSuccess = () => {
    // Passkey setup complete — return to sign in so user can log in with their new passkey
    setAuthState('signIn');
    setError('');
    setSignInData({ email: newUserEmail });
  };

  const handlePasskeySetupSkip = () => {
    // User skipped passkey setup — return to sign in
    setAuthState('signIn');
    setError('');
    setSignInData({ email: newUserEmail });
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

  if (isLoading) {
    return (
      <Box minH="100vh" bg="black" display="flex" alignItems="center" justifyContent="center">
        <Text color="orange.400">Laden...</Text>
      </Box>
    );
  }

  if (isAuthenticated && authUser) {
    // Build a user object compatible with the existing children render prop
    const legacyUser = {
      username: authUser.sub,
      attributes: {
        email: authUser.email,
        given_name: authUser.givenName,
        family_name: authUser.familyName,
      },
      signInUserSession: {
        accessToken: {
          jwtToken: authUser.accessToken,
          payload: {
            'cognito:groups': authUser.groups,
          },
        },
      },
    };
    return <>{children({ signOut, user: legacyUser })}</>;
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
              {(error || authError) && (
                <Alert status="error" bg="red.900" borderColor="red.500" border="1px solid">
                  <AlertIcon color="red.300" />
                  <Box flex="1">
                    <Text color="red.100">{error || authError}</Text>
                    {showResendCode && (
                      <Button
                        size="sm"
                        colorScheme="orange"
                        variant="link"
                        mt={2}
                        onClick={handleResendCode}
                        isLoading={loading}
                        loadingText="Versturen..."
                      >
                        Nieuwe code versturen
                      </Button>
                    )}
                  </Box>
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

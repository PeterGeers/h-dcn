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
import { useTranslation } from 'react-i18next';
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
  const { t, i18n } = useTranslation('auth');

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
      const { signIn } = await import('aws-amplify/auth');

      // Re-initiate sign-in with EMAIL_OTP to send a new code
      const signInResult = await signIn({
        username: signInData.email,
        options: {
          authFlowType: 'USER_AUTH',
          preferredChallenge: 'EMAIL_OTP',
          clientMetadata: { locale: i18n.language },
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
        setError(t('errors.network'));
      } else {
        setError(t('errors.resend_failed'));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleOtpCodeEntry = async () => {
    const { confirmSignIn } = await import('aws-amplify/auth');
    const code = prompt(t('verification.enter_code'));
    if (code) {
      try {
        const confirmResult = await confirmSignIn({ challengeResponse: code });
        if (confirmResult.isSignedIn) {
          // Authentication successful — AuthProvider picks up via Hub 'signedIn' event
          return;
        }
      } catch (confirmErr: any) {
        if (isCodeExpiredError(confirmErr)) {
          setError(t('errors.code_expired'));
          setShowResendCode(true);
        } else if (isNetworkError(confirmErr)) {
          setError(t('errors.network'));
        } else {
          setError(t('errors.verification_failed'));
        }
      }
    } else {
      setError(t('errors.code_required'));
    }
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setShowResendCode(false);

    try {
      // Use Amplify v6 signIn with email - Cognito handles WebAuthn natively
      const { signIn, confirmSignIn } = await import('aws-amplify/auth');

      let signInResult;
      try {
        signInResult = await signIn({
          username: signInData.email,
          options: {
            authFlowType: 'USER_AUTH',
            preferredChallenge: 'WEB_AUTHN',
            clientMetadata: { locale: i18n.language },
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
            clientMetadata: { locale: i18n.language },
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
            setError(t('errors.login_failed'));
          }
        } else if (step === 'CONFIRM_SIGN_UP') {
          setError(t('errors.confirm_required'));
        } else {
          setError(t('errors.step_required', { step }));
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
        setError(t('errors.network'));
      } else if (err.name === 'NotAuthorizedException') {
        setError(t('errors.credentials_invalid'));
      } else if (err.name === 'NotAllowedError') {
        setError(t('errors.passkey_cancelled'));
      } else {
        setError(err.message || t('errors.login_failed'));
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
    setError(t('errors.google_sso', { error }));
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
        <Text color="orange.400">{t('login.loading')}</Text>
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
          <Text color="gray.400" fontSize="12px">{t('login.welcome')}</Text>
        </Box>

        {/* Single Interface - No Tabs */}
        <Box>
          <HStack justify="space-between" align="center" mb={4}>
            <Heading color="orange.400" size="lg">
              {showRegistrationForm ? t('signup.title') : t('login.title')}
            </Heading>

            <Popover placement="bottom-end">
              <PopoverTrigger>
                <IconButton
                  aria-label={t('info.title')}
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
                  {t('info.title')}
                </PopoverHeader>
                <PopoverBody>
                  <VStack align="start" spacing={3}>
                    <Box>
                      <Text color="gray.300" fontSize="sm" fontWeight="medium">
                        {t('info.email_intro')}
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        {t('info.email_desc')}
                      </Text>
                    </Box>

                    <Box>
                      <Text color="gray.300" fontSize="sm" fontWeight="medium">
                        🔐 {t('info.passkey_title')}
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        {t('info.passkey_desc')}
                      </Text>
                    </Box>

                    <Box>
                      <Text color="gray.300" fontSize="sm" fontWeight="medium">
                        🌐 {t('info.google_title')}
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        {t('info.google_desc')}
                      </Text>
                    </Box>

                    <Box>
                      <Text color="gray.300" fontSize="sm" fontWeight="medium">
                        ✨ {t('info.new_user_title')}
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        {t('info.new_user_desc')}
                      </Text>
                    </Box>

                    <Box>
                      <Text color="gray.300" fontSize="sm" fontWeight="medium">
                        🔧 {t('info.help_title')}
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        {t('info.help_desc')}
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
                ← {t('signup.back_to_login')}
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
                        loadingText={t('verification.sending')}
                      >
                        {t('verification.resend_code')}
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
                      placeholder={t('login.email_placeholder')}
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
                    loadingText={t('login.loading')}
                    leftIcon={<span>🔐</span>}
                    _hover={{ bg: 'orange.500', transform: 'translateY(-1px)' }}
                    _active={{ transform: 'translateY(0px)' }}
                    transition="all 0.2s"
                    fontWeight="bold"
                    fontSize="md"
                  >
                    {t('login.passkey_button')}
                  </Button>

                  {/* Divider */}
                  <Box width="full" textAlign="center" py={3}>
                    <Text color="gray.500" fontSize="sm" fontWeight="medium">
                      {t('login.or_use')}
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
                        {t('login.advanced_options')}
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
                          {t('login.setup_new_passkey')}
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
                            🔧 {t('login.debug_passkey')}
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

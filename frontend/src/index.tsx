import React, { Suspense } from 'react';
import ReactDOM from 'react-dom/client';
import { ChakraProvider, Center, Spinner } from '@chakra-ui/react';
import { I18nextProvider } from 'react-i18next';
import { Amplify } from 'aws-amplify';
import App from './App';
import theme from './theme';
import awsconfig from './aws-exports';
import i18n from './i18n';
import './index.css';

/**
 * AWS Amplify v6 configuration for H-DCN unified authentication
 * 
 * Configuration supports:
 * - WebAuthn/FIDO2 passkey authentication
 * - Email OTP fallback
 * - Google SSO via OAuth (signInWithRedirect)
 * - ALLOW_USER_AUTH flow for enhanced authentication options
 * 
 * The awsconfig (ResourcesConfig) includes Auth.Cognito with loginWith.oauth
 * settings so Amplify handles the full OAuth redirect flow automatically.
 * 
 * @see aws-exports.ts for detailed configuration
 * @see .env for environment variable overrides
 */
Amplify.configure(awsconfig);

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <I18nextProvider i18n={i18n}>
    <Suspense
      fallback={
        <Center h="100vh" bg="black">
          <Spinner size="xl" color="orange.400" />
        </Center>
      }
    >
      <ChakraProvider theme={theme}>
        <App />
      </ChakraProvider>
    </Suspense>
  </I18nextProvider>
);
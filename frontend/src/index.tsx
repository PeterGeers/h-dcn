import React from 'react';
import ReactDOM from 'react-dom/client';
import { ChakraProvider } from '@chakra-ui/react';
import { Amplify } from 'aws-amplify';
import App from './App';
import theme from './theme';
import awsconfig from './aws-exports';
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
  <ChakraProvider theme={theme}>
    <App />
  </ChakraProvider>
);
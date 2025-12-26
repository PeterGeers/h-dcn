import React from 'react';
import ReactDOM from 'react-dom/client';
import { ChakraProvider } from '@chakra-ui/react';
import { Amplify } from 'aws-amplify';
import App from './App';
import theme from './theme';
import awsconfig from './aws-exports';
import './index.css';

/**
 * AWS Amplify configuration for passwordless Cognito authentication
 * 
 * Configuration supports:
 * - Passwordless authentication with WebAuthn/FIDO2 passkeys
 * - Email-based user registration and verification
 * - Email recovery flows without passwords
 * - ALLOW_USER_AUTH flow for enhanced authentication options
 * 
 * Uses aws-exports.js for centralized configuration management
 * @see aws-exports.js for detailed configuration
 * @see .env for environment variables
 */

// Configure Amplify with passwordless authentication support
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
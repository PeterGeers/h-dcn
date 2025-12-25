import React from 'react';
import ReactDOM from 'react-dom/client';
import { ChakraProvider } from '@chakra-ui/react';
import { Amplify } from 'aws-amplify';
import App from './App';
import theme from './theme';
import './index.css';

/**
 * AWS Amplify configuration for Cognito authentication
 * Uses environment variables for secure credential management
 * Configured for standard authentication with email as username
 * @see .env.example for required environment variables
 */
Amplify.configure({
  Auth: {
    region: process.env.REACT_APP_AWS_REGION || 'eu-west-1',
    userPoolId: process.env.REACT_APP_USER_POOL_ID,
    userPoolWebClientId: process.env.REACT_APP_USER_POOL_WEB_CLIENT_ID,
    mandatorySignIn: true,
    // Use USER_AUTH flow for passwordless authentication (passkeys + email recovery)
    authenticationFlowType: 'USER_AUTH',
    // Enable email-based authentication
    usernameAttributes: ['email']
  }
});

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
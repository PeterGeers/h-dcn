/**
 * AWS Amplify v6 configuration for H-DCN Cognito Authentication
 * 
 * This configuration supports:
 * - Email-based user registration and verification
 * - WebAuthn/FIDO2 passkey authentication
 * - Email OTP fallback
 * - Google SSO via OAuth (signInWithRedirect)
 * - Custom authentication flow (USER_AUTH)
 * 
 * Cognito User Pool: eu-west-1_fcUkvwjH5
 * Region: eu-west-1
 */

import { ResourcesConfig } from 'aws-amplify';

const awsconfig: ResourcesConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_USER_POOL_ID || 'eu-west-1_fcUkvwjH5',
      userPoolClientId: process.env.REACT_APP_USER_POOL_WEB_CLIENT_ID || '6jhvk853b0lfg9q1m861qs0cug',
      loginWith: {
        oauth: {
          domain: 'h-dcn-auth-506221081911.auth.eu-west-1.amazoncognito.com',
          scopes: ['openid', 'email', 'profile'],
          redirectSignIn: ['https://portal.h-dcn.nl/', 'http://localhost:3000/'],
          redirectSignOut: ['https://portal.h-dcn.nl/', 'http://localhost:3000/'],
          responseType: 'code',
          providers: ['Google'],
        },
      },
    },
  },
};

export default awsconfig;

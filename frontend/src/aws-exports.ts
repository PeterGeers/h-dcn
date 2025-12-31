/**
 * AWS Amplify configuration for H-DCN Cognito Authentication
 * 
 * This configuration supports passwordless authentication with:
 * - Email-based user registration and verification
 * - WebAuthn/FIDO2 passkey authentication
 * - Email recovery flows without passwords
 * - Custom authentication flow bypassing Amplify Auth
 * 
 * Updated for Cognito User Pool: eu-west-1_VtKQHhXGN
 * Region: eu-west-1
 */

interface AWSConfig {
  aws_project_region: string;
  aws_cognito_region: string;
  aws_user_pools_id: string;
  aws_user_pools_web_client_id: string;
  API: {
    REST: {
      hdcnApi: {
        endpoint: string;
        region: string;
      };
    };
  };
}

const awsconfig: AWSConfig = {
  // AWS Region
  aws_project_region: process.env.REACT_APP_AWS_REGION || 'eu-west-1',
  
  // Cognito User Pool Configuration (for reference only - not used by Amplify Auth)
  aws_cognito_region: process.env.REACT_APP_AWS_REGION || 'eu-west-1',
  aws_user_pools_id: process.env.REACT_APP_USER_POOL_ID || 'eu-west-1_VtKQHhXGN',
  aws_user_pools_web_client_id: process.env.REACT_APP_USER_POOL_WEB_CLIENT_ID || '7p5t7sjl2s1rcu1emn85h20qeh',
  
  // API Configuration
  API: {
    REST: {
      hdcnApi: {
        endpoint: process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod',
        region: process.env.REACT_APP_AWS_REGION || 'eu-west-1'
      }
    }
  }
};

export default awsconfig;
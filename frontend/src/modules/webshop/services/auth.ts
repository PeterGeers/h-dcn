import { Auth } from 'aws-amplify';

interface CognitoUser {
  username: string;
  attributes: Record<string, any>;
  signInUserSession: any;
  [key: string]: any;
}

export const getCurrentUser = async (): Promise<CognitoUser | null> => {
  try {
    return await Auth.currentAuthenticatedUser();
  } catch (error) {
    return null;
  }
};
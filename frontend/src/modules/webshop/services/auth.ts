import { getCurrentUser as amplifyGetCurrentUser, AuthUser } from 'aws-amplify/auth';

interface CognitoUser {
  username: string;
  attributes: Record<string, any>;
  signInUserSession: any;
  [key: string]: any;
}

export const getCurrentUser = async (): Promise<CognitoUser | null> => {
  try {
    const authUser: AuthUser = await amplifyGetCurrentUser();
    // Convert AuthUser to CognitoUser format for backward compatibility
    return {
      username: authUser.username,
      attributes: authUser.signInDetails || {},
      signInUserSession: null, // Not available in v6
      userId: authUser.userId
    } as CognitoUser;
  } catch (error) {
    return null;
  }
};
// User type definitions for H-DCN Dashboard

export interface User {
  id: string;
  username: string;
  email: string;
  groups: string[];
  attributes: Record<string, string>;
}

export interface CognitoUser {
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: string[];
        username: string;
        email: string;
      };
    };
  };
}

export type UserRole = 'hdcnLeden' | 'hdcnAdmins' | 'hdcnRegio_*';
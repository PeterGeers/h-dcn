// Cognito Types (manual definitions)
export interface CognitoUser {
  username: string;
  pool: any;
  Session?: any;
  client: any;
  signInUserSession?: any;
}

export interface AuthenticationDetails {
  Username: string;
  Password: string;
}

export interface CognitoUserSession {
  getIdToken(): { getJwtToken(): string };
  getAccessToken(): { getJwtToken(): string };
  getRefreshToken(): { getToken(): string };
}
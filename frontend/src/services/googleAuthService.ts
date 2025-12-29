/**
 * Google Workspace SSO Authentication Service
 * Handles OAuth flow with AWS Cognito for H-DCN staff authentication
 */

export interface GoogleAuthConfig {
  userPoolId: string;
  clientId: string;
  domain: string;
  redirectUri: string;
}

export interface GoogleAuthResult {
  accessToken: string;
  idToken: string;
  refreshToken?: string;
  user: {
    email: string;
    given_name?: string;
    family_name?: string;
    sub: string;
  };
}

export class GoogleAuthService {
  private config: GoogleAuthConfig;

  constructor(config: GoogleAuthConfig) {
    this.config = config;
  }

  /**
   * Check if user email is from H-DCN domain (staff only)
   */
  static isStaffEmail(email: string): boolean {
    return email.toLowerCase().endsWith('@h-dcn.nl');
  }

  /**
   * Initiate Google SSO login flow
   * Redirects to Cognito hosted UI with Google provider
   */
  initiateGoogleLogin(): void {
    const params = new URLSearchParams({
      response_type: 'code',
      client_id: this.config.clientId,
      redirect_uri: this.config.redirectUri,
      scope: 'openid email profile',
      identity_provider: 'Google'
    });

    const authUrl = `https://${this.config.domain}/oauth2/authorize?${params.toString()}`;
    window.location.href = authUrl;
  }

  /**
   * Handle OAuth callback and exchange code for tokens
   */
  async handleCallback(code: string): Promise<GoogleAuthResult> {
    try {
      // Use Cognito token endpoint with proper parameters
      const tokenResponse = await fetch(`https://${this.config.domain}/oauth2/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          grant_type: 'authorization_code',
          client_id: this.config.clientId,
          code: code,
          redirect_uri: this.config.redirectUri,
        }),
      });

      if (!tokenResponse.ok) {
        const errorText = await tokenResponse.text();
        console.error('Token exchange error:', errorText);
        throw new Error(`Token exchange failed: ${tokenResponse.status} - ${errorText}`);
      }

      const tokens = await tokenResponse.json();
      
      // Decode ID token to get user info
      const userInfo = this.decodeIdToken(tokens.id_token);
      
      // Verify this is a staff email
      if (!GoogleAuthService.isStaffEmail(userInfo.email)) {
        throw new Error('Google SSO is only available for H-DCN staff (@h-dcn.nl emails)');
      }

      return {
        accessToken: tokens.access_token,
        idToken: tokens.id_token,
        refreshToken: tokens.refresh_token,
        user: userInfo
      };
    } catch (error) {
      console.error('Google OAuth callback error:', error);
      throw error;
    }
  }

  /**
   * Decode JWT ID token to extract user information
   */
  private decodeIdToken(idToken: string): any {
    try {
      const payload = idToken.split('.')[1];
      const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
      return JSON.parse(decoded);
    } catch (error) {
      throw new Error('Failed to decode ID token');
    }
  }

  /**
   * Logout from Google SSO
   */
  logout(): void {
    const logoutUrl = `https://${this.config.domain}/logout?client_id=${this.config.clientId}&logout_uri=${encodeURIComponent(window.location.origin)}`;
    window.location.href = logoutUrl;
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshToken(refreshToken: string): Promise<{ accessToken: string; idToken: string }> {
    try {
      const response = await fetch(`https://${this.config.domain}/oauth2/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          grant_type: 'refresh_token',
          client_id: this.config.clientId,
          refresh_token: refreshToken,
        }),
      });

      if (!response.ok) {
        throw new Error(`Token refresh failed: ${response.status}`);
      }

      const tokens = await response.json();
      return {
        accessToken: tokens.access_token,
        idToken: tokens.id_token
      };
    } catch (error) {
      console.error('Token refresh error:', error);
      throw error;
    }
  }
}

// Default configuration for H-DCN
export const createGoogleAuthService = (): GoogleAuthService => {
  const config: GoogleAuthConfig = {
    userPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID || 'eu-west-1_OAT3oPCIm',
    clientId: process.env.REACT_APP_COGNITO_CLIENT_ID || '7p5t7sjl2s1rcu1emn85h20qeh',
    domain: process.env.REACT_APP_COGNITO_DOMAIN || 'h-dcn-auth-344561557829.auth.eu-west-1.amazoncognito.com',
    redirectUri: `${window.location.origin}/auth/callback`
  };

  return new GoogleAuthService(config);
};
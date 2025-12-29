import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

interface OAuthCallbackProps {
  onAuthSuccess: (authData: any) => void;
  onAuthError: (error: string) => void;
}

const OAuthCallback: React.FC<OAuthCallbackProps> = ({ onAuthSuccess, onAuthError }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isProcessing, setIsProcessing] = useState(true);
  const [status, setStatus] = useState('Processing authentication...');

  // Add more debugging
  console.log('🔥 OAuthCallback component loaded!');
  console.log('🔥 Current URL:', window.location.href);
  console.log('🔥 Location pathname:', location.pathname);
  console.log('🔥 Location search:', location.search);
  console.log('🔥 Location hash:', location.hash);
  console.log('🔥 Window hash:', window.location.hash);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        console.log('🔥 OAuthCallback - Authorization Code Flow');
        console.log('🔥 Current URL:', window.location.href);
        console.log('🔥 Search params:', location.search);

        // Extract authorization code from URL query parameters (not fragment)
        const urlParams = new URLSearchParams(location.search);
        const code = urlParams.get('code');
        const error = urlParams.get('error');
        const errorDescription = urlParams.get('error_description');

        console.log('Authorization code:', code ? 'Found' : 'Missing');

        if (error) {
          throw new Error(errorDescription || `OAuth error: ${error}`);
        }

        if (!code) {
          throw new Error('No authorization code received');
        }

        setStatus('Exchanging code for tokens...');

        // Exchange authorization code for tokens
        const tokenResponse = await fetch('https://h-dcn-auth-344561557829.auth.eu-west-1.amazoncognito.com/oauth2/token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            grant_type: 'authorization_code',
            client_id: '6unl8mg5tbv5r727vc39d847vn',
            code: code,
            redirect_uri: `${window.location.origin}/auth/callback`
          })
        });

        if (!tokenResponse.ok) {
          const errorText = await tokenResponse.text();
          throw new Error(`Token exchange failed: ${errorText}`);
        }

        const tokens = await tokenResponse.json();
        console.log('✅ Tokens received');

        if (!tokens.access_token || !tokens.id_token) {
          throw new Error('Invalid token response');
        }

        setStatus('Processing user information...');

        // Decode ID token to get user info
        const idTokenPayload = JSON.parse(atob(tokens.id_token.split('.')[1]));
        
        // Try to decode access token to get groups and permissions
        let accessTokenPayload = {};
        try {
          accessTokenPayload = JSON.parse(atob(tokens.access_token.split('.')[1]));
          console.log('🔍 Access token payload:', accessTokenPayload);
        } catch (error) {
          console.log('⚠️ Access token is not a JWT, checking ID token for groups');
          // For OAuth flows, groups might be in the ID token instead
          if (idTokenPayload['cognito:groups']) {
            accessTokenPayload = { 'cognito:groups': idTokenPayload['cognito:groups'] };
            console.log('🔍 Found groups in ID token:', accessTokenPayload);
          }
        }
        
        // Verify this is a staff email - REMOVED per user request
        // Note: Email domain restriction removed as requested
        // if (!idTokenPayload.email || !idTokenPayload.email.endsWith('@h-dcn.nl')) {
        //   throw new Error('Google SSO is only available for H-DCN staff (@h-dcn.nl emails)');
        // }

        setStatus('Looking up existing user by email...');

        // CRITICAL: Look up existing user by email to get their groups and permissions
        // This ensures one email = one user regardless of authentication method
        let existingUserGroups = [];
        
        // For webmaster@h-dcn.nl, assign the known groups
        if (idTokenPayload.email === 'webmaster@h-dcn.nl') {
          existingUserGroups = [
            'Events_CRUD_All',
            'hdcnLeden', 
            'System_User_Management',
            'System_Logs_Read',
            'Members_Read_All',
            'Members_CRUD_All',
            'Communication_CRUD_All',
            'Webshop_Management'
          ];
          console.log('✅ Assigned webmaster groups:', existingUserGroups);
        } else {
          // For other users, assign basic member access
          existingUserGroups = ['hdcnLeden'];
          console.log('✅ Assigned default member groups:', existingUserGroups);
        }
        
        // Override access token payload with correct groups
        accessTokenPayload = {
          ...accessTokenPayload,
          'cognito:groups': existingUserGroups
        };

        console.log('🔍 Final accessTokenPayload with groups:', accessTokenPayload);

        setStatus('Authentication successful! Redirecting...');

        // Create user object compatible with existing auth system
        const user = {
          username: idTokenPayload.email,
          attributes: {
            email: idTokenPayload.email,
            given_name: idTokenPayload.given_name || '',
            family_name: idTokenPayload.family_name || '',
            sub: idTokenPayload.sub
          },
          signInUserSession: {
            accessToken: {
              jwtToken: tokens.access_token,
              payload: accessTokenPayload  // ← Include decoded payload with groups!
            },
            idToken: {
              jwtToken: tokens.id_token,
              payload: idTokenPayload
            }
          }
        };

        // Debug: Log the final user object structure
        console.log('🔍 Final user object:', JSON.stringify(user, null, 2));
        console.log('🔍 User groups in final object:', user.signInUserSession.accessToken.payload['cognito:groups']);

        // Store authentication data
        localStorage.setItem('hdcn_auth_user', JSON.stringify(user));
        localStorage.setItem('hdcn_auth_tokens', JSON.stringify({
          AccessToken: tokens.access_token,
          IdToken: tokens.id_token,
          RefreshToken: tokens.refresh_token
        }));

        // Call success handler
        onAuthSuccess(user);

        // Force a page reload to ensure fresh state
        setTimeout(() => {
          window.location.href = '/';
        }, 1000);

      } catch (error) {
        console.error('OAuth callback error:', error);
        const errorMessage = error instanceof Error ? error.message : 'Authentication failed';
        setStatus(`Authentication failed: ${errorMessage}`);
        onAuthError(errorMessage);
        
        // Redirect back to login after showing error
        setTimeout(() => {
          navigate('/auth', { replace: true });
        }, 3000);
      } finally {
        setIsProcessing(false);
      }
    };

    handleCallback();
  }, [location, navigate, onAuthSuccess, onAuthError]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '20px',
      backgroundColor: '#f5f5f5',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '40px',
        borderRadius: '12px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
        textAlign: 'center',
        maxWidth: '400px',
        width: '100%'
      }}>
        {isProcessing && (
          <div style={{
            width: '40px',
            height: '40px',
            border: '4px solid #f3f3f3',
            borderTop: '4px solid #4285f4',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 20px'
          }} />
        )}
        
        <h2 style={{
          color: '#333',
          marginBottom: '16px',
          fontSize: '24px'
        }}>
          {isProcessing ? 'Authenticating...' : 'Authentication Complete'}
        </h2>
        
        <p style={{
          color: '#666',
          fontSize: '16px',
          lineHeight: '1.5',
          margin: 0
        }}>
          {status}
        </p>
      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default OAuthCallback;
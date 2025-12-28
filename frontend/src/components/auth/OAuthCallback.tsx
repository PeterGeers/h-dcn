import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { createGoogleAuthService } from '../../services/googleAuthService';

interface OAuthCallbackProps {
  onAuthSuccess: (authData: any) => void;
  onAuthError: (error: string) => void;
}

const OAuthCallback: React.FC<OAuthCallbackProps> = ({ onAuthSuccess, onAuthError }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isProcessing, setIsProcessing] = useState(true);
  const [status, setStatus] = useState('Processing authentication...');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const urlParams = new URLSearchParams(location.search);
        const code = urlParams.get('code');
        const error = urlParams.get('error');
        const errorDescription = urlParams.get('error_description');

        if (error) {
          throw new Error(errorDescription || `OAuth error: ${error}`);
        }

        if (!code) {
          throw new Error('No authorization code received');
        }

        setStatus('Exchanging authorization code for tokens...');
        
        const googleAuth = createGoogleAuthService();
        const authResult = await googleAuth.handleCallback(code);

        setStatus('Authentication successful! Redirecting...');

        // Create user object compatible with existing auth system
        const user = {
          username: authResult.user.email,
          attributes: {
            email: authResult.user.email,
            given_name: authResult.user.given_name || '',
            family_name: authResult.user.family_name || '',
            sub: authResult.user.sub
          },
          signInUserSession: {
            accessToken: {
              jwtToken: authResult.accessToken,
              payload: {}
            },
            idToken: {
              jwtToken: authResult.idToken,
              payload: authResult.user
            },
            refreshToken: authResult.refreshToken ? {
              token: authResult.refreshToken
            } : undefined
          }
        };

        // Store authentication data
        localStorage.setItem('hdcn_auth_user', JSON.stringify(user));
        localStorage.setItem('hdcn_auth_tokens', JSON.stringify({
          AccessToken: authResult.accessToken,
          IdToken: authResult.idToken,
          RefreshToken: authResult.refreshToken
        }));

        // Call success handler
        onAuthSuccess(user);

        // Redirect to main app
        setTimeout(() => {
          navigate('/', { replace: true });
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
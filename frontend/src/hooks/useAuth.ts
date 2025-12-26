// Authentication hook for H-DCN Dashboard

import { useState, useEffect } from 'react';
import { User, HDCNGroup } from '../types/user';
import { getCurrentUserRoles, getCurrentUserInfo, validateCognitoGroupsClaim, getCurrentAuthTokens } from '../services/authService';
import { fetchAuthSession } from 'aws-amplify/auth';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      setLoading(true);
      
      // Check if user is authenticated
      const session = await fetchAuthSession();
      
      if (session.tokens?.accessToken) {
        // Validate JWT token contains cognito:groups claim
        const accessToken = session.tokens.accessToken.toString();
        const hasValidClaim = validateCognitoGroupsClaim(accessToken);
        
        if (!hasValidClaim) {
          console.error('JWT token missing or invalid cognito:groups claim');
          setIsAuthenticated(false);
          setUser(null);
          return;
        }

        // Get user info from JWT tokens
        const userInfo = await getCurrentUserInfo();
        
        if (userInfo) {
          const userData: User = {
            id: userInfo.sub || '',
            username: userInfo.username || userInfo.email || '',
            email: userInfo.email || '',
            groups: userInfo.roles,
            attributes: {
              email: userInfo.email || '',
              username: userInfo.username || ''
            }
          };
          
          setUser(userData);
          setIsAuthenticated(true);
          console.log('User authenticated with roles:', userInfo.roles);
        } else {
          setIsAuthenticated(false);
          setUser(null);
        }
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
    } catch (error) {
      console.error('Authentication initialization failed:', error);
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    // TODO: Implement logout logic with Cognito
    setUser(null);
    setIsAuthenticated(false);
  };

  const hasRole = (role: HDCNGroup): boolean => {
    return user?.groups?.includes(role) || false;
  };

  const refreshUserRoles = async (): Promise<void> => {
    try {
      const roles = await getCurrentUserRoles();
      if (user) {
        setUser({
          ...user,
          groups: roles
        });
      }
    } catch (error) {
      console.error('Failed to refresh user roles:', error);
    }
  };

  return {
    user,
    loading,
    isAuthenticated,
    logout,
    hasRole,
    refreshUserRoles
  };
}
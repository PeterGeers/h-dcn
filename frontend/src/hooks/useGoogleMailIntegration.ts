/**
 * Google Mail Integration Hook for H-DCN Reporting
 * 
 * This hook provides state management and methods for Google Mail integration,
 * including authentication, distribution list creation, and error handling.
 */

import { useState, useEffect, useCallback } from 'react';
import { googleMailService, DistributionListResult, GoogleAuthResult } from '../services/GoogleMailService';
import { Member } from '../types/index';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface GoogleMailState {
  isAuthenticated: boolean;
  isAuthenticating: boolean;
  authUser: {
    email: string;
    name?: string;
    id: string;
  } | null;
  error: string | null;
  lastResult: DistributionListResult | null;
}

export interface GoogleMailActions {
  authenticate: () => Promise<void>;
  handleAuthCallback: (code: string) => Promise<GoogleAuthResult>;
  logout: () => void;
  createDistributionList: (viewName: string, members: Member[], customName?: string) => Promise<DistributionListResult>;
  clearError: () => void;
  clearLastResult: () => void;
}

export interface UseGoogleMailIntegrationReturn extends GoogleMailState, GoogleMailActions {
  availableTemplates: Array<{
    key: string;
    name: string;
    description: string;
    useCase: string;
  }>;
}

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export const useGoogleMailIntegration = (userRoles: string[] = []): UseGoogleMailIntegrationReturn => {
  // State management
  const [state, setState] = useState<GoogleMailState>({
    isAuthenticated: false,
    isAuthenticating: false,
    authUser: null,
    error: null,
    lastResult: null
  });

  // Check authentication status on mount and when service changes
  useEffect(() => {
    const checkAuthStatus = () => {
      const isAuth = googleMailService.isAuthenticated();
      setState(prev => ({
        ...prev,
        isAuthenticated: isAuth
      }));
    };

    checkAuthStatus();
    
    // Set up periodic check for auth status
    const interval = setInterval(checkAuthStatus, 30000); // Check every 30 seconds
    
    return () => clearInterval(interval);
  }, []);

  // ============================================================================
  // AUTHENTICATION METHODS
  // ============================================================================

  const authenticate = useCallback(async (): Promise<void> => {
    try {
      setState(prev => ({ ...prev, isAuthenticating: true, error: null }));
      
      // Initiate OAuth flow
      googleMailService.initiateAuth();
      
      // Note: The actual token exchange happens in handleAuthCallback
      // This method just starts the process
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Authentication failed';
      setState(prev => ({
        ...prev,
        isAuthenticating: false,
        error: errorMessage
      }));
      throw error;
    }
  }, []);

  const handleAuthCallback = useCallback(async (code: string): Promise<GoogleAuthResult> => {
    try {
      setState(prev => ({ ...prev, isAuthenticating: true, error: null }));
      
      const result = await googleMailService.handleAuthCallback(code);
      
      setState(prev => ({
        ...prev,
        isAuthenticated: true,
        isAuthenticating: false,
        authUser: result.user,
        error: null
      }));
      
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Authentication callback failed';
      setState(prev => ({
        ...prev,
        isAuthenticating: false,
        error: errorMessage
      }));
      throw error;
    }
  }, []);

  const logout = useCallback((): void => {
    try {
      googleMailService.logout();
      setState(prev => ({
        ...prev,
        isAuthenticated: false,
        authUser: null,
        error: null,
        lastResult: null
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Logout failed';
      setState(prev => ({ ...prev, error: errorMessage }));
    }
  }, []);

  // ============================================================================
  // DISTRIBUTION LIST METHODS
  // ============================================================================

  const createDistributionList = useCallback(async (
    viewName: string,
    members: Member[],
    customName?: string
  ): Promise<DistributionListResult> => {
    try {
      setState(prev => ({ ...prev, error: null }));
      
      if (!state.isAuthenticated) {
        throw new Error('Not authenticated with Google');
      }
      
      const result = await googleMailService.createDistributionListFromView(
        viewName,
        members,
        customName
      );
      
      setState(prev => ({
        ...prev,
        lastResult: result,
        error: result.success ? null : result.error || 'Creation failed'
      }));
      
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create distribution list';
      const failedResult: DistributionListResult = {
        success: false,
        error: errorMessage
      };
      
      setState(prev => ({
        ...prev,
        lastResult: failedResult,
        error: errorMessage
      }));
      
      return failedResult;
    }
  }, [state.isAuthenticated]);

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  const clearError = useCallback((): void => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const clearLastResult = useCallback((): void => {
    setState(prev => ({ ...prev, lastResult: null }));
  }, []);

  // Get available templates based on user roles
  const availableTemplates = googleMailService.getDistributionListTemplates();

  // ============================================================================
  // RETURN HOOK INTERFACE
  // ============================================================================

  return {
    // State
    isAuthenticated: state.isAuthenticated,
    isAuthenticating: state.isAuthenticating,
    authUser: state.authUser,
    error: state.error,
    lastResult: state.lastResult,
    
    // Actions
    authenticate,
    handleAuthCallback,
    logout,
    createDistributionList,
    clearError,
    clearLastResult,
    
    // Computed values
    availableTemplates
  };
};

// ============================================================================
// ADDITIONAL UTILITY HOOKS
// ============================================================================

/**
 * Hook for handling Google OAuth callback in a dedicated route/component
 */
export const useGoogleAuthCallback = () => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<GoogleAuthResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const processCallback = useCallback(async (code: string) => {
    try {
      setIsProcessing(true);
      setError(null);
      
      const authResult = await googleMailService.handleAuthCallback(code);
      setResult(authResult);
      
      // Close the popup window if it exists
      if (window.opener) {
        window.opener.postMessage({ type: 'GOOGLE_AUTH_SUCCESS', result: authResult }, '*');
        window.close();
      }
      
      return authResult;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Authentication failed';
      setError(errorMessage);
      
      // Notify parent window of error
      if (window.opener) {
        window.opener.postMessage({ type: 'GOOGLE_AUTH_ERROR', error: errorMessage }, '*');
        window.close();
      }
      
      throw err;
    } finally {
      setIsProcessing(false);
    }
  }, []);

  return {
    isProcessing,
    result,
    error,
    processCallback
  };
};

/**
 * Hook for listening to Google Auth popup messages
 */
export const useGoogleAuthListener = (onSuccess?: (result: GoogleAuthResult) => void, onError?: (error: string) => void) => {
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      
      if (event.data.type === 'GOOGLE_AUTH_SUCCESS') {
        onSuccess?.(event.data.result);
      } else if (event.data.type === 'GOOGLE_AUTH_ERROR') {
        onError?.(event.data.error);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [onSuccess, onError]);
};

export default useGoogleMailIntegration;
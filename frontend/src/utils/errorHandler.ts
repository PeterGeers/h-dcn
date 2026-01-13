import { useToast } from '@chakra-ui/react';
import React from 'react';

// Error types for consistent handling
export interface ApiError {
  status: number;
  message: string;
  details?: string;
  isMaintenanceMode?: boolean;
}

// Global maintenance screen state
let maintenanceScreenCallback: ((show: boolean, error?: ApiError) => void) | null = null;

export const setMaintenanceScreenCallback = (callback: (show: boolean, error?: ApiError) => void) => {
  maintenanceScreenCallback = callback;
};

export const showMaintenanceScreen = (error: ApiError) => {
  if (maintenanceScreenCallback) {
    maintenanceScreenCallback(true, error);
  }
};

export const hideMaintenanceScreen = () => {
  if (maintenanceScreenCallback) {
    maintenanceScreenCallback(false);
  }
};

// Standard error messages
export const ERROR_MESSAGES = {
  NETWORK: 'Netwerkfout - controleer je internetverbinding',
  UNAUTHORIZED: 'Je bent niet geautoriseerd voor deze actie',
  FORBIDDEN: 'Toegang geweigerd - onvoldoende rechten',
  NOT_FOUND: 'Gevraagde gegevens niet gevonden',
  SERVER_ERROR: 'Serverfout - probeer het later opnieuw',
  MAINTENANCE: 'Het systeem is tijdelijk niet beschikbaar voor onderhoud',
  VALIDATION: 'Invoergegevens zijn niet correct',
  TIMEOUT: 'Verzoek duurde te lang - probeer opnieuw',
  UNKNOWN: 'Er is een onbekende fout opgetreden'
};

// Parse API response errors
export const parseApiError = async (response: Response): Promise<ApiError> => {
  let message = ERROR_MESSAGES.UNKNOWN;
  let details = '';

  try {
    const errorData = await response.text();
    details = errorData;

    // Try to parse JSON error
    try {
      const jsonError = JSON.parse(errorData);
      message = jsonError.message || jsonError.error || message;
    } catch {
      // Use text as is if not JSON
      message = errorData || message;
    }
  } catch {
    // Fallback to status-based messages
  }

  // Map status codes to user-friendly messages
  switch (response.status) {
    case 400:
      message = ERROR_MESSAGES.VALIDATION;
      break;
    case 401:
      message = ERROR_MESSAGES.UNAUTHORIZED;
      break;
    case 403:
      message = ERROR_MESSAGES.FORBIDDEN;
      break;
    case 404:
      message = ERROR_MESSAGES.NOT_FOUND;
      break;
    case 408:
      message = ERROR_MESSAGES.TIMEOUT;
      break;
    case 500:
    case 502:
    case 504:
      message = ERROR_MESSAGES.SERVER_ERROR;
      break;
    case 503:
      message = ERROR_MESSAGES.MAINTENANCE;
      break;
  }

  return {
    status: response.status,
    message,
    details,
    isMaintenanceMode: response.status === 503
  };
};

// Handle fetch errors (network issues, etc.)
export const handleFetchError = (error: any): ApiError => {
  if (error.name === 'AbortError') {
    return { status: 408, message: ERROR_MESSAGES.TIMEOUT };
  }
  if (error.name === 'TypeError') {
    return { status: 0, message: ERROR_MESSAGES.NETWORK };
  }
  return { status: 0, message: error.message || ERROR_MESSAGES.UNKNOWN };
};

// Standardized error handler hook
export const useErrorHandler = () => {
  const toast = useToast();

  const handleError = (error: ApiError, context?: string) => {
    // Handle 503 maintenance mode specially
    if (error.status === 503 || error.isMaintenanceMode) {
      showMaintenanceScreen(error);
      return; // Don't show toast for maintenance mode
    }

    const title = context ? `Fout bij ${context}` : 'Fout';
    
    toast({
      title,
      description: error.message,
      status: 'error',
      duration: 5000,
      isClosable: true
    });

    // Log for debugging
    console.error(`${title}:`, error);
  };

  const handleSuccess = (message: string, context?: string) => {
    const title = context ? `${context} succesvol` : 'Succesvol';
    
    toast({
      title,
      description: message,
      status: 'success',
      duration: 3000,
      isClosable: true
    });
  };

  return { handleError, handleSuccess };
};

// Wrapper for API calls with standardized error handling
export const apiCall = async <T>(
  fetchPromise: Promise<Response>,
  context?: string
): Promise<T> => {
  try {
    const response = await fetchPromise;
    
    if (!response.ok) {
      const error = await parseApiError(response);
      
      // Handle 503 maintenance mode globally
      if (error.status === 503 || error.isMaintenanceMode) {
        showMaintenanceScreen(error);
      }
      
      throw error;
    }
    
    return await response.json();
  } catch (error: any) {
    if (error.status !== undefined) {
      // Already an ApiError
      throw error;
    }
    // Handle fetch errors
    throw handleFetchError(error);
  }
};

// Global error handler for API responses
export const handleApiError = (error: any) => {
  if (error.response?.status === 503) {
    // Auth system maintenance
    const apiError: ApiError = {
      status: 503,
      message: error.response.data?.message || ERROR_MESSAGES.MAINTENANCE,
      details: error.response.data?.details || '',
      isMaintenanceMode: true
    };
    showMaintenanceScreen(apiError);
    return;
  }
  
  // Handle other errors normally
  console.error('API Error:', error);
};
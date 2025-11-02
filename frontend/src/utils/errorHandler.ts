import { useToast } from '@chakra-ui/react';

// Error types for consistent handling
export interface ApiError {
  status: number;
  message: string;
  details?: string;
}

// Standard error messages
export const ERROR_MESSAGES = {
  NETWORK: 'Netwerkfout - controleer je internetverbinding',
  UNAUTHORIZED: 'Je bent niet geautoriseerd voor deze actie',
  FORBIDDEN: 'Toegang geweigerd - onvoldoende rechten',
  NOT_FOUND: 'Gevraagde gegevens niet gevonden',
  SERVER_ERROR: 'Serverfout - probeer het later opnieuw',
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
    case 503:
    case 504:
      message = ERROR_MESSAGES.SERVER_ERROR;
      break;
  }

  return {
    status: response.status,
    message,
    details
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
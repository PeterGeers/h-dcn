import { useToast } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';

// Error types for consistent handling
export interface ApiError {
  status: number;
  message: string;
  details?: string;
  isMaintenanceMode?: boolean;
  errorKey?: string;
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

// Translated error messages using common namespace
// Replaces the static ERROR_MESSAGES object (Requirement 6.1)
export function getErrorMessages(t: TFunction) {
  return {
    NETWORK: t('errors.network'),
    UNAUTHORIZED: t('errors.unauthorized'),
    FORBIDDEN: t('errors.forbidden'),
    NOT_FOUND: t('errors.not_found'),
    SERVER_ERROR: t('errors.server_error'),
    MAINTENANCE: t('errors.maintenance'),
    TIMEOUT: t('errors.timeout'),
    UNKNOWN: t('errors.unknown'),
  };
}

// Backward-compatible static fallback for code that imports ERROR_MESSAGES directly
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

// Map API error_key to frontend translation (Requirement 6a.1)
export function getApiErrorMessage(t: TFunction, errorKey: string): string {
  return t(`api_errors.${errorKey}`, { defaultValue: '' });
}

// Parse API response errors
// Priority chain: backend `error` field > `message` field > `error_key` lookup > status mapping
export const parseApiError = async (response: Response): Promise<ApiError> => {
  let message = ERROR_MESSAGES.UNKNOWN;
  let details = '';
  let errorKey: string | undefined;
  let backendError: string | undefined;
  let backendMessage: string | undefined;

  try {
    const errorData = await response.text();
    details = errorData;

    // Try to parse JSON error
    try {
      const jsonError = JSON.parse(errorData);
      // Extract error_key from response body (Requirement 6a)
      if (jsonError.error_key) {
        errorKey = jsonError.error_key;
      }
      // Priority: specific backend `error` field first, then `message` field
      backendError = jsonError.error || undefined;
      backendMessage = jsonError.message || undefined;

      // Use backend error (specific detail) first, then message (localized generic)
      if (backendError) {
        message = backendError;
      } else if (backendMessage) {
        message = backendMessage;
      }
    } catch {
      // Use text as is if not JSON
      if (errorData) {
        message = errorData;
      }
    }
  } catch {
    // Fallback to status-based messages
  }

  // Map status codes to user-friendly messages only when no specific backend message was found
  const hasSpecificMessage = !!(backendError || backendMessage);
  if (!hasSpecificMessage) {
    switch (response.status) {
      case 400:
        if (message === ERROR_MESSAGES.UNKNOWN) {
          message = ERROR_MESSAGES.VALIDATION;
        }
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
  }

  return {
    status: response.status,
    message,
    details,
    isMaintenanceMode: response.status === 503,
    errorKey
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

// Standardized error handler hook (Requirement 6.2)
export const useErrorHandler = () => {
  const { t } = useTranslation('common');
  const toast = useToast();

  const handleError = (error: ApiError, context?: string) => {
    // Handle 503 maintenance mode specially
    if (error.status === 503 || error.isMaintenanceMode) {
      showMaintenanceScreen(error);
      return; // Don't show toast for maintenance mode
    }

    // Use translated toast title (Requirement 6.3)
    const title = context
      ? t('notifications.action_error', { action: context })
      : t('labels.error');

    // Priority chain for description:
    // 1. error.details (backend specific `error` field) — already set by parseApiError
    // 2. error.message (backend `message` field or status mapping) — already set by parseApiError
    // 3. error_key lookup via t('api_errors.{errorKey}')
    // 4. Fallback to status-based translated message
    let description = error.message;

    // If message is still the generic unknown fallback, try error_key lookup
    const messages = getErrorMessages(t);
    if (description === ERROR_MESSAGES.UNKNOWN || !description) {
      if (error.errorKey) {
        const keyLookup = getApiErrorMessage(t, error.errorKey);
        if (keyLookup) {
          description = keyLookup;
        }
      }
      // Final fallback: translated unknown error
      if (!description || description === ERROR_MESSAGES.UNKNOWN) {
        description = messages.UNKNOWN;
      }
    }

    toast({
      title,
      description,
      status: 'error',
      duration: 5000,
      isClosable: true
    });

    // Log for debugging
    console.error(`${title}:`, error);
  };

  const handleSuccess = (message: string, context?: string) => {
    // Use translated toast title (Requirement 6.4)
    const title = context
      ? t('notifications.action_success', { action: context })
      : t('labels.success');

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
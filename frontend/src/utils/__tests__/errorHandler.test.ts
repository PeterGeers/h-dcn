/**
 * Error Handler Tests
 * 
 * Comprehensive tests for centralized error handling utilities including
 * 503 maintenance mode detection, API error parsing, and user-friendly
 * error message generation.
 */

import { 
  parseApiError, 
  handleFetchError, 
  handleApiError,
  showMaintenanceScreen,
  hideMaintenanceScreen,
  setMaintenanceScreenCallback,
  ERROR_MESSAGES,
  ApiError
} from '../errorHandler';

// Mock Chakra UI toast
const mockToast = jest.fn();
jest.mock('@chakra-ui/react', () => ({
  useToast: () => mockToast,
}));

describe('Error Handler Utilities', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('parseApiError', () => {
    test('should parse 503 maintenance mode response correctly', async () => {
      const mockResponse = {
        status: 503,
        text: () => Promise.resolve(JSON.stringify({
          message: 'Het authenticatiesysteem is tijdelijk niet beschikbaar voor onderhoud',
          details: 'AUTH_SYSTEM_FAILURE'
        }))
      } as Response;

      const error = await parseApiError(mockResponse);

      expect(error).toEqual({
        status: 503,
        message: ERROR_MESSAGES.MAINTENANCE, // The function overrides with default message for 503
        details: JSON.stringify({
          message: 'Het authenticatiesysteem is tijdelijk niet beschikbaar voor onderhoud',
          details: 'AUTH_SYSTEM_FAILURE'
        }),
        isMaintenanceMode: true
      });
    });

    test('should handle 503 with plain text response', async () => {
      const mockResponse = {
        status: 503,
        text: () => Promise.resolve('Service temporarily unavailable')
      } as Response;

      const error = await parseApiError(mockResponse);

      expect(error).toEqual({
        status: 503,
        message: ERROR_MESSAGES.MAINTENANCE,
        details: 'Service temporarily unavailable',
        isMaintenanceMode: true
      });
    });

    test('should parse 401 unauthorized error', async () => {
      const mockResponse = {
        status: 401,
        text: () => Promise.resolve(JSON.stringify({
          error: 'Invalid JWT token'
        }))
      } as Response;

      const error = await parseApiError(mockResponse);

      expect(error).toEqual({
        status: 401,
        message: ERROR_MESSAGES.UNAUTHORIZED,
        details: JSON.stringify({ error: 'Invalid JWT token' }),
        isMaintenanceMode: false
      });
    });

    test('should parse 403 forbidden error', async () => {
      const mockResponse = {
        status: 403,
        text: () => Promise.resolve('Insufficient permissions')
      } as Response;

      const error = await parseApiError(mockResponse);

      expect(error).toEqual({
        status: 403,
        message: ERROR_MESSAGES.FORBIDDEN,
        details: 'Insufficient permissions',
        isMaintenanceMode: false
      });
    });

    test('should parse 404 not found error', async () => {
      const mockResponse = {
        status: 404,
        text: () => Promise.resolve('')
      } as Response;

      const error = await parseApiError(mockResponse);

      expect(error).toEqual({
        status: 404,
        message: ERROR_MESSAGES.NOT_FOUND,
        details: '',
        isMaintenanceMode: false
      });
    });

    test('should parse 500 server error', async () => {
      const mockResponse = {
        status: 500,
        text: () => Promise.resolve(JSON.stringify({
          message: 'Internal server error',
          stack: 'Error stack trace...'
        }))
      } as Response;

      const error = await parseApiError(mockResponse);

      expect(error).toEqual({
        status: 500,
        message: ERROR_MESSAGES.SERVER_ERROR,
        details: JSON.stringify({
          message: 'Internal server error',
          stack: 'Error stack trace...'
        }),
        isMaintenanceMode: false
      });
    });

    test('should handle response.text() failure gracefully', async () => {
      const mockResponse = {
        status: 500,
        text: () => Promise.reject(new Error('Failed to read response'))
      } as Response;

      const error = await parseApiError(mockResponse);

      expect(error).toEqual({
        status: 500,
        message: ERROR_MESSAGES.SERVER_ERROR,
        details: '',
        isMaintenanceMode: false
      });
    });
  });

  describe('handleFetchError', () => {
    test('should handle AbortError (timeout)', () => {
      const abortError = new Error('Request aborted');
      abortError.name = 'AbortError';

      const error = handleFetchError(abortError);

      expect(error).toEqual({
        status: 408,
        message: ERROR_MESSAGES.TIMEOUT
      });
    });

    test('should handle TypeError (network error)', () => {
      const networkError = new Error('Failed to fetch');
      networkError.name = 'TypeError';

      const error = handleFetchError(networkError);

      expect(error).toEqual({
        status: 0,
        message: ERROR_MESSAGES.NETWORK
      });
    });

    test('should handle generic errors', () => {
      const genericError = new Error('Something went wrong');

      const error = handleFetchError(genericError);

      expect(error).toEqual({
        status: 0,
        message: 'Something went wrong'
      });
    });

    test('should handle errors without message', () => {
      const errorWithoutMessage = { name: 'UnknownError' };

      const error = handleFetchError(errorWithoutMessage);

      expect(error).toEqual({
        status: 0,
        message: ERROR_MESSAGES.UNKNOWN
      });
    });
  });

  describe('handleApiError', () => {
    let mockMaintenanceCallback: jest.Mock;

    beforeEach(() => {
      mockMaintenanceCallback = jest.fn();
      setMaintenanceScreenCallback(mockMaintenanceCallback);
    });

    test('should trigger maintenance screen for 503 errors', () => {
      const error = {
        response: {
          status: 503,
          data: {
            message: 'Authentication system maintenance',
            details: 'AUTH_SYSTEM_FAILURE'
          }
        }
      };

      handleApiError(error);

      expect(mockMaintenanceCallback).toHaveBeenCalledWith(true, {
        status: 503,
        message: 'Authentication system maintenance',
        details: 'AUTH_SYSTEM_FAILURE',
        isMaintenanceMode: true
      });
    });

    test('should use default maintenance message for 503 without data', () => {
      const error = {
        response: {
          status: 503
        }
      };

      handleApiError(error);

      expect(mockMaintenanceCallback).toHaveBeenCalledWith(true, {
        status: 503,
        message: ERROR_MESSAGES.MAINTENANCE,
        details: '',
        isMaintenanceMode: true
      });
    });

    test('should not trigger maintenance screen for non-503 errors', () => {
      const error = {
        response: {
          status: 401,
          data: { message: 'Unauthorized' }
        }
      };

      handleApiError(error);

      expect(mockMaintenanceCallback).not.toHaveBeenCalled();
    });

    test('should handle errors without response property', () => {
      const error = new Error('Network error');

      // Should not crash
      expect(() => handleApiError(error)).not.toThrow();
      expect(mockMaintenanceCallback).not.toHaveBeenCalled();
    });
  });

  describe('Maintenance Screen Callbacks', () => {
    test('should set and call maintenance screen callback', () => {
      const mockCallback = jest.fn();
      setMaintenanceScreenCallback(mockCallback);

      const testError: ApiError = {
        status: 503,
        message: 'Test maintenance',
        isMaintenanceMode: true
      };

      showMaintenanceScreen(testError);

      expect(mockCallback).toHaveBeenCalledWith(true, testError);
    });

    test('should hide maintenance screen', () => {
      const mockCallback = jest.fn();
      setMaintenanceScreenCallback(mockCallback);

      hideMaintenanceScreen();

      expect(mockCallback).toHaveBeenCalledWith(false);
    });

    test('should handle missing callback gracefully', () => {
      setMaintenanceScreenCallback(null as any);

      // Should not crash
      expect(() => showMaintenanceScreen({
        status: 503,
        message: 'Test',
        isMaintenanceMode: true
      })).not.toThrow();

      expect(() => hideMaintenanceScreen()).not.toThrow();
    });
  });

  describe('Error Messages', () => {
    test('should have Dutch error messages', () => {
      expect(ERROR_MESSAGES.NETWORK).toBe('Netwerkfout - controleer je internetverbinding');
      expect(ERROR_MESSAGES.UNAUTHORIZED).toBe('Je bent niet geautoriseerd voor deze actie');
      expect(ERROR_MESSAGES.FORBIDDEN).toBe('Toegang geweigerd - onvoldoende rechten');
      expect(ERROR_MESSAGES.NOT_FOUND).toBe('Gevraagde gegevens niet gevonden');
      expect(ERROR_MESSAGES.SERVER_ERROR).toBe('Serverfout - probeer het later opnieuw');
      expect(ERROR_MESSAGES.MAINTENANCE).toBe('Het systeem is tijdelijk niet beschikbaar voor onderhoud');
      expect(ERROR_MESSAGES.VALIDATION).toBe('Invoergegevens zijn niet correct');
      expect(ERROR_MESSAGES.TIMEOUT).toBe('Verzoek duurde te lang - probeer opnieuw');
      expect(ERROR_MESSAGES.UNKNOWN).toBe('Er is een onbekende fout opgetreden');
    });
  });
});
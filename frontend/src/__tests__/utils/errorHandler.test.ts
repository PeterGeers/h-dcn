/**
 * Unit tests for errorHandler priority chain and i18n integration
 *
 * Tests the error message resolution priority:
 * 1. Backend `error` field (specific detail)
 * 2. Backend `message` field (localized generic)
 * 3. `error_key` lookup via t('api_errors.{errorKey}')
 * 4. Status-based mapping fallback
 *
 * Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6a.1, 6a.2, 6a.3, 6a.5
 */

import {
  parseApiError,
  getErrorMessages,
  getApiErrorMessage,
  handleFetchError,
  ERROR_MESSAGES,
} from '../../utils/errorHandler';
import type { TFunction } from 'i18next';

// Helper: create a mock Response with JSON body
function mockResponse(status: number, body: Record<string, unknown>): Response {
  const bodyStr = JSON.stringify(body);
  return {
    status,
    ok: status >= 200 && status < 300,
    text: () => Promise.resolve(bodyStr),
    json: () => Promise.resolve(body),
    headers: new Headers(),
    redirected: false,
    statusText: '',
    type: 'basic',
    url: '',
    clone: () => mockResponse(status, body),
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
  } as Response;
}

// Helper: create a mock Response with plain text body
function mockTextResponse(status: number, text: string): Response {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: () => Promise.resolve(text),
    headers: new Headers(),
    redirected: false,
    statusText: '',
    type: 'basic',
    url: '',
    clone: () => mockTextResponse(status, text),
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
  } as Response;
}

// Helper: mock TFunction that returns translations from a lookup table
function createMockT(translations: Record<string, string>): TFunction {
  return ((key: string, options?: any) => {
    if (translations[key] !== undefined) {
      return translations[key];
    }
    const defaultValue = options?.defaultValue;
    // If defaultValue is explicitly provided (even empty string), use it
    if (defaultValue !== undefined) {
      return defaultValue;
    }
    // Otherwise return the key itself (i18next default behavior)
    return key;
  }) as unknown as TFunction;
}

describe('errorHandler', () => {
  describe('parseApiError - priority chain', () => {
    it('should use backend `error` field as highest priority', async () => {
      const response = mockResponse(400, {
        error: 'Product naam is verplicht',
        message: 'Validation failed',
        error_key: 'validation_error',
      });

      const result = await parseApiError(response);

      expect(result.message).toBe('Product naam is verplicht');
      expect(result.errorKey).toBe('validation_error');
      expect(result.status).toBe(400);
    });

    it('should use backend `message` field when no `error` field', async () => {
      const response = mockResponse(400, {
        message: 'Ongeldige invoer',
        error_key: 'invalid_input',
      });

      const result = await parseApiError(response);

      expect(result.message).toBe('Ongeldige invoer');
      expect(result.errorKey).toBe('invalid_input');
    });

    it('should extract error_key from response body', async () => {
      const response = mockResponse(404, {
        error_key: 'member_not_found',
        message: 'Lid niet gevonden',
      });

      const result = await parseApiError(response);

      expect(result.errorKey).toBe('member_not_found');
      expect(result.message).toBe('Lid niet gevonden');
    });

    it('should fall back to status-based message when no backend fields', async () => {
      const response = mockResponse(401, {});

      const result = await parseApiError(response);

      expect(result.message).toBe(ERROR_MESSAGES.UNAUTHORIZED);
    });

    it('should map 403 to FORBIDDEN when no backend message', async () => {
      const response = mockResponse(403, {});

      const result = await parseApiError(response);

      expect(result.message).toBe(ERROR_MESSAGES.FORBIDDEN);
    });

    it('should map 404 to NOT_FOUND when no backend message', async () => {
      const response = mockResponse(404, {});

      const result = await parseApiError(response);

      expect(result.message).toBe(ERROR_MESSAGES.NOT_FOUND);
    });

    it('should map 408 to TIMEOUT when no backend message', async () => {
      const response = mockResponse(408, {});

      const result = await parseApiError(response);

      expect(result.message).toBe(ERROR_MESSAGES.TIMEOUT);
    });

    it('should map 500 to SERVER_ERROR when no backend message', async () => {
      const response = mockResponse(500, {});

      const result = await parseApiError(response);

      expect(result.message).toBe(ERROR_MESSAGES.SERVER_ERROR);
    });

    it('should map 502 to SERVER_ERROR when no backend message', async () => {
      const response = mockResponse(502, {});

      const result = await parseApiError(response);

      expect(result.message).toBe(ERROR_MESSAGES.SERVER_ERROR);
    });

    it('should map 503 to MAINTENANCE and set isMaintenanceMode', async () => {
      const response = mockResponse(503, {});

      const result = await parseApiError(response);

      expect(result.message).toBe(ERROR_MESSAGES.MAINTENANCE);
      expect(result.isMaintenanceMode).toBe(true);
    });

    it('should map 504 to SERVER_ERROR when no backend message', async () => {
      const response = mockResponse(504, {});

      const result = await parseApiError(response);

      expect(result.message).toBe(ERROR_MESSAGES.SERVER_ERROR);
    });

    it('should NOT override specific backend error with status mapping', async () => {
      // Even on a 500, if the backend returns an `error` field, use it
      const response = mockResponse(500, {
        error: 'Database connection timeout',
      });

      const result = await parseApiError(response);

      expect(result.message).toBe('Database connection timeout');
      expect(result.message).not.toBe(ERROR_MESSAGES.SERVER_ERROR);
    });

    it('should NOT override specific backend message with status mapping', async () => {
      const response = mockResponse(403, {
        message: 'Je hebt geen toegang tot regio Noord',
      });

      const result = await parseApiError(response);

      expect(result.message).toBe('Je hebt geen toegang tot regio Noord');
      expect(result.message).not.toBe(ERROR_MESSAGES.FORBIDDEN);
    });

    it('should handle non-JSON response text', async () => {
      // When body is non-JSON text, it's set as `message` but since
      // backendError/backendMessage are not set (JSON parse failed),
      // the status-based mapping takes over for known status codes.
      const response = mockTextResponse(500, 'Internal Server Error');

      const result = await parseApiError(response);

      // Status 500 maps to SERVER_ERROR since hasSpecificMessage is false
      expect(result.message).toBe(ERROR_MESSAGES.SERVER_ERROR);
      expect(result.errorKey).toBeUndefined();
    });

    it('should handle empty response body', async () => {
      const response = mockTextResponse(500, '');

      const result = await parseApiError(response);

      expect(result.message).toBe(ERROR_MESSAGES.SERVER_ERROR);
    });

    it('should handle response with only error_key (no error or message)', async () => {
      const response = mockResponse(400, {
        error_key: 'cart_empty',
      });

      const result = await parseApiError(response);

      // No specific message from backend, so fallback to status-based validation message
      expect(result.errorKey).toBe('cart_empty');
      // 400 without a backend message falls through to VALIDATION
      expect(result.message).toBe(ERROR_MESSAGES.VALIDATION);
    });
  });

  describe('getErrorMessages - i18n integration', () => {
    it('should return translated messages from common namespace', () => {
      const t = createMockT({
        'errors.network': 'Network error - check your connection',
        'errors.unauthorized': 'You are not authorized',
        'errors.forbidden': 'Access denied',
        'errors.not_found': 'Not found',
        'errors.server_error': 'Server error - try again later',
        'errors.maintenance': 'System under maintenance',
        'errors.timeout': 'Request timed out',
        'errors.unknown': 'An unknown error occurred',
      });

      const messages = getErrorMessages(t);

      expect(messages.NETWORK).toBe('Network error - check your connection');
      expect(messages.UNAUTHORIZED).toBe('You are not authorized');
      expect(messages.FORBIDDEN).toBe('Access denied');
      expect(messages.NOT_FOUND).toBe('Not found');
      expect(messages.SERVER_ERROR).toBe('Server error - try again later');
      expect(messages.MAINTENANCE).toBe('System under maintenance');
      expect(messages.TIMEOUT).toBe('Request timed out');
      expect(messages.UNKNOWN).toBe('An unknown error occurred');
    });

    it('should return fallback when translations are missing', () => {
      // Our mock t returns the key when no translation found
      // Real i18next returns the key or defaultValue depending on config
      const t = createMockT({}); // Empty translations

      const messages = getErrorMessages(t);

      // Mock returns key for unknown translations (no defaultValue passed in getErrorMessages)
      expect(messages.NETWORK).toBe('errors.network');
      expect(messages.UNAUTHORIZED).toBe('errors.unauthorized');
    });
  });

  describe('getApiErrorMessage - error_key lookup', () => {
    it('should look up api_errors.{errorKey} from common namespace', () => {
      const t = createMockT({
        'api_errors.member_not_found': 'Member not found',
        'api_errors.validation_error': 'Invalid input data',
        'api_errors.forbidden': 'Insufficient permissions',
      });

      expect(getApiErrorMessage(t, 'member_not_found')).toBe('Member not found');
      expect(getApiErrorMessage(t, 'validation_error')).toBe('Invalid input data');
      expect(getApiErrorMessage(t, 'forbidden')).toBe('Insufficient permissions');
    });

    it('should return empty string for unknown error keys', () => {
      const t = createMockT({});

      // defaultValue is '' so unknown keys return empty string
      expect(getApiErrorMessage(t, 'nonexistent_key')).toBe('');
    });

    it('should handle all 15 expected backend error keys', () => {
      const expectedKeys = [
        'authorization_required',
        'forbidden',
        'not_found',
        'validation_error',
        'internal_error',
        'member_not_found',
        'member_already_exists',
        'invalid_input',
        'payment_failed',
        'order_not_found',
        'product_not_found',
        'cart_empty',
        'insufficient_stock',
        'email_already_exists',
        'invalid_membership',
      ];

      const translations: Record<string, string> = {};
      expectedKeys.forEach((key) => {
        translations[`api_errors.${key}`] = `Translated: ${key}`;
      });

      const t = createMockT(translations);

      for (const key of expectedKeys) {
        expect(getApiErrorMessage(t, key)).toBe(`Translated: ${key}`);
      }
    });
  });

  describe('handleFetchError', () => {
    it('should return TIMEOUT for AbortError', () => {
      const error = new Error('The operation was aborted');
      error.name = 'AbortError';

      const result = handleFetchError(error);

      expect(result.status).toBe(408);
      expect(result.message).toBe(ERROR_MESSAGES.TIMEOUT);
    });

    it('should return NETWORK for TypeError (fetch failure)', () => {
      const error = new TypeError('Failed to fetch');

      const result = handleFetchError(error);

      expect(result.status).toBe(0);
      expect(result.message).toBe(ERROR_MESSAGES.NETWORK);
    });

    it('should use error.message for other error types', () => {
      const error = new Error('Custom error message');

      const result = handleFetchError(error);

      expect(result.status).toBe(0);
      expect(result.message).toBe('Custom error message');
    });

    it('should return UNKNOWN when error has no message', () => {
      const error = { name: 'SomeError' };

      const result = handleFetchError(error);

      expect(result.message).toBe(ERROR_MESSAGES.UNKNOWN);
    });
  });

  describe('Priority chain property: specific error preferred over generic', () => {
    // Property 7: Error message priority — specific error preferred over generic message
    // Validates: Requirements 6a.2, 6a.3, 6a.5

    it('error field always wins over message field', async () => {
      const testCases = [
        { error: 'Specific error A', message: 'Generic message A' },
        { error: 'Prijs moet groter zijn dan 0', message: 'Validation failed' },
        { error: 'Lid bestaat al met dit e-mailadres', message: 'Conflict' },
      ];

      for (const tc of testCases) {
        const response = mockResponse(400, tc);
        const result = await parseApiError(response);
        expect(result.message).toBe(tc.error);
      }
    });

    it('message field wins over status-based fallback', async () => {
      const statusCodes = [400, 401, 403, 404, 500, 502, 503, 504];

      for (const status of statusCodes) {
        const customMessage = `Custom message for ${status}`;
        const response = mockResponse(status, { message: customMessage });
        const result = await parseApiError(response);
        expect(result.message).toBe(customMessage);
      }
    });

    it('status-based fallback used only when no backend fields present', async () => {
      const statusMappings: [number, string][] = [
        [401, ERROR_MESSAGES.UNAUTHORIZED],
        [403, ERROR_MESSAGES.FORBIDDEN],
        [404, ERROR_MESSAGES.NOT_FOUND],
        [408, ERROR_MESSAGES.TIMEOUT],
        [500, ERROR_MESSAGES.SERVER_ERROR],
        [503, ERROR_MESSAGES.MAINTENANCE],
      ];

      for (const [status, expectedMessage] of statusMappings) {
        const response = mockResponse(status, {});
        const result = await parseApiError(response);
        expect(result.message).toBe(expectedMessage);
      }
    });
  });
});

/**
 * Unit tests for errorHandler priority chain.
 *
 * Feature: i18n-error-messages
 * Property 7: Error message priority — specific error preferred over generic message
 * **Validates: Requirements 6a.2, 6a.3, 6a.5**
 *
 * Tests the priority chain in parseApiError and useErrorHandler:
 * 1. Backend `error` field (specific detail) → displayed directly
 * 2. Backend `message` field (localized generic) → fallback when no `error`
 * 3. `error_key` → frontend lookup via t('api_errors.{error_key}')
 * 4. HTTP status code → generic errors.* mapping
 */

import * as fc from 'fast-check';
import { parseApiError, getErrorMessages, getApiErrorMessage, ERROR_MESSAGES } from '../../utils/errorHandler';

// ---------- Helper: create a mock Response ----------

function createMockResponse(status: number, body?: object | string): Response {
  const bodyStr = body !== undefined
    ? (typeof body === 'string' ? body : JSON.stringify(body))
    : '';

  return {
    status,
    ok: status >= 200 && status < 300,
    statusText: '',
    headers: new Headers(),
    redirected: false,
    type: 'basic',
    url: '',
    clone: () => createMockResponse(status, body),
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    json: () => Promise.resolve(typeof body === 'object' ? body : JSON.parse(bodyStr)),
    text: () => Promise.resolve(bodyStr),
    bytes: () => Promise.resolve(new Uint8Array()),
  } as Response;
}

// ---------- parseApiError unit tests ----------

describe('parseApiError - priority chain', () => {
  it('response with specific `error` field displays it directly (priority 1)', async () => {
    const response = createMockResponse(400, {
      error: 'Specific detail: field X is invalid',
      error_key: 'validation_error',
      message: 'Generic validation error',
    });

    const result = await parseApiError(response);

    expect(result.message).toBe('Specific detail: field X is invalid');
    expect(result.errorKey).toBe('validation_error');
  });

  it('response with `message` but no `error` uses `message` (priority 2)', async () => {
    const response = createMockResponse(400, {
      message: 'Backend localized message',
      error_key: 'validation_error',
    });

    const result = await parseApiError(response);

    expect(result.message).toBe('Backend localized message');
    expect(result.errorKey).toBe('validation_error');
  });

  it('response with `error_key` only sets errorKey for frontend lookup (priority 3)', async () => {
    const response = createMockResponse(400, {
      error_key: 'member_not_found',
    });

    const result = await parseApiError(response);

    expect(result.errorKey).toBe('member_not_found');
  });

  it('response with 401 status and no body falls back to UNAUTHORIZED message (priority 4)', async () => {
    const response = createMockResponse(401, '');

    const result = await parseApiError(response);

    expect(result.message).toBe(ERROR_MESSAGES.UNAUTHORIZED);
    expect(result.status).toBe(401);
  });

  it('response with 403 status and no body falls back to FORBIDDEN message', async () => {
    const response = createMockResponse(403, '');

    const result = await parseApiError(response);

    expect(result.message).toBe(ERROR_MESSAGES.FORBIDDEN);
  });

  it('response with 404 status and no body falls back to NOT_FOUND message', async () => {
    const response = createMockResponse(404, '');

    const result = await parseApiError(response);

    expect(result.message).toBe(ERROR_MESSAGES.NOT_FOUND);
  });

  it('response with 500 status and no body falls back to SERVER_ERROR message', async () => {
    const response = createMockResponse(500, '');

    const result = await parseApiError(response);

    expect(result.message).toBe(ERROR_MESSAGES.SERVER_ERROR);
  });

  it('response with 503 status sets isMaintenanceMode', async () => {
    const response = createMockResponse(503, '');

    const result = await parseApiError(response);

    expect(result.isMaintenanceMode).toBe(true);
    expect(result.message).toBe(ERROR_MESSAGES.MAINTENANCE);
  });

  it('specific error takes precedence over status code mapping', async () => {
    const response = createMockResponse(401, {
      error: 'Your session expired, please log in again',
    });

    const result = await parseApiError(response);

    // Should use the specific error, not the generic UNAUTHORIZED fallback
    expect(result.message).toBe('Your session expired, please log in again');
  });

  it('message takes precedence over status code mapping when error is absent', async () => {
    const response = createMockResponse(403, {
      message: 'Toegang geweigerd voor regio Noord',
    });

    const result = await parseApiError(response);

    // Should use backend message, not generic FORBIDDEN
    expect(result.message).toBe('Toegang geweigerd voor regio Noord');
  });
});

// ---------- getErrorMessages unit tests ----------

describe('getErrorMessages - translated error mapping', () => {
  const mockT = ((key: string, _opts?: any): string => {
    return `translated:${key}`;
  }) as any;

  it('returns translated messages for all error types', () => {
    const messages = getErrorMessages(mockT);

    expect(messages.NETWORK).toBe('translated:errors.network');
    expect(messages.UNAUTHORIZED).toBe('translated:errors.unauthorized');
    expect(messages.FORBIDDEN).toBe('translated:errors.forbidden');
    expect(messages.NOT_FOUND).toBe('translated:errors.not_found');
    expect(messages.SERVER_ERROR).toBe('translated:errors.server_error');
    expect(messages.MAINTENANCE).toBe('translated:errors.maintenance');
    expect(messages.TIMEOUT).toBe('translated:errors.timeout');
    expect(messages.UNKNOWN).toBe('translated:errors.unknown');
  });
});

// ---------- getApiErrorMessage unit tests ----------

describe('getApiErrorMessage - error_key lookup', () => {
  const mockT = ((key: string, opts?: any): string => {
    // Simulate i18next: return translated value for known keys, defaultValue for unknown
    const known: Record<string, string> = {
      'api_errors.member_not_found': 'Lid niet gevonden',
      'api_errors.validation_error': 'Validatiefout',
      'api_errors.payment_failed': 'Betaling mislukt',
    };
    return known[key] || opts?.defaultValue || '';
  }) as any;

  it('returns translated message for known error_key', () => {
    expect(getApiErrorMessage(mockT, 'member_not_found')).toBe('Lid niet gevonden');
    expect(getApiErrorMessage(mockT, 'validation_error')).toBe('Validatiefout');
    expect(getApiErrorMessage(mockT, 'payment_failed')).toBe('Betaling mislukt');
  });

  it('returns empty string for unknown error_key (defaultValue fallback)', () => {
    expect(getApiErrorMessage(mockT, 'unknown_key_xyz')).toBe('');
  });
});

// ---------- useErrorHandler hook tests ----------

const mockToast = jest.fn();

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any): string => {
      if (key === 'notifications.action_error' && opts?.action) {
        return `Fout bij ${opts.action}`;
      }
      if (key === 'notifications.action_success' && opts?.action) {
        return `${opts.action} succesvol`;
      }
      if (key === 'labels.error') return 'Fout';
      if (key === 'labels.success') return 'Succes';
      if (key.startsWith('api_errors.')) {
        const errorKey = key.replace('api_errors.', '');
        const translations: Record<string, string> = {
          member_not_found: 'Lid niet gevonden',
          validation_error: 'Validatiefout',
        };
        return translations[errorKey] || opts?.defaultValue || '';
      }
      if (key.startsWith('errors.')) {
        return `translated:${key}`;
      }
      return key;
    },
    i18n: { language: 'nl' },
  }),
}));

jest.mock('@chakra-ui/react', () => ({
  useToast: () => mockToast,
}));

// Import after mocks are set up
import { useErrorHandler } from '../../utils/errorHandler';
import { renderHook } from '@testing-library/react';

describe('useErrorHandler hook', () => {
  beforeEach(() => {
    mockToast.mockClear();
  });

  it('handleError uses t("notifications.action_error", { action }) for toast title', () => {
    const { result } = renderHook(() => useErrorHandler());

    result.current.handleError(
      { status: 400, message: 'Something went wrong' },
      'leden bijwerken'
    );

    expect(mockToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Fout bij leden bijwerken',
        status: 'error',
      })
    );
  });

  it('handleSuccess uses t("notifications.action_success", { action }) for toast title', () => {
    const { result } = renderHook(() => useErrorHandler());

    result.current.handleSuccess('Product bijgewerkt', 'product opslaan');

    expect(mockToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'product opslaan succesvol',
        description: 'Product bijgewerkt',
        status: 'success',
      })
    );
  });

  it('handleError without context uses t("labels.error") as title', () => {
    const { result } = renderHook(() => useErrorHandler());

    result.current.handleError({ status: 400, message: 'Validation failed' });

    expect(mockToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Fout',
        status: 'error',
      })
    );
  });

  it('handleSuccess without context uses t("labels.success") as title', () => {
    const { result } = renderHook(() => useErrorHandler());

    result.current.handleSuccess('Opgeslagen');

    expect(mockToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Succes',
        description: 'Opgeslagen',
        status: 'success',
      })
    );
  });

  it('handleError does not show toast for 503 maintenance mode', () => {
    const { result } = renderHook(() => useErrorHandler());

    result.current.handleError({
      status: 503,
      message: 'Maintenance',
      isMaintenanceMode: true,
    });

    // Should NOT show a toast — maintenance mode is handled via the maintenance screen
    expect(mockToast).not.toHaveBeenCalled();
  });
});

// ---------- Property 7: Error message priority ----------

describe('Property 7: Error message priority — specific error preferred over generic message', () => {
  /**
   * **Validates: Requirements 6a.2, 6a.3, 6a.5**
   *
   * Property 7: For any API error response containing both an `error` field
   * (specific detail) and a `message` field (generic localized), the error
   * handler SHALL display the `error` field directly. Only when `error` is
   * absent or empty SHALL it fall back to `message`.
   */
  it('when both error and message are present, error is preferred', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom(400, 401, 403, 404, 500),
        fc.string({ minLength: 1, maxLength: 200 }),
        fc.string({ minLength: 1, maxLength: 200 }).filter(s => s !== ''),
        async (status, errorStr, messageStr) => {
          // Use a suffix to guarantee they differ
          const distinctMessage = messageStr + '__msg';

          const response = createMockResponse(status, {
            error: errorStr,
            message: distinctMessage,
          });

          const result = await parseApiError(response);

          // error field takes priority over message (even if error is non-empty)
          if (errorStr.length > 0) {
            return result.message === errorStr;
          }
          // empty error string falls through to message
          return result.message === distinctMessage;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 6a.2, 6a.3, 6a.5**
   *
   * When `error` is absent, the `message` field is used as fallback.
   */
  it('when error is absent, message is used as fallback', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom(400, 401, 403, 404, 500),
        fc.string({ minLength: 1, maxLength: 200 }),
        async (status, messageStr) => {
          const response = createMockResponse(status, {
            message: messageStr,
          });

          const result = await parseApiError(response);

          // message is used when error is absent
          return result.message === messageStr;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 6a.2, 6a.3, 6a.5**
   *
   * When error is empty string, message is used as fallback.
   */
  it('when error is empty string, message is used as fallback', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom(400, 401, 403, 404, 500),
        fc.string({ minLength: 1, maxLength: 200 }),
        async (status, messageStr) => {
          const response = createMockResponse(status, {
            error: '',
            message: messageStr,
          });

          const result = await parseApiError(response);

          // empty error falls through to message
          return result.message === messageStr;
        }
      ),
      { numRuns: 100 }
    );
  });
});

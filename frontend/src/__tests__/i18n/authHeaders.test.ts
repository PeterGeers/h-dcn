/**
 * Unit tests for Accept-Language header in getAuthHeaders.
 *
 * Validates: Requirement 6.1 — Frontend sends active locale as
 * Accept-Language header in API requests.
 */

import { getAuthHeaders, getAuthHeadersForGet } from '../../utils/authHeaders';

// --- Mocks ---

let mockLanguage = 'nl';

jest.mock('../../i18n', () => ({
  get language() {
    return mockLanguage;
  },
}));

const mockFetchAuthSession = jest.fn();

jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: () => mockFetchAuthSession(),
}));

// --- Helpers ---

function createMockSession(overrides?: {
  token?: string | null;
  groups?: string[];
  email?: string;
}) {
  const token = overrides?.token !== undefined ? overrides.token : 'mock-access-token';
  const groups = overrides?.groups ?? ['hdcnLeden'];
  const email = overrides?.email ?? 'test@example.com';

  return {
    tokens: token
      ? {
          accessToken: {
            toString: () => token,
            payload: {
              'cognito:groups': groups,
            },
          },
          idToken: {
            payload: {
              email,
            },
          },
        }
      : undefined,
  };
}

// --- Tests ---

describe('getAuthHeaders — Accept-Language header', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLanguage = 'nl';
    mockFetchAuthSession.mockResolvedValue(createMockSession());
  });

  describe('includes Accept-Language with active locale (Req 6.1)', () => {
    it('includes Accept-Language header set to the active i18n locale', async () => {
      mockLanguage = 'en';
      const headers = await getAuthHeaders();
      expect(headers['Accept-Language']).toBe('en');
    });

    it('defaults to nl when i18n language is nl', async () => {
      mockLanguage = 'nl';
      const headers = await getAuthHeaders();
      expect(headers['Accept-Language']).toBe('nl');
    });

    it.each(['fr', 'de', 'sv', 'da', 'it', 'es'])(
      'sends Accept-Language: %s when locale is %s',
      async (locale) => {
        mockLanguage = locale;
        const headers = await getAuthHeaders();
        expect(headers['Accept-Language']).toBe(locale);
      }
    );
  });

  describe('getAuthHeadersForGet also includes Accept-Language', () => {
    it('includes Accept-Language header in GET request headers', async () => {
      mockLanguage = 'fr';
      const headers = await getAuthHeadersForGet();
      expect(headers['Accept-Language']).toBe('fr');
    });

    it('reflects the current i18n language for GET requests', async () => {
      mockLanguage = 'de';
      const headers = await getAuthHeadersForGet();
      expect(headers['Accept-Language']).toBe('de');
    });
  });

  describe('other headers remain correct', () => {
    it('includes Authorization Bearer token', async () => {
      const headers = await getAuthHeaders();
      expect(headers['Authorization']).toBe('Bearer mock-access-token');
    });

    it('includes Content-Type for POST headers', async () => {
      const headers = await getAuthHeaders();
      expect(headers['Content-Type']).toBe('application/json');
    });

    it('does not include Content-Type for GET headers', async () => {
      const headers = await getAuthHeadersForGet();
      expect(headers['Content-Type']).toBeUndefined();
    });

    it('includes X-User-Email when available', async () => {
      const headers = await getAuthHeaders();
      expect(headers['X-User-Email']).toBe('test@example.com');
    });

    it('includes X-Enhanced-Groups with valid roles', async () => {
      mockFetchAuthSession.mockResolvedValue(
        createMockSession({ groups: ['hdcnLeden', 'Regio_Noord'] })
      );
      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);
      expect(groups).toContain('hdcnLeden');
      expect(groups).toContain('Regio_Noord');
    });
  });

  describe('error handling', () => {
    it('throws when not authenticated (no token)', async () => {
      mockFetchAuthSession.mockResolvedValue(createMockSession({ token: null }));
      await expect(getAuthHeaders()).rejects.toThrow('Not authenticated');
    });
  });
});

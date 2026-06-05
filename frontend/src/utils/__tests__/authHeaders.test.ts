/**
 * Unit tests for authHeaders utility — Accept-Language header inclusion.
 *
 * Validates that getAuthHeaders and getAuthHeadersForGet include the
 * Accept-Language header set to the active i18n locale.
 *
 * Requirements: 6.1
 */

import { getAuthHeaders, getAuthHeadersForGet } from '../authHeaders';

// Mock aws-amplify/auth
jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: jest.fn(),
}));

// Mock the i18n module
jest.mock('../../i18n', () => ({
  __esModule: true,
  default: {
    language: 'nl',
  },
}));

import { fetchAuthSession } from 'aws-amplify/auth';
import i18n from '../../i18n';

const mockFetchAuthSession = fetchAuthSession as jest.MockedFunction<typeof fetchAuthSession>;

/** Creates a mock session with valid tokens */
function createMockSession(groups: string[] = ['hdcnLeden'], email = 'user@test.nl') {
  return {
    tokens: {
      accessToken: {
        toString: () => 'mock-access-token',
        payload: {
          'cognito:groups': groups,
        },
      },
      idToken: {
        payload: {
          email,
        },
      },
    },
  };
}

describe('getAuthHeaders — Accept-Language header', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetchAuthSession.mockResolvedValue(createMockSession());
    // Reset to default locale
    (i18n as any).language = 'nl';
  });

  it('includes Accept-Language header with the active i18n locale', async () => {
    (i18n as any).language = 'en';

    const headers = await getAuthHeaders();

    expect(headers['Accept-Language']).toBe('en');
  });

  it('uses Dutch locale when i18n.language is nl', async () => {
    (i18n as any).language = 'nl';

    const headers = await getAuthHeaders();

    expect(headers['Accept-Language']).toBe('nl');
  });

  it('reflects locale changes across supported locales', async () => {
    const locales = ['fr', 'de', 'sv', 'da', 'it', 'es'];

    for (const locale of locales) {
      (i18n as any).language = locale;
      const headers = await getAuthHeaders();
      expect(headers['Accept-Language']).toBe(locale);
    }
  });

  it('includes Accept-Language alongside other required headers', async () => {
    (i18n as any).language = 'fr';

    const headers = await getAuthHeaders();

    expect(headers).toHaveProperty('Content-Type', 'application/json');
    expect(headers).toHaveProperty('Authorization', 'Bearer mock-access-token');
    expect(headers).toHaveProperty('Accept-Language', 'fr');
  });
});

describe('getAuthHeadersForGet — Accept-Language header', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetchAuthSession.mockResolvedValue(createMockSession());
    (i18n as any).language = 'nl';
  });

  it('includes Accept-Language header with the active i18n locale', async () => {
    (i18n as any).language = 'de';

    const headers = await getAuthHeadersForGet();

    expect(headers['Accept-Language']).toBe('de');
  });

  it('does not include Content-Type header (GET requests)', async () => {
    const headers = await getAuthHeadersForGet();

    expect(headers).not.toHaveProperty('Content-Type');
    expect(headers).toHaveProperty('Authorization');
    expect(headers).toHaveProperty('Accept-Language', 'nl');
  });

  it('reflects the current i18n language at call time', async () => {
    (i18n as any).language = 'sv';
    const headers1 = await getAuthHeadersForGet();
    expect(headers1['Accept-Language']).toBe('sv');

    (i18n as any).language = 'it';
    const headers2 = await getAuthHeadersForGet();
    expect(headers2['Accept-Language']).toBe('it');
  });
});

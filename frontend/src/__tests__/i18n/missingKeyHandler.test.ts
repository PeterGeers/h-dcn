/**
 * Unit tests for missing key handler and namespace loading.
 *
 * Validates: Requirements 10.5, 10.6, 4.5
 *
 * Tests:
 * 1. Console warning output format when keys are missing (requirement 10.5)
 * 2. Empty string values trigger Dutch fallback (requirement 10.6)
 * 3. Failed namespace load falls back to Dutch (requirement 4.5)
 */

import i18next, { i18n as I18nInstance } from 'i18next';
import HttpBackend from 'i18next-http-backend';
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from '../../i18n/constants';

// ---------- Helpers ----------

/**
 * Creates a test i18next instance with in-memory resources and
 * the same missing key handler configuration as production.
 */
async function createTestInstance(
  resources: Record<string, Record<string, Record<string, string>>>,
  options: { isDevelopment?: boolean } = {}
): Promise<I18nInstance> {
  const { isDevelopment = true } = options;
  const instance = i18next.createInstance();

  await instance.init({
    fallbackLng: DEFAULT_LOCALE,
    supportedLngs: [...SUPPORTED_LOCALES],
    lng: DEFAULT_LOCALE,
    ns: ['common'],
    defaultNS: 'common',
    resources,
    react: { useSuspense: false },
    interpolation: { escapeValue: false },
    returnEmptyString: false,
    parseMissingKeyHandler: (key: string) => key,
    saveMissing: isDevelopment,
    missingKeyHandler: (lngs, ns, key) => {
      if (isDevelopment) {
        console.warn(
          `[i18n] Missing key: locale=${lngs}, namespace=${ns}, key="${key}"`
        );
      }
    },
    initImmediate: false,
  });

  return instance;
}

/**
 * Creates an i18next instance with HTTP backend and custom request function
 * (matching production config) for testing namespace load failures.
 */
async function createHttpBackendInstance(
  fetchMock: jest.Mock
): Promise<I18nInstance> {
  const instance = i18next.createInstance();

  await instance.use(HttpBackend).init({
    fallbackLng: DEFAULT_LOCALE,
    supportedLngs: [...SUPPORTED_LOCALES],
    lng: 'en',
    ns: ['common'],
    defaultNS: 'common',
    react: { useSuspense: false },
    interpolation: { escapeValue: false },
    returnEmptyString: false,
    parseMissingKeyHandler: (key: string) => key,
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
      request: (_options: unknown, url: string, _payload: unknown, callback: Function) => {
        const fetchResult = fetchMock(url);

        if (fetchResult instanceof Promise) {
          fetchResult
            .then((response: { ok: boolean; status: number; json: () => Promise<unknown> }) => {
              if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
              }
              return response.json();
            })
            .then((data: unknown) => {
              callback(null, { status: 200, data: JSON.stringify(data) });
            })
            .catch(() => {
              // Extract locale from URL
              const localeMatch = (url as string).match(/\/locales\/([^/]+)\//);
              const locale = localeMatch ? localeMatch[1] : '';

              if (locale !== DEFAULT_LOCALE) {
                // Non-Dutch locale failed: attempt Dutch fallback
                const fallbackUrl = (url as string).replace(
                  `/locales/${locale}/`,
                  `/locales/${DEFAULT_LOCALE}/`
                );
                const fallbackResult = fetchMock(fallbackUrl);

                if (fallbackResult instanceof Promise) {
                  fallbackResult
                    .then((response: { ok: boolean; status: number; json: () => Promise<unknown> }) => {
                      if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                      }
                      return response.json();
                    })
                    .then((data: unknown) => {
                      callback(null, { status: 200, data: JSON.stringify(data) });
                    })
                    .catch(() => {
                      callback(null, { status: 200, data: '{}' });
                    });
                }
              } else {
                callback(null, { status: 200, data: '{}' });
              }
            });
        }
      },
    },
    initImmediate: false,
  });

  return instance;
}

// ---------- Tests ----------

describe('Missing Key Handler - Console Warning Format (Requirement 10.5)', () => {
  let consoleSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  it('logs warning with correct format: [i18n] Missing key: locale=..., namespace=..., key="..."', async () => {
    const resources = {
      nl: { common: { greeting: 'Hallo' } },
      en: { common: {} },
    };

    const instance = await createTestInstance(resources, { isDevelopment: true });
    await instance.changeLanguage('en');

    // Access a key that doesn't exist in English (but exists in Dutch)
    instance.t('nonexistent_key');

    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringMatching(
        /\[i18n\] Missing key: locale=.*?, namespace=common, key="nonexistent_key"/
      )
    );
  });

  it('includes the correct locale in the warning message', async () => {
    const resources = {
      nl: { common: { title: 'Titel' } },
      fr: { common: {} },
    };

    const instance = await createTestInstance(resources, { isDevelopment: true });
    await instance.changeLanguage('fr');

    instance.t('missing_key_test');

    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('locale=')
    );
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('key="missing_key_test"')
    );
  });

  it('includes the correct namespace in the warning message', async () => {
    const resources = {
      nl: { common: { nav_home: 'Thuis' } },
      de: { common: {} },
    };

    const instance = await createTestInstance(resources, { isDevelopment: true });
    await instance.changeLanguage('de');

    instance.t('nav_home_missing');

    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('namespace=common')
    );
  });

  it('does NOT log warning when not in development mode', async () => {
    const resources = {
      nl: { common: { greeting: 'Hallo' } },
      en: { common: {} },
    };

    const instance = await createTestInstance(resources, { isDevelopment: false });
    await instance.changeLanguage('en');

    instance.t('nonexistent_key');

    expect(consoleSpy).not.toHaveBeenCalled();
  });

  it('does NOT log warning when key exists in the active locale', async () => {
    const resources = {
      nl: { common: { greeting: 'Hallo' } },
      en: { common: { greeting: 'Hello' } },
    };

    const instance = await createTestInstance(resources, { isDevelopment: true });
    await instance.changeLanguage('en');

    instance.t('greeting');

    expect(consoleSpy).not.toHaveBeenCalled();
  });
});

describe('Empty String Values Trigger Dutch Fallback (Requirement 10.6)', () => {
  it('returns Dutch value when locale translation is empty string', async () => {
    const resources = {
      nl: { common: { welcome: 'Welkom' } },
      en: { common: { welcome: '' } },
    };

    const instance = await createTestInstance(resources);
    await instance.changeLanguage('en');

    expect(instance.t('welcome')).toBe('Welkom');
  });

  it('returns Dutch value when multiple keys have empty strings', async () => {
    const resources = {
      nl: { common: { title: 'Titel', subtitle: 'Ondertitel' } },
      fr: { common: { title: '', subtitle: '' } },
    };

    const instance = await createTestInstance(resources);
    await instance.changeLanguage('fr');

    expect(instance.t('title')).toBe('Titel');
    expect(instance.t('subtitle')).toBe('Ondertitel');
  });

  it('returns key string when both locale and Dutch have empty strings', async () => {
    const resources = {
      nl: { common: { orphan_key: '' } },
      sv: { common: { orphan_key: '' } },
    };

    const instance = await createTestInstance(resources);
    await instance.changeLanguage('sv');

    expect(instance.t('orphan_key')).toBe('orphan_key');
  });

  it('returns locale value when it is non-empty (no fallback needed)', async () => {
    const resources = {
      nl: { common: { greeting: 'Hallo' } },
      es: { common: { greeting: 'Hola' } },
    };

    const instance = await createTestInstance(resources);
    await instance.changeLanguage('es');

    expect(instance.t('greeting')).toBe('Hola');
  });

  it('treats whitespace-only value as non-empty (not treated as missing)', async () => {
    const resources = {
      nl: { common: { spacer: 'NL spacer' } },
      it: { common: { spacer: ' ' } },
    };

    const instance = await createTestInstance(resources);
    await instance.changeLanguage('it');

    // Whitespace is not empty string, so it should be returned as-is
    expect(instance.t('spacer')).toBe(' ');
  });
});

describe('Failed Namespace Load Falls Back to Dutch (Requirement 4.5)', () => {
  let fetchMock: jest.Mock;

  beforeEach(() => {
    fetchMock = jest.fn();
  });

  it('loads Dutch namespace when non-Dutch locale namespace fails', async () => {
    const dutchTranslations = { greeting: 'Hallo', farewell: 'Tot ziens' };

    fetchMock.mockImplementation((url: string) => {
      if (url.includes('/locales/en/')) {
        // English namespace fails
        return Promise.resolve({ ok: false, status: 404, json: () => Promise.reject() });
      }
      if (url.includes('/locales/nl/')) {
        // Dutch namespace succeeds
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(dutchTranslations) });
      }
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.reject() });
    });

    const instance = await createHttpBackendInstance(fetchMock);

    // Wait for loading to complete
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Verify Dutch fallback was attempted
    const nlCalls = fetchMock.mock.calls.filter(
      (call: string[]) => call[0].includes('/locales/nl/')
    );
    expect(nlCalls.length).toBeGreaterThan(0);
  });

  it('returns Dutch translations after non-Dutch locale load failure', async () => {
    const dutchTranslations = { page_title: 'Dashboard' };

    fetchMock.mockImplementation((url: string) => {
      if (url.includes('/locales/fr/')) {
        return Promise.resolve({ ok: false, status: 500, json: () => Promise.reject() });
      }
      if (url.includes('/locales/nl/')) {
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(dutchTranslations) });
      }
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.reject() });
    });

    const instance = i18next.createInstance();
    await instance.use(HttpBackend).init({
      fallbackLng: DEFAULT_LOCALE,
      supportedLngs: [...SUPPORTED_LOCALES],
      lng: 'fr',
      ns: ['common'],
      defaultNS: 'common',
      react: { useSuspense: false },
      interpolation: { escapeValue: false },
      returnEmptyString: false,
      parseMissingKeyHandler: (key: string) => key,
      backend: {
        loadPath: '/locales/{{lng}}/{{ns}}.json',
        request: (_options: unknown, url: string, _payload: unknown, callback: Function) => {
          fetchMock(url)
            .then((response: { ok: boolean; status: number; json: () => Promise<unknown> }) => {
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              return response.json();
            })
            .then((data: unknown) => {
              callback(null, { status: 200, data: JSON.stringify(data) });
            })
            .catch(() => {
              const localeMatch = (url as string).match(/\/locales\/([^/]+)\//);
              const locale = localeMatch ? localeMatch[1] : '';

              if (locale !== DEFAULT_LOCALE) {
                const fallbackUrl = (url as string).replace(
                  `/locales/${locale}/`,
                  `/locales/${DEFAULT_LOCALE}/`
                );
                fetchMock(fallbackUrl)
                  .then((resp: { ok: boolean; status: number; json: () => Promise<unknown> }) => {
                    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                    return resp.json();
                  })
                  .then((data: unknown) => {
                    callback(null, { status: 200, data: JSON.stringify(data) });
                  })
                  .catch(() => {
                    callback(null, { status: 200, data: '{}' });
                  });
              } else {
                callback(null, { status: 200, data: '{}' });
              }
            });
        },
      },
      initImmediate: false,
    });

    // Wait for async loading
    await new Promise((resolve) => setTimeout(resolve, 150));

    expect(instance.t('page_title')).toBe('Dashboard');
  });

  it('returns empty object when both locale and Dutch fail to load', async () => {
    fetchMock.mockImplementation(() => {
      return Promise.resolve({ ok: false, status: 500, json: () => Promise.reject() });
    });

    const instance = i18next.createInstance();
    await instance.use(HttpBackend).init({
      fallbackLng: DEFAULT_LOCALE,
      supportedLngs: [...SUPPORTED_LOCALES],
      lng: 'de',
      ns: ['common'],
      defaultNS: 'common',
      react: { useSuspense: false },
      interpolation: { escapeValue: false },
      returnEmptyString: false,
      parseMissingKeyHandler: (key: string) => key,
      backend: {
        loadPath: '/locales/{{lng}}/{{ns}}.json',
        request: (_options: unknown, url: string, _payload: unknown, callback: Function) => {
          fetchMock(url)
            .then((response: { ok: boolean; status: number; json: () => Promise<unknown> }) => {
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              return response.json();
            })
            .then((data: unknown) => {
              callback(null, { status: 200, data: JSON.stringify(data) });
            })
            .catch(() => {
              const localeMatch = (url as string).match(/\/locales\/([^/]+)\//);
              const locale = localeMatch ? localeMatch[1] : '';

              if (locale !== DEFAULT_LOCALE) {
                const fallbackUrl = (url as string).replace(
                  `/locales/${locale}/`,
                  `/locales/${DEFAULT_LOCALE}/`
                );
                fetchMock(fallbackUrl)
                  .then((resp: { ok: boolean; status: number; json: () => Promise<unknown> }) => {
                    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                    return resp.json();
                  })
                  .then((data: unknown) => {
                    callback(null, { status: 200, data: JSON.stringify(data) });
                  })
                  .catch(() => {
                    callback(null, { status: 200, data: '{}' });
                  });
              } else {
                callback(null, { status: 200, data: '{}' });
              }
            });
        },
      },
      initImmediate: false,
    });

    // Wait for async loading
    await new Promise((resolve) => setTimeout(resolve, 150));

    // When both fail, key string is returned (parseMissingKeyHandler)
    expect(instance.t('any_key')).toBe('any_key');
  });

  it('does not attempt Dutch fallback when Dutch locale itself fails', async () => {
    fetchMock.mockImplementation((url: string) => {
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.reject() });
    });

    const instance = i18next.createInstance();
    await instance.use(HttpBackend).init({
      fallbackLng: DEFAULT_LOCALE,
      supportedLngs: [...SUPPORTED_LOCALES],
      lng: 'nl',
      ns: ['common'],
      defaultNS: 'common',
      react: { useSuspense: false },
      interpolation: { escapeValue: false },
      returnEmptyString: false,
      parseMissingKeyHandler: (key: string) => key,
      backend: {
        loadPath: '/locales/{{lng}}/{{ns}}.json',
        request: (_options: unknown, url: string, _payload: unknown, callback: Function) => {
          fetchMock(url)
            .then((response: { ok: boolean; status: number; json: () => Promise<unknown> }) => {
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              return response.json();
            })
            .then((data: unknown) => {
              callback(null, { status: 200, data: JSON.stringify(data) });
            })
            .catch(() => {
              const localeMatch = (url as string).match(/\/locales\/([^/]+)\//);
              const locale = localeMatch ? localeMatch[1] : '';

              if (locale !== DEFAULT_LOCALE) {
                // This should NOT be reached for Dutch locale
                const fallbackUrl = (url as string).replace(
                  `/locales/${locale}/`,
                  `/locales/${DEFAULT_LOCALE}/`
                );
                fetchMock(fallbackUrl);
              } else {
                // Dutch itself failed — return empty
                callback(null, { status: 200, data: '{}' });
              }
            });
        },
      },
      initImmediate: false,
    });

    await new Promise((resolve) => setTimeout(resolve, 150));

    // Only one call should be made (the initial Dutch load that failed)
    // No recursive Dutch-to-Dutch fallback
    const nlCalls = fetchMock.mock.calls.filter(
      (call: string[]) => call[0].includes('/locales/nl/')
    );
    expect(nlCalls.length).toBe(1);
  });
});

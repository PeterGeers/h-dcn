/**
 * i18next initialization for the H-DCN portal.
 *
 * Configures react-i18next with:
 * - HttpBackend for lazy-loading namespace JSON files per route
 * - Dutch (nl) as fallback language
 * - React Suspense integration (blocks rendering until common namespace is ready)
 * - parseMissingKeyHandler returning the key as visible text (requirement 1.6)
 * - Empty string values treated as missing → triggers Dutch fallback (requirement 10.6)
 * - Development-mode console warnings for missing keys (requirement 10.5)
 * - Fallback to Dutch namespace on load failure (requirement 4.5)
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import HttpBackend, { HttpBackendOptions } from 'i18next-http-backend';
import { DEFAULT_LOCALE, DEFAULT_NAMESPACE, NAMESPACES } from './constants';

const isDevelopment = process.env.NODE_ENV === 'development';

i18n
  .use(HttpBackend)
  .use(initReactI18next)
  .init<HttpBackendOptions>({
    // Language settings
    fallbackLng: DEFAULT_LOCALE,
    supportedLngs: ['nl', 'en', 'fr', 'de', 'sv', 'da', 'it', 'es'],
    lng: DEFAULT_LOCALE, // Will be overridden by resolveLocale on app init

    // Namespace settings
    ns: [...NAMESPACES],
    defaultNS: DEFAULT_NAMESPACE,

    // Backend: lazy-load translation files per route (requirement 1.7)
    // On load failure, fall back to Dutch namespace file (requirement 4.5)
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
      request: (options, url, payload, callback) => {
        fetch(url)
          .then((response) => {
            if (!response.ok) {
              throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
          })
          .then((data) => {
            callback(null, { status: 200, data: JSON.stringify(data) });
          })
          .catch((error) => {
            // Extract locale from the URL to determine if this is already a Dutch fallback attempt
            const localeMatch = url.match(/\/locales\/([^/]+)\//);
            const locale = localeMatch ? localeMatch[1] : '';

            if (locale !== DEFAULT_LOCALE) {
              // Non-Dutch locale failed: attempt Dutch fallback (requirement 4.5)
              const fallbackUrl = url.replace(
                `/locales/${locale}/`,
                `/locales/${DEFAULT_LOCALE}/`
              );
              if (isDevelopment) {
                console.warn(
                  `[i18n] Failed to load namespace, falling back to Dutch: ${url}`
                );
              }
              fetch(fallbackUrl)
                .then((response) => {
                  if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                  }
                  return response.json();
                })
                .then((data) => {
                  callback(null, { status: 200, data: JSON.stringify(data) });
                })
                .catch(() => {
                  // Dutch fallback also failed — return empty to prevent crash
                  callback(null, { status: 200, data: '{}' });
                });
            } else {
              // Dutch locale itself failed — return empty to prevent crash
              callback(null, { status: 200, data: '{}' });
            }
          });
      },
    },

    // React integration
    react: {
      useSuspense: true,
    },

    // Interpolation (React already escapes values)
    interpolation: {
      escapeValue: false,
    },

    // Treat empty string values as missing — triggers Dutch fallback (requirement 10.6)
    returnEmptyString: false,

    // Missing key handling: return key as visible text (requirement 1.6)
    parseMissingKeyHandler: (key: string) => {
      return key;
    },

    // Development: log missing keys to console (requirement 10.5)
    saveMissing: isDevelopment,
    missingKeyHandler: (lngs, ns, key) => {
      if (isDevelopment) {
        console.warn(
          `[i18n] Missing key: locale=${lngs}, namespace=${ns}, key="${key}"`
        );
      }
    },
  });

export default i18n;

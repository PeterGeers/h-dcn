/**
 * Internationalization constants for the H-DCN portal.
 *
 * Defines supported locales and namespace configuration used
 * throughout the i18n system.
 */

/** Supported locale codes (ISO 639-1) */
export const SUPPORTED_LOCALES = [
  'nl', // Nederlands (default)
  'en', // English
  'fr', // Français
  'de', // Deutsch
  'sv', // Svenska
  'da', // Dansk
  'it', // Italiano
  'es', // Español
] as const;

export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

/** Default / fallback locale */
export const DEFAULT_LOCALE: SupportedLocale = 'nl';

/** Translation namespaces — one per feature module */
export const NAMESPACES = [
  'common',
  'dashboard',
  'webshop',
  'members',
  'events',
  'products',
  'auth',
  'presmeet',
  'eventBooking',
] as const;

export type Namespace = (typeof NAMESPACES)[number];

/** Default namespace loaded on every page */
export const DEFAULT_NAMESPACE: Namespace = 'common';

/** Native language names for display in the LanguageSelector */
export const LOCALE_NAMES: Record<SupportedLocale, string> = {
  nl: 'Nederlands',
  en: 'English',
  fr: 'Français',
  de: 'Deutsch',
  sv: 'Svenska',
  da: 'Dansk',
  it: 'Italiano',
  es: 'Español',
};

/** Country flag emoji codes for display in the LanguageSelector */
export const LOCALE_FLAGS: Record<SupportedLocale, string> = {
  nl: '🇳🇱',
  en: '🇬🇧',
  fr: '🇫🇷',
  de: '🇩🇪',
  sv: '🇸🇪',
  da: '🇩🇰',
  it: '🇮🇹',
  es: '🇪🇸',
};

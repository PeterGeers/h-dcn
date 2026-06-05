/**
 * useAdminLocale - Admin panel locale override hook.
 *
 * The admin panel remains Dutch-only (Requirement 9). This hook:
 * - Detects whether the current route is an admin panel page
 * - Overrides the i18n locale to 'nl' on admin routes
 * - Restores the user's preferred language on member-facing routes
 * - Provides a boolean for hiding the LanguageSelector on admin routes
 *
 * Requirements: 9.1, 9.3, 9.4, 9.5, 9.6
 */

import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { DEFAULT_LOCALE } from '../i18n/constants';

/**
 * Admin route path prefixes. Routes starting with any of these
 * are considered admin panel pages and will be forced to Dutch.
 */
const ADMIN_ROUTE_PREFIXES = [
  '/members',
  '/products',
  '/events',
  '/memberships',
  '/advanced-exports',
];

/**
 * Returns true if the given pathname matches an admin panel route.
 *
 * A path matches if it equals the prefix exactly or starts with the prefix
 * followed by a "/" (to support nested routes like /members/123).
 */
function isAdminPath(pathname: string): boolean {
  return ADMIN_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(prefix + '/')
  );
}

/**
 * Hook that returns whether the current route is an admin panel page.
 *
 * Use this to conditionally hide the LanguageSelector or apply
 * admin-specific UI behavior.
 */
export function useIsAdminRoute(): boolean {
  const location = useLocation();
  return isAdminPath(location.pathname);
}

/**
 * Hook that switches i18n locale to 'nl' on admin routes and restores
 * the user's preferred language when navigating back to member-facing routes.
 *
 * Should be called once at the app layout level (e.g., in the navigation header
 * or a top-level wrapper component).
 *
 * Behavior:
 * - When navigating TO an admin route: stores the current locale and switches to 'nl'
 * - When navigating FROM an admin route to a member route: restores the stored locale
 * - Does not persist locale changes — admin override is session-only
 */
export function useAdminLocaleOverride(): void {
  const { i18n } = useTranslation();
  const location = useLocation();
  const isAdmin = isAdminPath(location.pathname);

  // Store the user's preferred locale so we can restore it
  // when navigating away from admin routes.
  const userLocaleRef = useRef<string>(i18n.language);

  // Track whether we're currently in admin-override state
  const isOverriddenRef = useRef<boolean>(false);

  useEffect(() => {
    if (isAdmin) {
      // Entering admin route: save current locale (if not already overridden)
      // and switch to Dutch
      if (!isOverriddenRef.current) {
        userLocaleRef.current = i18n.language;
      }
      if (i18n.language !== DEFAULT_LOCALE) {
        i18n.changeLanguage(DEFAULT_LOCALE);
      }
      isOverriddenRef.current = true;
    } else {
      // Leaving admin route: restore the user's preferred locale
      if (isOverriddenRef.current) {
        const restoreLocale = userLocaleRef.current;
        if (i18n.language !== restoreLocale) {
          i18n.changeLanguage(restoreLocale);
        }
        isOverriddenRef.current = false;
      }
    }
  }, [isAdmin, i18n]);

  // Keep the ref in sync when the user changes language on member-facing pages
  // (e.g., via LanguageSelector)
  useEffect(() => {
    if (!isOverriddenRef.current) {
      userLocaleRef.current = i18n.language;
    }
  }, [i18n.language]);
}

// Also export the helper for testing purposes
export { isAdminPath, ADMIN_ROUTE_PREFIXES };

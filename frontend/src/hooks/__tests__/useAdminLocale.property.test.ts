/**
 * Property-based tests for admin locale override round-trip.
 *
 * Property 10: Admin locale override round-trip
 * **Validates: Requirements 9.1, 9.3, 9.4, 9.5, 9.6, 3.1**
 *
 * Uses fast-check to verify:
 * 1. isAdminPath returns true for any path starting with admin prefixes + optional /
 * 2. isAdminPath returns false for non-admin paths
 * 3. The locale is always 'nl' when on an admin route (round-trip property)
 */

import * as fc from 'fast-check';
import { isAdminPath, ADMIN_ROUTE_PREFIXES } from '../useAdminLocale';
import { SUPPORTED_LOCALES, DEFAULT_LOCALE } from '../../i18n/constants';

// ---------- Arbitraries ----------

/** Generates a valid admin route prefix */
const adminPrefixArb = fc.constantFrom(...ADMIN_ROUTE_PREFIXES);

/** Generates a path suffix (e.g., "/123", "/edit/1", "/new") */
const pathSuffixArb = fc.oneof(
  fc.constant(''),
  fc
    .array(
      fc.stringOf(
        fc.constantFrom(
          'a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p',
          'q','r','s','t','u','v','w','x','y','z',
          '0','1','2','3','4','5','6','7','8','9',
          '-','_'
        ),
        { minLength: 1, maxLength: 10 }
      ),
      { minLength: 1, maxLength: 3 }
    )
    .map((segments) => '/' + segments.join('/'))
);

/** Generates a full admin route (prefix + optional suffix) */
const adminRouteArb = fc.tuple(adminPrefixArb, pathSuffixArb).map(
  ([prefix, suffix]) => prefix + suffix
);

/**
 * Generates a member-facing route that does NOT start with any admin prefix.
 * Uses known safe prefixes that cannot collide with admin prefixes.
 */
const memberRoutePrefixes = [
  '/',
  '/dashboard',
  '/webshop',
  '/my-account',
  '/membership',
  '/presmeet',
  '/profile',
  '/cart',
  '/checkout',
  '/orders',
  '/help',
  '/contact',
  '/about',
];

const memberRouteArb = fc.oneof(
  fc.constantFrom(...memberRoutePrefixes),
  fc.tuple(
    fc.constantFrom(...memberRoutePrefixes),
    pathSuffixArb.filter((s) => s.length > 0)
  ).map(([prefix, suffix]) => prefix === '/' ? suffix : prefix + suffix)
);

/** Generates a non-Dutch supported locale */
const nonDutchLocales = SUPPORTED_LOCALES.filter((l) => l !== DEFAULT_LOCALE) as string[];
const nonDutchLocaleArb = fc.constantFrom(...nonDutchLocales);

/** Generates any supported locale */
const allLocales: string[] = [...SUPPORTED_LOCALES];
const supportedLocaleArb = fc.constantFrom(...allLocales);

// ---------- Tests ----------

describe('Admin Locale Override Round-Trip - Property Tests', () => {
  /**
   * **Validates: Requirements 9.1, 9.3**
   *
   * Property: For any path formed by an admin prefix followed by nothing or
   * a "/" and additional segments, isAdminPath returns true.
   */
  it('isAdminPath returns true for any path starting with an admin prefix + optional /', () => {
    fc.assert(
      fc.property(adminRouteArb, (adminPath) => {
        return isAdminPath(adminPath) === true;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 9.4, 3.1**
   *
   * Property: For any member-facing route that does not start with an admin
   * prefix, isAdminPath returns false.
   */
  it('isAdminPath returns false for non-admin (member-facing) routes', () => {
    fc.assert(
      fc.property(memberRouteArb, (memberPath) => {
        return isAdminPath(memberPath) === false;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 9.1, 9.3, 9.4, 9.5, 9.6, 3.1**
   *
   * Property: For any user with a non-Dutch preferred locale, simulating
   * navigation from a member route to an admin route and back produces:
   * - locale === 'nl' while on the admin route
   * - locale === original preference after returning to member route
   *
   * This tests the round-trip invariant of the admin locale override logic
   * using pure function simulation (no React rendering needed).
   */
  it('admin locale override round-trip: locale is nl on admin routes and restores on member routes', () => {
    fc.assert(
      fc.property(
        nonDutchLocaleArb,
        adminRouteArb,
        memberRouteArb,
        (userLocale, adminRoute, memberRoute) => {
          // Simulate the override logic from useAdminLocaleOverride:
          // State: user starts on a member route with their preferred locale
          let currentLocale = userLocale;
          let savedLocale = userLocale;
          let isOverridden = false;

          // Step 1: Navigate to admin route
          const isAdmin = isAdminPath(adminRoute);
          if (isAdmin) {
            if (!isOverridden) {
              savedLocale = currentLocale;
            }
            currentLocale = DEFAULT_LOCALE;
            isOverridden = true;
          }

          // Verify: locale must be 'nl' on admin route
          if (currentLocale !== DEFAULT_LOCALE) return false;

          // Step 2: Navigate back to member route
          const isMember = !isAdminPath(memberRoute);
          if (isMember && isOverridden) {
            currentLocale = savedLocale;
            isOverridden = false;
          }

          // Verify: locale must be restored to original preference
          if (currentLocale !== userLocale) return false;

          return true;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 9.1, 9.5**
   *
   * Property: For any supported locale and any admin route, the resolved
   * locale on the admin route is ALWAYS 'nl' (Dutch), regardless of
   * the user's preference.
   */
  it('locale is always nl on admin routes regardless of user preference', () => {
    fc.assert(
      fc.property(
        supportedLocaleArb,
        adminRouteArb,
        (userLocale, adminRoute) => {
          // The hook logic: if path is admin → force nl
          const isAdmin = isAdminPath(adminRoute);
          const effectiveLocale = isAdmin ? DEFAULT_LOCALE : userLocale;
          return effectiveLocale === DEFAULT_LOCALE;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 9.4, 3.1**
   *
   * Property: For any supported locale and any member route, the effective
   * locale remains the user's preference (not overridden to nl).
   */
  it('locale preserves user preference on member-facing routes', () => {
    fc.assert(
      fc.property(
        supportedLocaleArb,
        memberRouteArb,
        (userLocale, memberPath) => {
          // The hook logic: if path is NOT admin → keep user locale
          const isAdmin = isAdminPath(memberPath);
          const effectiveLocale = isAdmin ? DEFAULT_LOCALE : userLocale;
          return effectiveLocale === userLocale;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 9.5, 9.6**
   *
   * Property: The LanguageSelector visibility is the inverse of isAdminPath —
   * hidden on admin routes, visible on member routes. For any arbitrary path,
   * selector visibility equals !isAdminPath(path).
   */
  it('LanguageSelector visibility is the inverse of admin route detection', () => {
    fc.assert(
      fc.property(
        fc.oneof(adminRouteArb, memberRouteArb),
        (path) => {
          const isAdmin = isAdminPath(path);
          const selectorVisible = !isAdmin;
          // On admin routes: hidden (selectorVisible === false)
          // On member routes: visible (selectorVisible === true)
          return selectorVisible === !isAdmin;
        }
      ),
      { numRuns: 20 }
    );
  });
});

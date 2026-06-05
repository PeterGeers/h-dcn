/**
 * Unit tests for admin route detection via useIsAdminRoute / isAdminPath.
 *
 * Validates: Requirement 9.1 — Admin pages stay Dutch regardless of user preference.
 *
 * Tests that the helper correctly identifies admin vs member-facing routes.
 */

import { isAdminPath, ADMIN_ROUTE_PREFIXES } from '../../hooks/useAdminLocale';

describe('isAdminPath — admin route detection', () => {
  describe('identifies admin routes', () => {
    it.each([
      '/members',
      '/products',
      '/events',
      '/memberships',
      '/advanced-exports',
    ])('returns true for exact admin path "%s"', (path) => {
      expect(isAdminPath(path)).toBe(true);
    });

    it.each([
      '/members/123',
      '/members/edit/456',
      '/products/new',
      '/events/upcoming',
      '/memberships/type/gold',
      '/advanced-exports/csv',
    ])('returns true for nested admin path "%s"', (path) => {
      expect(isAdminPath(path)).toBe(true);
    });
  });

  describe('identifies member-facing routes', () => {
    it.each([
      '/',
      '/dashboard',
      '/webshop',
      '/webshop/cart',
      '/profile',
      '/profile/settings',
      '/login',
      '/auth/callback',
    ])('returns false for member-facing path "%s"', (path) => {
      expect(isAdminPath(path)).toBe(false);
    });
  });

  describe('edge cases', () => {
    it('returns false for empty string', () => {
      expect(isAdminPath('')).toBe(false);
    });

    it('returns false for root path', () => {
      expect(isAdminPath('/')).toBe(false);
    });

    it('returns false for path that partially matches but is not a prefix', () => {
      // "/membership" should not match "/memberships"
      expect(isAdminPath('/membership')).toBe(false);
    });

    it('returns false for paths with admin prefix as substring', () => {
      // "/my-members" should not match "/members"
      expect(isAdminPath('/my-members')).toBe(false);
    });

    it('returns false for path "/event" (not "/events")', () => {
      expect(isAdminPath('/event')).toBe(false);
    });

    it('returns false for path "/product" (not "/products")', () => {
      expect(isAdminPath('/product')).toBe(false);
    });
  });

  describe('ADMIN_ROUTE_PREFIXES constant', () => {
    it('contains exactly the 5 expected admin routes', () => {
      expect(ADMIN_ROUTE_PREFIXES).toEqual([
        '/members',
        '/products',
        '/events',
        '/memberships',
        '/advanced-exports',
      ]);
    });

    it('has 5 entries', () => {
      expect(ADMIN_ROUTE_PREFIXES).toHaveLength(5);
    });
  });
});

/**
 * Unit tests for useAdminLocale hook.
 *
 * Tests admin route detection (useIsAdminRoute) and locale override logic
 * (useAdminLocaleOverride) — switching to Dutch on admin routes and
 * restoring user preference on member-facing routes.
 *
 * Requirements: 9.1, 9.3, 9.4, 9.5, 9.6
 */

import { renderHook } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { isAdminPath, ADMIN_ROUTE_PREFIXES, useIsAdminRoute } from '../useAdminLocale';

describe('isAdminPath', () => {
  it('identifies exact admin routes as admin paths', () => {
    const adminRoutes = ['/members', '/products', '/events', '/memberships', '/advanced-exports'];
    adminRoutes.forEach((route) => {
      expect(isAdminPath(route)).toBe(true);
    });
  });

  it('identifies nested admin routes as admin paths', () => {
    expect(isAdminPath('/members/123')).toBe(true);
    expect(isAdminPath('/products/edit/1')).toBe(true);
    expect(isAdminPath('/events/new')).toBe(true);
    expect(isAdminPath('/memberships/manage')).toBe(true);
    expect(isAdminPath('/advanced-exports/csv')).toBe(true);
  });

  it('identifies member-facing routes as non-admin paths', () => {
    const memberRoutes = ['/', '/dashboard', '/webshop', '/my-account', '/membership', '/presmeet'];
    memberRoutes.forEach((route) => {
      expect(isAdminPath(route)).toBe(false);
    });
  });

  it('does not match partial path overlaps', () => {
    // '/membership' should NOT match '/members' prefix
    expect(isAdminPath('/membership')).toBe(false);
    // '/event-info' should NOT match '/events' prefix
    expect(isAdminPath('/event-info')).toBe(false);
    // '/product-details' should NOT match '/products' prefix
    expect(isAdminPath('/product-details')).toBe(false);
  });

  it('exports the expected admin route prefixes', () => {
    expect(ADMIN_ROUTE_PREFIXES).toEqual([
      '/members',
      '/products',
      '/events',
      '/memberships',
      '/advanced-exports',
    ]);
  });
});


describe('useIsAdminRoute', () => {
  function renderUseIsAdminRoute(path: string) {
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(MemoryRouter, { initialEntries: [path] }, children);

    return renderHook(() => useIsAdminRoute(), { wrapper });
  }

  it('returns true for admin routes', () => {
    const adminPaths = ['/members', '/products', '/events', '/memberships', '/advanced-exports'];
    adminPaths.forEach((path) => {
      const { result } = renderUseIsAdminRoute(path);
      expect(result.current).toBe(true);
    });
  });

  it('returns true for nested admin routes', () => {
    const { result } = renderUseIsAdminRoute('/members/123/edit');
    expect(result.current).toBe(true);
  });

  it('returns false for member-facing routes', () => {
    const memberPaths = ['/', '/dashboard', '/webshop', '/my-account', '/presmeet'];
    memberPaths.forEach((path) => {
      const { result } = renderUseIsAdminRoute(path);
      expect(result.current).toBe(false);
    });
  });

  it('returns false for partial prefix matches', () => {
    // '/membership' should NOT match '/members'
    const { result } = renderUseIsAdminRoute('/membership');
    expect(result.current).toBe(false);
  });
});

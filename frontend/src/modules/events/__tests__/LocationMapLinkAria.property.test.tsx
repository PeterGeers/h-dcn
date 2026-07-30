import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import fc from 'fast-check';
import LocationMapLink from '../components/LocationMapLink';

/**
 * Feature: event-location-maps-link, Property 4: Aria-label contains the location text
 *
 * Validates: Requirements 5.2
 *
 * For any valid non-empty, non-whitespace-only location string, the rendered link's
 * aria-label attribute SHALL contain the original location string value.
 */

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      if (key === 'location.openInMaps' && opts?.location) {
        return `Open ${opts.location} in Google Maps (opens in new tab)`;
      }
      return key;
    },
    i18n: { language: 'en' },
  }),
}));

describe('LocationMapLink - Property 4: Aria-label contains the location text', () => {
  const nonEmptyNonWhitespaceString = fc
    .fullUnicodeString({ minLength: 1, maxLength: 300 })
    .filter((s) => s.trim().length > 0);

  afterEach(() => {
    cleanup();
  });

  it('aria-label contains the trimmed location string for all valid locations', () => {
    fc.assert(
      fc.property(nonEmptyNonWhitespaceString, (location) => {
        render(
          <ChakraProvider>
            <LocationMapLink location={location} />
          </ChakraProvider>
        );

        const link = screen.getByRole('link');
        const ariaLabel = link.getAttribute('aria-label');

        expect(ariaLabel).not.toBeNull();
        expect(ariaLabel).toContain(location.trim());

        cleanup();
      }),
      { numRuns: 100 }
    );
  });
});

/**
 * Property-based tests for LocationMapLink — Invalid locations produce no output
 *
 * Feature: event-location-maps-link, Property 2: Invalid locations produce no output
 *
 * **Validates: Requirements 1.4, 2.2**
 *
 * Uses fast-check to generate null, undefined, empty strings, and whitespace-only strings.
 * Asserts the component renders nothing (returns null) for all invalid location values.
 */

import React from 'react';
import * as fc from 'fast-check';
import { render } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import LocationMapLink from '../components/LocationMapLink';

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

const renderWithChakra = (ui: React.ReactElement) =>
  render(<ChakraProvider>{ui}</ChakraProvider>);

// ---------------------------------------------------------------------------
// Generators
// ---------------------------------------------------------------------------

/**
 * Generates whitespace-only strings (spaces, tabs, newlines, carriage returns)
 * including the empty string.
 */
const whitespaceOnlyArbitrary = fc.stringOf(
  fc.constantFrom(' ', '\t', '\n', '\r'),
  { minLength: 0, maxLength: 50 }
);

// ---------------------------------------------------------------------------
// Property 2: Invalid locations produce no output
// ---------------------------------------------------------------------------

describe('Property 2: Invalid locations produce no output', () => {
  /**
   * **Validates: Requirements 1.4, 2.2**
   *
   * For any whitespace-only string (including empty string), the LocationMapLink
   * component renders nothing — no link element is present in the DOM.
   */
  it('renders no link for whitespace-only strings', () => {
    fc.assert(
      fc.property(whitespaceOnlyArbitrary, (whitespaceStr) => {
        const { container } = renderWithChakra(
          <LocationMapLink location={whitespaceStr} />
        );
        const link = container.querySelector('a');
        expect(link).toBeNull();
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 1.4, 2.2**
   *
   * For explicit null value, the component renders nothing — no link element.
   */
  it('renders no link for null', () => {
    const { container } = renderWithChakra(
      <LocationMapLink location={null} />
    );
    const link = container.querySelector('a');
    expect(link).toBeNull();
  });

  /**
   * **Validates: Requirements 1.4, 2.2**
   *
   * For explicit undefined value, the component renders nothing — no link element.
   */
  it('renders no link for undefined', () => {
    const { container } = renderWithChakra(
      <LocationMapLink location={undefined} />
    );
    const link = container.querySelector('a');
    expect(link).toBeNull();
  });
});

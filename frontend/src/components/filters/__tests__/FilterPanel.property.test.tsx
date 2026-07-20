/**
 * Property-based tests for FilterPanel component
 *
 * Uses fast-check to verify that FilterPanel renders exactly one
 * filter control per config entry for any valid configuration array.
 *
 * **Validates: Requirements 3.2**
 */

import React from 'react';
import { render } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import * as fc from 'fast-check';
import { FilterPanel } from '../FilterPanel';
import type { FilterConfig, SearchFilterConfig } from '../types';

// Mock react-i18next (used by GenericMultiFilter)
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      if (key === 'nSelected' && params?.count !== undefined) {
        return `${params.count} selected`;
      }
      return key;
    },
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

// ---------------------------------------------------------------------------
// Generators
// ---------------------------------------------------------------------------

/** Generate a non-empty label string. */
const labelArbitrary = fc.stringMatching(/^[A-Za-z ]{1,12}$/).filter((s) => s.trim().length > 0);

/** Generate a FilterOption object. */
const filterOptionArbitrary = fc.record({
  value: fc.stringMatching(/^[a-z0-9]{1,8}$/).filter((s) => s.length > 0),
  label: fc.stringMatching(/^[A-Za-z ]{1,10}$/).filter((s) => s.trim().length > 0),
});

/** Generate a single-select FilterConfig. */
const singleFilterArbitrary: fc.Arbitrary<FilterConfig<any>> = fc.record({
  type: fc.constant('single' as const),
  label: labelArbitrary,
  options: fc.array(filterOptionArbitrary, { minLength: 1, maxLength: 5 }),
  value: fc.constant(''),
  onChange: fc.constant(jest.fn()),
});

/** Generate a multi-select FilterConfig. */
const multiFilterArbitrary: fc.Arbitrary<FilterConfig<any>> = fc.record({
  type: fc.constant('multi' as const),
  label: labelArbitrary,
  options: fc.array(filterOptionArbitrary, { minLength: 1, maxLength: 5 }),
  value: fc.constant([] as string[]),
  onChange: fc.constant(jest.fn()),
});

/** Generate a search FilterConfig. */
const searchFilterArbitrary: fc.Arbitrary<SearchFilterConfig> = fc.record({
  type: fc.constant('search' as const),
  label: labelArbitrary,
  value: fc.constant(''),
  onChange: fc.constant(jest.fn()),
});

/** Generate a random filter config (single, multi, or search). */
const anyFilterArbitrary: fc.Arbitrary<FilterConfig<any> | SearchFilterConfig> = fc.oneof(
  singleFilterArbitrary,
  multiFilterArbitrary,
  searchFilterArbitrary,
);

/** Generate a random array of filter configs (1-8 entries). */
const filtersArrayArbitrary = fc.array(anyFilterArbitrary, { minLength: 1, maxLength: 8 });

/** Generate a layout mode. */
const layoutArbitrary = fc.constantFrom('horizontal' as const, 'vertical' as const, 'grid' as const);

// ---------------------------------------------------------------------------
// Property 3: FilterPanel renders one control per config entry
// ---------------------------------------------------------------------------

describe('Property 3: FilterPanel renders one control per config entry', () => {
  /**
   * **Validates: Requirements 3.2**
   *
   * For any array of FilterConfig objects passed to FilterPanel, the number
   * of rendered filter controls (GenericFilter select, GenericMultiFilter
   * button, or search Input) must equal the length of the filters prop array.
   */
  it('renders exactly one filter control per config entry for any valid config array', () => {
    fc.assert(
      fc.property(
        filtersArrayArbitrary,
        layoutArbitrary,
        (filters, layout) => {
          const { container } = render(
            <ChakraProvider>
              <FilterPanel filters={filters} layout={layout} />
            </ChakraProvider>,
          );

          // Each filter config entry renders exactly one FormLabel.
          // - GenericFilter renders a <FormLabel> with the filter label
          // - GenericMultiFilter renders a <FormLabel> with the filter label
          // - Search filter renders a <FormLabel> with the filter label
          // FormLabel renders as a <label> element in the DOM.
          const labels = container.querySelectorAll('label');

          expect(labels.length).toBe(filters.length);
        },
      ),
      { numRuns: 100 },
    );
  });
});

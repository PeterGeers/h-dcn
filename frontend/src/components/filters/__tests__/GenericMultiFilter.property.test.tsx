/**
 * Property-based tests for GenericMultiFilter component
 *
 * Uses fast-check with minimum 100 iterations per property.
 *
 * **Validates: Requirements 5.4, 5.6, 5.10**
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import '@testing-library/jest-dom';
import * as fc from 'fast-check';

// Mock react-i18next — returns key with interpolated params for count assertion
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      // For 'nSelected' key, return "N selected" format so we can assert on the count
      if (key === 'nSelected' && params && params.count !== undefined) {
        return `${params.count} selected`;
      }
      return key;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

import { GenericMultiFilter } from '../GenericMultiFilter';
import type { FilterOption } from '../types';

// ---------------------------------------------------------------------------
// Generators
// ---------------------------------------------------------------------------

/** Generate a valid filter option with unique value and non-empty label */
const filterOptionArbitrary: fc.Arbitrary<FilterOption> = fc.record({
  value: fc.stringMatching(/^[a-zA-Z0-9]{1,8}$/),
  label: fc.stringMatching(/^[a-zA-Z0-9 ]{1,12}$/),
});

/** Generate a unique array of filter options (unique by value) */
const optionsArrayArbitrary = fc.uniqueArray(filterOptionArbitrary, {
  minLength: 1,
  maxLength: 8,
  selector: (opt) => opt.value,
});

// ---------------------------------------------------------------------------
// Property 4: GenericMultiFilter selection display and accessibility
// ---------------------------------------------------------------------------

describe('Property 4: GenericMultiFilter selection display and accessibility', () => {
  /**
   * **Validates: Requirements 5.4, 5.10**
   *
   * For any non-empty value: string[] passed to GenericMultiFilter, the trigger
   * button text must contain the count value.length (via the translated
   * "N geselecteerd" pattern), and the aria-label must reflect the current
   * selection state.
   */
  it('trigger button displays count and aria-label reflects selection for any non-empty value', () => {
    fc.assert(
      fc.property(
        optionsArrayArbitrary.chain((options) => {
          const values = options.map((o) => o.value);
          return fc.tuple(
            fc.constant(options),
            fc.subarray(values, { minLength: 1 }),
          );
        }),
        ([options, selectedValues]) => {
          const { container, unmount } = render(
            <ChakraProvider>
              <GenericMultiFilter
                label="TestFilter"
                value={selectedValues}
                options={options}
                onChange={jest.fn()}
              />
            </ChakraProvider>
          );

          // Query within our container to avoid stale DOM issues
          const button = container.querySelector('button[aria-haspopup="menu"]') as HTMLElement;
          expect(button).toBeTruthy();

          const countStr = String(selectedValues.length);

          // The mock returns "N selected" for nSelected key — trigger text must contain count
          expect(button.textContent).toContain(countStr);

          // The aria-label should reflect the selection state and contain the count
          const ariaLabel = button.getAttribute('aria-label');
          expect(ariaLabel).toBeTruthy();
          expect(ariaLabel).toContain(countStr);

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 5.4**
   *
   * When value is empty, the trigger displays the placeholder (not a count).
   */
  it('trigger button displays placeholder when value is empty', () => {
    fc.assert(
      fc.property(
        optionsArrayArbitrary,
        (options) => {
          const { container, unmount } = render(
            <ChakraProvider>
              <GenericMultiFilter
                label="TestFilter"
                value={[]}
                options={options}
                onChange={jest.fn()}
              />
            </ChakraProvider>
          );

          const button = container.querySelector('button[aria-haspopup="menu"]') as HTMLElement;
          expect(button).toBeTruthy();

          // With empty value, display text should be the placeholder 'alle' (the t key)
          expect(button.textContent).toContain('alle');

          // aria-label should include the placeholder
          const ariaLabel = button.getAttribute('aria-label');
          expect(ariaLabel).toContain('alle');

          unmount();
        },
      ),
      { numRuns: 50 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 5: GenericMultiFilter toggle produces correct array
// ---------------------------------------------------------------------------

describe('Property 5: GenericMultiFilter toggle produces correct array', () => {
  /**
   * **Validates: Requirements 5.6**
   *
   * For any current selection value: string[] and any option opt from the
   * options array, toggling opt must call onChange with:
   * - if opt.value was in value, the new array is value without opt.value
   * - if opt.value was not in value, the new array is value with opt.value appended
   */
  it('toggling an option produces the correct onChange array', () => {
    fc.assert(
      fc.property(
        optionsArrayArbitrary.chain((options) => {
          const values = options.map((o) => o.value);
          return fc.tuple(
            fc.constant(options),
            fc.subarray(values, { minLength: 0 }),
            fc.integer({ min: 0, max: options.length - 1 }),
          );
        }),
        ([options, currentSelection, toggleIndex]) => {
          const toggledOption = options[toggleIndex];
          const onChange = jest.fn();

          const { container, unmount } = render(
            <ChakraProvider>
              <GenericMultiFilter
                label="TestFilter"
                value={currentSelection}
                options={options}
                onChange={onChange}
              />
            </ChakraProvider>
          );

          // Open the menu by clicking the trigger button
          const button = container.querySelector('button[aria-haspopup="menu"]') as HTMLElement;
          fireEvent.click(button);

          // Find menu item options within our container
          const menuItems = container.querySelectorAll('[role="menuitemcheckbox"]');
          const targetItem = menuItems[toggleIndex] as HTMLElement;
          fireEvent.click(targetItem);

          // Verify onChange was called
          expect(onChange).toHaveBeenCalled();
          const result = onChange.mock.calls[0][0] as string[];

          // Determine expected result
          const wasSelected = currentSelection.includes(toggledOption.value);
          if (wasSelected) {
            // Should be removed
            expect(result).not.toContain(toggledOption.value);
            expect(result.length).toBe(currentSelection.length - 1);
            // All other selected items should remain
            for (const v of currentSelection) {
              if (v !== toggledOption.value) {
                expect(result).toContain(v);
              }
            }
          } else {
            // Should be added
            expect(result).toContain(toggledOption.value);
            expect(result.length).toBe(currentSelection.length + 1);
            // All previously selected items should remain
            for (const v of currentSelection) {
              expect(result).toContain(v);
            }
          }

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });
});

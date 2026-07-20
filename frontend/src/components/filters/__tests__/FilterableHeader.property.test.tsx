/**
 * Property-based tests for FilterableHeader component
 *
 * Uses fast-check with minimum 100 iterations per property.
 *
 * **Validates: Requirements 2.1**
 */

import React from 'react';
import { render } from '@testing-library/react';
import { ChakraProvider, Table, Thead, Tr } from '@chakra-ui/react';
import '@testing-library/jest-dom';
import * as fc from 'fast-check';
import { FilterableHeader } from '../FilterableHeader';

function renderInTable(header: React.ReactElement) {
  return render(
    <ChakraProvider>
      <Table>
        <Thead>
          <Tr>{header}</Tr>
        </Thead>
      </Table>
    </ChakraProvider>
  );
}

/**
 * Generate non-empty label strings.
 * Uses printable ASCII characters to avoid rendering issues in tests.
 */
const nonEmptyLabelArbitrary = fc
  .stringMatching(/^[a-zA-Z0-9 _-]{1,30}$/)
  .filter((s) => s.trim().length > 0);

/** Generate a sort direction or null (inactive). */
const sortDirectionArbitrary = fc.oneof(
  fc.constant('asc' as const),
  fc.constant('desc' as const),
  fc.constant(null),
);

// ---------------------------------------------------------------------------
// Property: Accessibility Label Propagation
// ---------------------------------------------------------------------------

describe('FilterableHeader Property: Accessibility Label Propagation', () => {
  /**
   * **Validates: Requirements 2.1**
   *
   * For any non-empty label string, FilterableHeader renders `aria-label`
   * on the filter input containing the label text.
   */
  it('filter input aria-label contains the label text for any non-empty label', () => {
    fc.assert(
      fc.property(nonEmptyLabelArbitrary, (label) => {
        const { container, unmount } = renderInTable(
          <FilterableHeader
            label={label}
            filterValue=""
            onFilterChange={() => {}}
          />
        );

        const input = container.querySelector('input');
        expect(input).not.toBeNull();

        const ariaLabel = input!.getAttribute('aria-label');
        expect(ariaLabel).not.toBeNull();
        expect(ariaLabel).toContain(label);
        expect(ariaLabel).toBe(`Filter by ${label}`);

        unmount();
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 2.1**
   *
   * For any non-empty label string and any sort direction, when sorting is
   * enabled, FilterableHeader renders a valid `aria-sort` attribute on the
   * `<Th>` element matching the current sort direction.
   */
  it('aria-sort on <Th> matches the current sort direction for any label and direction', () => {
    fc.assert(
      fc.property(
        nonEmptyLabelArbitrary,
        sortDirectionArbitrary,
        (label, direction) => {
          const { container, unmount } = renderInTable(
            <FilterableHeader
              label={label}
              sortable
              sortDirection={direction}
              onSort={() => {}}
            />
          );

          const th = container.querySelector('th');
          expect(th).not.toBeNull();

          const ariaSort = th!.getAttribute('aria-sort');
          expect(ariaSort).not.toBeNull();

          if (direction === 'asc') {
            expect(ariaSort).toBe('ascending');
          } else if (direction === 'desc') {
            expect(ariaSort).toBe('descending');
          } else {
            expect(ariaSort).toBe('none');
          }

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });

  /**
   * Combined property: for any non-empty label, when both filter and sort
   * are enabled, both aria-label on input and aria-sort on Th are correct.
   */
  it('both aria-label and aria-sort are correct when filter and sort are enabled together', () => {
    fc.assert(
      fc.property(
        nonEmptyLabelArbitrary,
        sortDirectionArbitrary,
        (label, direction) => {
          const { container, unmount } = renderInTable(
            <FilterableHeader
              label={label}
              filterValue=""
              onFilterChange={() => {}}
              sortable
              sortDirection={direction}
              onSort={() => {}}
            />
          );

          // Check filter input aria-label
          const input = container.querySelector('input');
          expect(input).not.toBeNull();
          expect(input!.getAttribute('aria-label')).toBe(`Filter by ${label}`);

          // Check Th aria-sort
          const th = container.querySelector('th');
          expect(th).not.toBeNull();
          const expectedSort =
            direction === 'asc'
              ? 'ascending'
              : direction === 'desc'
                ? 'descending'
                : 'none';
          expect(th!.getAttribute('aria-sort')).toBe(expectedSort);

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });
});

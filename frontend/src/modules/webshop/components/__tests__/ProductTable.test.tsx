import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import '@testing-library/jest-dom';

// Feature: webshop-table-improvements — Task 4.5 "RTL component tests for ProductTable".
//
// These React Testing Library tests exercise the PUBLIC webshop ProductTable as
// a whole (filter + sort composition, thumbnail column, price formatting, row
// click, and the removal of the Opties column). The pure filter/sort helpers
// (`matchesFilters`, `fieldMatches`) are covered separately by
// productTableLogic.property.test.ts; here we assert the rendered behaviour.
//
// i18n: react-i18next is mocked so `t(key)` returns the key verbatim (the
// established webshop convention — see WebshopPage.test.tsx). A stable return
// object avoids re-render loops. Column labels therefore render as their keys
// (e.g. "table.name") and filter inputs use the key placeholders
// (e.g. "table.filter_name"). Tests locate filter inputs by placeholder.
//
// _Requirements: 4.1, 4.4, 1.4, 1.5, 1.6, 3.1, 3.2, 1.8, 6.2_

jest.mock('react-i18next', () => {
  const stableT = (key: string) => key;
  const stableI18n = { language: 'nl', changeLanguage: jest.fn() };
  const stableUseTranslation = { t: stableT, i18n: stableI18n };
  return {
    useTranslation: () => stableUseTranslation,
    initReactI18next: { type: '3rdParty', init: jest.fn() },
  };
});

// eslint-disable-next-line import/first -- must be imported AFTER jest.mock('react-i18next') above
import ProductTable, { Product } from '../ProductTable';

function renderTable(products: Product[], onProductSelect = jest.fn()) {
  const utils = render(
    <ChakraProvider>
      <ProductTable products={products} onProductSelect={onProductSelect} />
    </ChakraProvider>,
  );
  return { ...utils, onProductSelect };
}

/** The data rows (Tbody <tr>) in document order, excluding the header row. */
function getBodyRows(): HTMLElement[] {
  // Header cells are <th>; body cells are <td>. A body row contains <td>s.
  return screen
    .getAllByRole('row')
    .filter((row) => within(row).queryAllByRole('cell').length > 0);
}

/** The visible Name-column text for each body row, in document order. */
function getRowNames(): string[] {
  return getBodyRows().map((row) => {
    const cells = within(row).getAllByRole('cell');
    // Cell order: [thumbnail, name, group, subgroup, price].
    return cells[1].textContent?.trim() ?? '';
  });
}

const FULL_BUCKET_HOST = 'https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com';

describe('ProductTable (public webshop)', () => {
  // -----------------------------------------------------------------------
  // Thumbnail column (Requirement 4.1, 4.4)
  // -----------------------------------------------------------------------

  describe('thumbnail column', () => {
    it('renders an <img> for a product that has a usable image', () => {
      const imageUrl = `${FULL_BUCKET_HOST}/products/shirt.jpg`;
      renderTable([
        { product_id: 'p1', naam: 'Shirt', images: [imageUrl] },
      ]);

      const img = screen.getByRole('img');
      expect(img).toHaveAttribute('src', imageUrl);
    });

    it('uses the product name as the image alt text', () => {
      renderTable([
        { product_id: 'p1', naam: 'Leather Jacket', images: [`${FULL_BUCKET_HOST}/a.jpg`] },
      ]);
      expect(screen.getByRole('img')).toHaveAttribute('alt', 'Leather Jacket');
    });

    it('renders no <img> when the product has no image', () => {
      renderTable([{ product_id: 'p1', naam: 'No Image Product' }]);
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
    });

    it('renders no <img> when the image array is empty', () => {
      renderTable([{ product_id: 'p1', naam: 'Empty Images', images: [] }]);
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
    });

    it('renders an <img> only for rows that have an image', () => {
      renderTable([
        { product_id: 'p1', naam: 'With Image', images: [`${FULL_BUCKET_HOST}/a.jpg`] },
        { product_id: 'p2', naam: 'Without Image' },
      ]);
      // Exactly one image across both rows.
      expect(screen.getAllByRole('img')).toHaveLength(1);
    });
  });

  // -----------------------------------------------------------------------
  // Name text filter — case-insensitive (Requirement 1.4)
  // -----------------------------------------------------------------------

  describe('name text filter', () => {
    const products: Product[] = [
      { product_id: 'p1', naam: 'Harley Cap' },
      { product_id: 'p2', naam: 'Davidson Shirt' },
      { product_id: 'p3', naam: 'Leather Gloves' },
    ];

    it('shows only rows whose name contains the typed text', () => {
      renderTable(products);
      expect(getBodyRows()).toHaveLength(3);

      const nameFilter = screen.getByPlaceholderText('table.filter_name');
      fireEvent.change(nameFilter, { target: { value: 'Harley' } });

      expect(getRowNames()).toEqual(['Harley Cap']);
    });

    it('matches case-insensitively', () => {
      renderTable(products);
      const nameFilter = screen.getByPlaceholderText('table.filter_name');

      fireEvent.change(nameFilter, { target: { value: 'harley' } });
      expect(getRowNames()).toEqual(['Harley Cap']);

      fireEvent.change(nameFilter, { target: { value: 'LEATHER' } });
      expect(getRowNames()).toEqual(['Leather Gloves']);
    });

    it('shows every row again when the filter is cleared', () => {
      renderTable(products);
      const nameFilter = screen.getByPlaceholderText('table.filter_name');

      fireEvent.change(nameFilter, { target: { value: 'Harley' } });
      expect(getBodyRows()).toHaveLength(1);

      fireEvent.change(nameFilter, { target: { value: '' } });
      expect(getBodyRows()).toHaveLength(3);
    });
  });

  // -----------------------------------------------------------------------
  // Sort toggle: asc → desc → none (Requirement 1.5)
  // -----------------------------------------------------------------------

  describe('sort toggle', () => {
    const products: Product[] = [
      { product_id: 'p1', naam: 'Banana' },
      { product_id: 'p2', naam: 'Apple' },
      { product_id: 'p3', naam: 'Cherry' },
    ];

    it('starts sorted ascending by name (default)', () => {
      renderTable(products);
      // Default sort field is 'naam', direction 'asc'.
      expect(getRowNames()).toEqual(['Apple', 'Banana', 'Cherry']);
      // Ascending indicator present on the Name header.
      expect(screen.getByText('↑')).toBeInTheDocument();
    });

    it('cycles the Name column asc → desc, then to none when another column sorts', () => {
      renderTable(products);

      // asc (default)
      expect(getRowNames()).toEqual(['Apple', 'Banana', 'Cherry']);
      expect(screen.getByText('↑')).toBeInTheDocument();

      // Click Name → desc
      fireEvent.click(screen.getByRole('button', { name: 'Sort by table.name' }));
      expect(getRowNames()).toEqual(['Cherry', 'Banana', 'Apple']);
      expect(screen.getByText('↓')).toBeInTheDocument();
      expect(screen.queryByText('↑')).not.toBeInTheDocument();

      // Click Name again → back to asc
      fireEvent.click(screen.getByRole('button', { name: 'Sort by table.name' }));
      expect(getRowNames()).toEqual(['Apple', 'Banana', 'Cherry']);
      expect(screen.getByText('↑')).toBeInTheDocument();

      // Sorting a DIFFERENT column (Price) leaves the Name column in the
      // "none" state: its asc/desc indicator is no longer shown.
      fireEvent.click(screen.getByRole('button', { name: 'Sort by table.price' }));
      const nameHeader = screen.getByRole('columnheader', { name: /table\.name/ });
      expect(nameHeader).toHaveAttribute('aria-sort', 'none');
    });

    it('reflects the active sort column via aria-sort on the header', () => {
      renderTable(products);
      const nameHeader = screen.getByRole('columnheader', { name: /table\.name/ });
      // Default active sort is Name ascending.
      expect(nameHeader).toHaveAttribute('aria-sort', 'ascending');

      fireEvent.click(screen.getByRole('button', { name: 'Sort by table.name' }));
      expect(nameHeader).toHaveAttribute('aria-sort', 'descending');
    });
  });

  // -----------------------------------------------------------------------
  // Multiple filters combine with AND (Requirement 1.6)
  // -----------------------------------------------------------------------

  describe('multiple filters (AND)', () => {
    const products: Product[] = [
      { product_id: 'p1', naam: 'Red Cap', groep: 'Headwear', subgroep: 'Caps' },
      { product_id: 'p2', naam: 'Blue Cap', groep: 'Headwear', subgroep: 'Caps' },
      { product_id: 'p3', naam: 'Red Shirt', groep: 'Clothing', subgroep: 'Shirts' },
    ];

    it('shows only rows satisfying every active column filter', () => {
      renderTable(products);
      expect(getBodyRows()).toHaveLength(3);

      // Name contains "Red" → p1, p3
      fireEvent.change(screen.getByPlaceholderText('table.filter_name'), {
        target: { value: 'Red' },
      });
      expect(getRowNames().sort()).toEqual(['Red Cap', 'Red Shirt']);

      // AND Group contains "Headwear" → only p1 remains
      fireEvent.change(screen.getByPlaceholderText('table.filter_group'), {
        target: { value: 'Headwear' },
      });
      expect(getRowNames()).toEqual(['Red Cap']);
    });

    it('yields no rows when the combined filters match nothing', () => {
      renderTable(products);
      fireEvent.change(screen.getByPlaceholderText('table.filter_name'), {
        target: { value: 'Red' },
      });
      fireEvent.change(screen.getByPlaceholderText('table.filter_subgroup'), {
        target: { value: 'Shirts' },
      });
      // Red + Shirts → only "Red Shirt"
      expect(getRowNames()).toEqual(['Red Shirt']);

      // Now add an incompatible group filter.
      fireEvent.change(screen.getByPlaceholderText('table.filter_group'), {
        target: { value: 'Headwear' },
      });
      expect(getBodyRows()).toHaveLength(0);
    });
  });

  // -----------------------------------------------------------------------
  // No "Opties" column (Requirement 3.1, 3.2)
  // -----------------------------------------------------------------------

  describe('removed Opties column', () => {
    it('renders no "Opties" / table.options header', () => {
      renderTable([
        { product_id: 'p1', naam: 'Parent Product', is_parent: true },
      ]);
      expect(screen.queryByText('Opties')).not.toBeInTheDocument();
      expect(screen.queryByText('table.options')).not.toBeInTheDocument();
    });

    it('renders no "Varianten" / "Standaard" cell content', () => {
      renderTable([
        { product_id: 'p1', naam: 'Parent', is_parent: true },
        { product_id: 'p2', naam: 'Simple', is_parent: false },
      ]);
      expect(screen.queryByText('Varianten')).not.toBeInTheDocument();
      expect(screen.queryByText('Standaard')).not.toBeInTheDocument();
    });

    it('renders exactly the expected header columns (thumbnail + 4 labelled)', () => {
      const { container } = renderTable([{ product_id: 'p1', naam: 'A' }]);
      // Query the raw <th> DOM (not the `columnheader` role): the thumbnail <Th>
      // is aria-hidden and the Group/Subgroup headers are responsively hidden at
      // the jsdom base breakpoint, so they fall out of the accessibility tree.
      // Thumbnail + Name + Group + Subgroup + Price = 5 header cells, no Opties.
      const headerCells = container.querySelectorAll('thead th');
      expect(headerCells).toHaveLength(5);
      // None of them is the Opties header.
      const headerText = Array.from(headerCells)
        .map((th) => th.textContent ?? '')
        .join(' ');
      expect(headerText).not.toContain('Opties');
      expect(headerText).not.toContain('table.options');
    });
  });

  // -----------------------------------------------------------------------
  // Row click fires onProductSelect (Requirement 1.8)
  // -----------------------------------------------------------------------

  describe('row click', () => {
    it('calls onProductSelect with the clicked product', () => {
      const product: Product = { product_id: 'p1', naam: 'Clickable' };
      const { onProductSelect } = renderTable([product]);

      fireEvent.click(getBodyRows()[0]);

      expect(onProductSelect).toHaveBeenCalledTimes(1);
      expect(onProductSelect).toHaveBeenCalledWith(product);
    });

    it('still fires onProductSelect after a filter narrows the rows', () => {
      const products: Product[] = [
        { product_id: 'p1', naam: 'Keep Me' },
        { product_id: 'p2', naam: 'Filter Out' },
      ];
      const { onProductSelect } = renderTable(products);

      fireEvent.change(screen.getByPlaceholderText('table.filter_name'), {
        target: { value: 'Keep' },
      });
      expect(getBodyRows()).toHaveLength(1);

      fireEvent.click(getBodyRows()[0]);
      expect(onProductSelect).toHaveBeenCalledWith(products[0]);
    });
  });

  // -----------------------------------------------------------------------
  // Price via formatPrice (Requirement 6.2)
  // -----------------------------------------------------------------------

  describe('price formatting', () => {
    it('renders a numeric price as €X.XX', () => {
      renderTable([{ product_id: 'p1', naam: 'Priced', prijs: 25 }]);
      expect(screen.getByText('€25.00')).toBeInTheDocument();
    });

    it('renders a string price safely via formatPrice', () => {
      renderTable([{ product_id: 'p1', naam: 'Str Priced', prijs: '12.5' }]);
      expect(screen.getByText('€12.50')).toBeInTheDocument();
    });

    it('renders €0.00 for a null price (no crash, no .toFixed on raw field)', () => {
      renderTable([
        { product_id: 'p1', naam: 'Null Priced', prijs: null as unknown as number },
      ]);
      expect(screen.getByText('€0.00')).toBeInTheDocument();
    });

    it('renders €0.00 when the price field is absent', () => {
      renderTable([{ product_id: 'p1', naam: 'No Price' }]);
      expect(screen.getByText('€0.00')).toBeInTheDocument();
    });
  });
});

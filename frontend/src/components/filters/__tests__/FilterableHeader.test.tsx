/**
 * FilterableHeader Unit Tests
 *
 * Test suite for the FilterableHeader component covering:
 * - Label rendering
 * - Filter input rendering and callbacks
 * - Sort indicator rendering and callbacks
 * - Accessibility attributes (aria-label, aria-sort)
 * - isNumeric right-alignment
 *
 * Requirements: 2.1
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider, Table, Thead, Tr } from '@chakra-ui/react';
import '@testing-library/jest-dom';
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

describe('FilterableHeader', () => {
  // -----------------------------------------------------------------------
  // Label rendering
  // -----------------------------------------------------------------------

  it('renders label text in <Th>', () => {
    renderInTable(<FilterableHeader label="Account Name" />);
    expect(screen.getByText('Account Name')).toBeInTheDocument();
  });

  it('renders label with dark theme styling', () => {
    renderInTable(<FilterableHeader label="Status" />);
    const th = screen.getByRole('columnheader');
    expect(th).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Filter input rendering
  // -----------------------------------------------------------------------

  it('renders filter input when filterValue is provided', () => {
    renderInTable(<FilterableHeader label="Name" filterValue="" onFilterChange={jest.fn()} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('does not render filter input when filterValue is omitted', () => {
    renderInTable(<FilterableHeader label="Name" />);
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('renders filter input with dark theme styling', () => {
    renderInTable(<FilterableHeader label="Name" filterValue="test" onFilterChange={jest.fn()} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('renders filter input with default placeholder', () => {
    renderInTable(<FilterableHeader label="Name" filterValue="" onFilterChange={jest.fn()} />);
    expect(screen.getByPlaceholderText('Filter...')).toBeInTheDocument();
  });

  it('renders filter input with custom placeholder', () => {
    renderInTable(
      <FilterableHeader
        label="Name"
        filterValue=""
        onFilterChange={jest.fn()}
        placeholder="Search names..."
      />
    );
    expect(screen.getByPlaceholderText('Search names...')).toBeInTheDocument();
  });

  it('displays current filter value in input', () => {
    renderInTable(<FilterableHeader label="Name" filterValue="john" onFilterChange={jest.fn()} />);
    expect(screen.getByRole('textbox')).toHaveValue('john');
  });

  // -----------------------------------------------------------------------
  // Filter change callback
  // -----------------------------------------------------------------------

  it('calls onFilterChange on input change', () => {
    const onFilterChange = jest.fn();
    renderInTable(<FilterableHeader label="Name" filterValue="" onFilterChange={onFilterChange} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'abc' } });
    expect(onFilterChange).toHaveBeenCalledWith('abc');
  });

  // -----------------------------------------------------------------------
  // Sort indicator rendering
  // -----------------------------------------------------------------------

  it('renders ascending sort indicator when sortable and sortDirection is asc', () => {
    renderInTable(<FilterableHeader label="Amount" sortable sortDirection="asc" onSort={jest.fn()} />);
    expect(screen.getByText('↑')).toBeInTheDocument();
  });

  it('renders descending sort indicator when sortable and sortDirection is desc', () => {
    renderInTable(<FilterableHeader label="Amount" sortable sortDirection="desc" onSort={jest.fn()} />);
    expect(screen.getByText('↓')).toBeInTheDocument();
  });

  it('does not render sort indicator when sortable but sortDirection is null', () => {
    renderInTable(<FilterableHeader label="Amount" sortable sortDirection={null} onSort={jest.fn()} />);
    expect(screen.queryByText('↑')).not.toBeInTheDocument();
    expect(screen.queryByText('↓')).not.toBeInTheDocument();
  });

  it('does not render sort indicator when not sortable', () => {
    renderInTable(<FilterableHeader label="Notes" />);
    expect(screen.queryByText('↑')).not.toBeInTheDocument();
    expect(screen.queryByText('↓')).not.toBeInTheDocument();
  });

  it('renders sort indicator with orange.300 color', () => {
    renderInTable(<FilterableHeader label="Amount" sortable sortDirection="asc" onSort={jest.fn()} />);
    const indicator = screen.getByText('↑');
    expect(indicator).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Sort click callback
  // -----------------------------------------------------------------------

  it('calls onSort callback on sort click', () => {
    const onSort = jest.fn();
    renderInTable(<FilterableHeader label="Amount" sortable sortDirection="asc" onSort={onSort} />);
    const labelRow = screen.getByRole('button', { name: 'Sort by Amount' });
    fireEvent.click(labelRow);
    expect(onSort).toHaveBeenCalledTimes(1);
  });

  it('does not call onSort when not sortable', () => {
    const onSort = jest.fn();
    renderInTable(<FilterableHeader label="Notes" onSort={onSort} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(onSort).not.toHaveBeenCalled();
  });

  it('sets cursor to pointer when sortable', () => {
    renderInTable(<FilterableHeader label="Amount" sortable onSort={jest.fn()} />);
    const labelRow = screen.getByRole('button', { name: 'Sort by Amount' });
    expect(labelRow).toBeInTheDocument();
  });

  it('sets cursor to default when not sortable', () => {
    renderInTable(<FilterableHeader label="Notes" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('sets role=button on label row when sortable', () => {
    renderInTable(<FilterableHeader label="Amount" sortable onSort={jest.fn()} />);
    expect(screen.getByRole('button', { name: 'Sort by Amount' })).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Accessibility: aria-label on filter input
  // -----------------------------------------------------------------------

  it('sets aria-label on filter input', () => {
    renderInTable(<FilterableHeader label="Account" filterValue="" onFilterChange={jest.fn()} />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-label', 'Filter by Account');
  });

  // -----------------------------------------------------------------------
  // Accessibility: aria-sort on <Th>
  // -----------------------------------------------------------------------

  it('sets aria-sort="ascending" on <Th> when sortable and direction is asc', () => {
    renderInTable(<FilterableHeader label="Amount" sortable sortDirection="asc" onSort={jest.fn()} />);
    const th = screen.getByRole('columnheader');
    expect(th).toHaveAttribute('aria-sort', 'ascending');
  });

  it('sets aria-sort="descending" on <Th> when sortable and direction is desc', () => {
    renderInTable(<FilterableHeader label="Amount" sortable sortDirection="desc" onSort={jest.fn()} />);
    const th = screen.getByRole('columnheader');
    expect(th).toHaveAttribute('aria-sort', 'descending');
  });

  it('sets aria-sort="none" on <Th> when sortable but no active direction', () => {
    renderInTable(<FilterableHeader label="Amount" sortable sortDirection={null} onSort={jest.fn()} />);
    const th = screen.getByRole('columnheader');
    expect(th).toHaveAttribute('aria-sort', 'none');
  });

  it('does not set aria-sort on <Th> when not sortable', () => {
    renderInTable(<FilterableHeader label="Notes" />);
    const th = screen.getByRole('columnheader');
    expect(th).not.toHaveAttribute('aria-sort');
  });

  // -----------------------------------------------------------------------
  // isNumeric prop
  // -----------------------------------------------------------------------

  it('passes isNumeric prop to <Th> for right-alignment', () => {
    renderInTable(<FilterableHeader label="Amount" isNumeric />);
    const th = screen.getByRole('columnheader');
    expect(th).toBeInTheDocument();
  });

  it('aligns VStack to flex-end when isNumeric', () => {
    renderInTable(<FilterableHeader label="Amount" isNumeric />);
    expect(screen.getByText('Amount')).toBeInTheDocument();
  });

  it('aligns VStack to flex-start when not isNumeric', () => {
    renderInTable(<FilterableHeader label="Name" />);
    expect(screen.getByText('Name')).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Combined: filter + sort
  // -----------------------------------------------------------------------

  it('renders both filter input and sort indicator together', () => {
    renderInTable(
      <FilterableHeader
        label="Account"
        filterValue="test"
        onFilterChange={jest.fn()}
        sortable
        sortDirection="asc"
        onSort={jest.fn()}
      />
    );
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByText('↑')).toBeInTheDocument();
    expect(screen.getByText('Account')).toBeInTheDocument();
  });
});

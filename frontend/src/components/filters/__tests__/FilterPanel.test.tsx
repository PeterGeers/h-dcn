/**
 * FilterPanel Unit Tests
 *
 * Test suite for the FilterPanel component covering:
 * - Horizontal layout
 * - Vertical layout
 * - Grid layout
 * - Mixed filter types (single, multi, search)
 * - Props propagation to child filter components
 *
 * Requirements: 3.1
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import '@testing-library/jest-dom';
import { FilterPanel } from '../FilterPanel';
import { FilterConfig, SearchFilterConfig } from '../types';

// Mock GenericFilter to simplify testing
jest.mock('../GenericFilter', () => ({
  GenericFilter: ({ label, value, options, isDisabled, placeholder }: any) => (
    <div data-testid={`filter-${label}`}>
      <span data-label={label}>{label}</span>
      <span data-value={value}>{value || 'none'}</span>
      <span data-options={JSON.stringify(options)}>
        {options?.length || 0} options
      </span>
      {isDisabled && <span data-disabled="true">disabled</span>}
      {placeholder && <span data-placeholder={placeholder}>{placeholder}</span>}
    </div>
  ),
}));

// Mock GenericMultiFilter to simplify testing
jest.mock('../GenericMultiFilter', () => ({
  GenericMultiFilter: ({ label, value, options, isDisabled, placeholder }: any) => (
    <div data-testid={`multi-filter-${label}`}>
      <span data-label={label}>{label}</span>
      <span data-values={JSON.stringify(value)}>
        {value.length > 0 ? value.join(', ') : 'none'}
      </span>
      <span data-options={JSON.stringify(options)}>
        {options?.length || 0} options
      </span>
      {isDisabled && <span data-disabled="true">disabled</span>}
      {placeholder && <span data-placeholder={placeholder}>{placeholder}</span>}
    </div>
  ),
}));

function renderWithChakra(ui: React.ReactElement) {
  return render(<ChakraProvider>{ui}</ChakraProvider>);
}

describe('FilterPanel', () => {
  const mockSingleSelectFilter: FilterConfig<string> = {
    type: 'single',
    label: 'Year',
    options: ['2023', '2024', '2025'],
    value: '2024',
    onChange: jest.fn(),
  };

  const mockMultiSelectFilter: FilterConfig<string> = {
    type: 'multi',
    label: 'Listings',
    options: ['Listing 1', 'Listing 2', 'Listing 3'],
    value: ['Listing 1', 'Listing 2'],
    onChange: jest.fn(),
  };

  const mockSearchFilter: SearchFilterConfig = {
    type: 'search',
    label: 'Reference',
    value: '',
    onChange: jest.fn(),
    placeholder: 'Search...',
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Horizontal Layout', () => {
    it('renders with horizontal layout by default', () => {
      renderWithChakra(
        <FilterPanel filters={[mockSingleSelectFilter]} />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
    });

    it('renders multiple filters in horizontal layout', () => {
      renderWithChakra(
        <FilterPanel filters={[mockSingleSelectFilter, mockMultiSelectFilter]} />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
      expect(screen.getByTestId('multi-filter-Listings')).toBeInTheDocument();
    });

    it('renders filters with custom spacing', () => {
      renderWithChakra(
        <FilterPanel filters={[mockSingleSelectFilter]} spacing={6} />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
    });
  });

  describe('Vertical Layout', () => {
    it('renders with vertical layout when specified', () => {
      renderWithChakra(
        <FilterPanel filters={[mockSingleSelectFilter]} layout="vertical" />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
    });

    it('renders multiple filters in vertical layout', () => {
      renderWithChakra(
        <FilterPanel
          filters={[mockSingleSelectFilter, mockMultiSelectFilter]}
          layout="vertical"
        />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
      expect(screen.getByTestId('multi-filter-Listings')).toBeInTheDocument();
    });

    it('renders filters with custom spacing in vertical layout', () => {
      renderWithChakra(
        <FilterPanel
          filters={[mockSingleSelectFilter]}
          layout="vertical"
          spacing={3}
        />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
    });
  });

  describe('Grid Layout', () => {
    it('renders with grid layout when specified', () => {
      renderWithChakra(
        <FilterPanel filters={[mockSingleSelectFilter]} layout="grid" />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
    });

    it('renders multiple filters in grid layout', () => {
      renderWithChakra(
        <FilterPanel
          filters={[mockSingleSelectFilter, mockMultiSelectFilter, mockSearchFilter]}
          layout="grid"
        />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
      expect(screen.getByTestId('multi-filter-Listings')).toBeInTheDocument();
      // Search filter renders as FormControl, not GenericFilter
      expect(screen.getByText('Reference')).toBeInTheDocument();
    });

    it('renders with custom grid columns', () => {
      renderWithChakra(
        <FilterPanel
          filters={[mockSingleSelectFilter]}
          layout="grid"
          gridColumns={3}
        />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
    });

    it('renders with custom minChildWidth', () => {
      renderWithChakra(
        <FilterPanel
          filters={[mockSingleSelectFilter]}
          layout="grid"
          gridMinWidth="250px"
        />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
    });

    it('renders with custom spacing in grid layout', () => {
      renderWithChakra(
        <FilterPanel
          filters={[mockSingleSelectFilter]}
          layout="grid"
          spacing={5}
        />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
    });
  });

  describe('Mixed Filter Types', () => {
    it('renders single-select filter correctly', () => {
      renderWithChakra(
        <FilterPanel filters={[mockSingleSelectFilter]} />
      );

      const filter = screen.getByTestId('filter-Year');
      expect(filter).toHaveTextContent('Year');
      expect(filter).toHaveTextContent('2024');
    });

    it('renders multi-select filter correctly', () => {
      renderWithChakra(
        <FilterPanel filters={[mockMultiSelectFilter]} />
      );

      const filter = screen.getByTestId('multi-filter-Listings');
      expect(filter).toHaveTextContent('Listings');
      expect(filter).toHaveTextContent('Listing 1, Listing 2');
    });

    it('renders both single and multi-select filters together', () => {
      renderWithChakra(
        <FilterPanel filters={[mockSingleSelectFilter, mockMultiSelectFilter]} />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
      expect(screen.getByTestId('multi-filter-Listings')).toBeInTheDocument();
    });

    it('handles search filter type', () => {
      renderWithChakra(
        <FilterPanel filters={[mockSearchFilter]} />
      );

      // Search filters render as FormControl with label + input
      expect(screen.getByText('Reference')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument();
    });

    it('renders three different filter types together', () => {
      renderWithChakra(
        <FilterPanel
          filters={[mockSingleSelectFilter, mockMultiSelectFilter, mockSearchFilter]}
          layout="grid"
          gridColumns={3}
        />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
      expect(screen.getByTestId('multi-filter-Listings')).toBeInTheDocument();
      expect(screen.getByText('Reference')).toBeInTheDocument();
    });
  });

  describe('Props Propagation', () => {
    it('propagates disabled state from filter config to single-select', () => {
      const disabledFilter: FilterConfig<string> = {
        ...mockSingleSelectFilter,
        disabled: true,
      };

      renderWithChakra(
        <FilterPanel filters={[disabledFilter]} />
      );

      const filter = screen.getByTestId('filter-Year');
      expect(filter).toHaveTextContent('disabled');
    });

    it('propagates disabled state from filter config to multi-select', () => {
      const disabledFilter: FilterConfig<string> = {
        ...mockMultiSelectFilter,
        disabled: true,
      };

      renderWithChakra(
        <FilterPanel filters={[disabledFilter]} />
      );

      const filter = screen.getByTestId('multi-filter-Listings');
      expect(filter).toHaveTextContent('disabled');
    });

    it('propagates placeholder from filter config', () => {
      const filterWithPlaceholder: FilterConfig<string> = {
        ...mockSingleSelectFilter,
        placeholder: 'Choose a year',
      };

      renderWithChakra(
        <FilterPanel filters={[filterWithPlaceholder]} />
      );

      const filter = screen.getByTestId('filter-Year');
      expect(filter).toHaveTextContent('Choose a year');
    });
  });

  describe('Value Handling', () => {
    it('passes single value to GenericFilter', () => {
      renderWithChakra(
        <FilterPanel filters={[mockSingleSelectFilter]} />
      );

      const filter = screen.getByTestId('filter-Year');
      expect(filter).toHaveTextContent('2024');
    });

    it('passes array values to GenericMultiFilter', () => {
      renderWithChakra(
        <FilterPanel filters={[mockMultiSelectFilter]} />
      );

      const filter = screen.getByTestId('multi-filter-Listings');
      expect(filter).toHaveTextContent('Listing 1, Listing 2');
    });

    it('handles empty single value', () => {
      const emptyFilter: FilterConfig<string> = {
        ...mockSingleSelectFilter,
        value: '',
      };

      renderWithChakra(
        <FilterPanel filters={[emptyFilter]} />
      );

      const filter = screen.getByTestId('filter-Year');
      expect(filter).toHaveTextContent('none');
    });

    it('handles empty array value', () => {
      const emptyFilter: FilterConfig<string> = {
        ...mockMultiSelectFilter,
        value: [],
      };

      renderWithChakra(
        <FilterPanel filters={[emptyFilter]} />
      );

      const filter = screen.getByTestId('multi-filter-Listings');
      expect(filter).toHaveTextContent('none');
    });
  });

  describe('Edge Cases', () => {
    it('renders with empty filters array', () => {
      const { container } = renderWithChakra(
        <FilterPanel filters={[]} />
      );

      // Should render without crashing even with no filters
      expect(container).toBeTruthy();
    });

    it('renders with single filter', () => {
      renderWithChakra(
        <FilterPanel filters={[mockSingleSelectFilter]} />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
    });

    it('renders with many filters', () => {
      const manyFilters: FilterConfig<string>[] = Array.from({ length: 10 }, (_, i) => ({
        type: 'single' as const,
        label: `Filter ${i + 1}`,
        options: ['A', 'B', 'C'],
        value: 'A',
        onChange: jest.fn(),
      }));

      renderWithChakra(
        <FilterPanel
          filters={manyFilters}
          layout="grid"
          gridColumns={4}
        />
      );

      manyFilters.forEach((_, i) => {
        expect(screen.getByTestId(`filter-Filter ${i + 1}`)).toBeInTheDocument();
      });
    });

    it('handles filters with special characters in labels', () => {
      const specialFilter: FilterConfig<string> = {
        type: 'single',
        label: 'Year (2023-2025)',
        options: ['2023', '2024', '2025'],
        value: '2024',
        onChange: jest.fn(),
      };

      renderWithChakra(
        <FilterPanel filters={[specialFilter]} />
      );

      expect(screen.getByTestId('filter-Year (2023-2025)')).toBeInTheDocument();
    });
  });

  describe('Responsive Behavior', () => {
    it('renders grid layout with responsive columns', () => {
      renderWithChakra(
        <FilterPanel
          filters={[mockSingleSelectFilter, mockMultiSelectFilter]}
          layout="grid"
          gridColumns={3}
        />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
      expect(screen.getByTestId('multi-filter-Listings')).toBeInTheDocument();
    });

    it('horizontal layout renders filters', () => {
      renderWithChakra(
        <FilterPanel
          filters={[mockSingleSelectFilter, mockMultiSelectFilter]}
          layout="horizontal"
        />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
      expect(screen.getByTestId('multi-filter-Listings')).toBeInTheDocument();
    });

    it('grid layout renders with minChildWidth', () => {
      renderWithChakra(
        <FilterPanel
          filters={[mockSingleSelectFilter]}
          layout="grid"
          gridMinWidth="300px"
        />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
    });
  });

  describe('Integration Scenarios', () => {
    it('renders report filter pattern (single year + single quarter)', () => {
      const yearFilter: FilterConfig<string> = {
        type: 'single',
        label: 'Year',
        options: ['2023', '2024', '2025'],
        value: '2024',
        onChange: jest.fn(),
      };

      const quarterFilter: FilterConfig<string> = {
        type: 'single',
        label: 'Quarter',
        options: ['Q1', 'Q2', 'Q3', 'Q4'],
        value: 'Q1',
        onChange: jest.fn(),
      };

      renderWithChakra(
        <FilterPanel
          filters={[yearFilter, quarterFilter]}
          layout="horizontal"
        />
      );

      expect(screen.getByTestId('filter-Year')).toBeInTheDocument();
      expect(screen.getByTestId('filter-Quarter')).toBeInTheDocument();
    });

    it('renders multi-year filter pattern', () => {
      const yearFilter: FilterConfig<string> = {
        type: 'multi',
        label: 'Years',
        options: ['2022', '2023', '2024', '2025'],
        value: ['2023', '2024'],
        onChange: jest.fn(),
      };

      renderWithChakra(
        <FilterPanel
          filters={[yearFilter]}
          layout="horizontal"
        />
      );

      const filter = screen.getByTestId('multi-filter-Years');
      expect(filter).toHaveTextContent('2023, 2024');
    });

    it('renders complex filter pattern (multi-year + multi-listing + multi-channel)', () => {
      const yearFilter: FilterConfig<string> = {
        type: 'multi',
        label: 'Years',
        options: ['2023', '2024', '2025'],
        value: ['2024'],
        onChange: jest.fn(),
      };

      const listingFilter: FilterConfig<string> = {
        type: 'multi',
        label: 'Listings',
        options: ['Listing 1', 'Listing 2'],
        value: [],
        onChange: jest.fn(),
      };

      const channelFilter: FilterConfig<string> = {
        type: 'multi',
        label: 'Channels',
        options: ['airbnb', 'booking', 'direct'],
        value: ['airbnb'],
        onChange: jest.fn(),
      };

      renderWithChakra(
        <FilterPanel
          filters={[yearFilter, listingFilter, channelFilter]}
          layout="grid"
          gridColumns={3}
        />
      );

      expect(screen.getByTestId('multi-filter-Years')).toBeInTheDocument();
      expect(screen.getByTestId('multi-filter-Listings')).toBeInTheDocument();
      expect(screen.getByTestId('multi-filter-Channels')).toBeInTheDocument();
    });
  });
});

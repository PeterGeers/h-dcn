/**
 * MemberFilters Component Tests
 * 
 * Tests for the MemberFilters component including:
 * - Filter controls update results
 * - Multiple filters combine with AND logic
 * - Filter state management
 * - Clear filters functionality
 * - Performance requirements (<200ms)
 * 
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { MemberFilters, applyFilters, MemberFilters as MemberFiltersType } from '../MemberFilters';
import { Member } from '../../types/index';

// Mock Chakra UI icons
jest.mock('@chakra-ui/icons', () => ({
  SearchIcon: () => <span data-testid="search-icon">🔍</span>,
  CloseIcon: () => <span data-testid="close-icon">✕</span>,
  ChevronDownIcon: () => <span data-testid="chevron-down">▼</span>,
  ChevronUpIcon: () => <span data-testid="chevron-up">▲</span>,
}));

// Mock Chakra UI components
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div data-testid="box" {...props}>{children}</div>,
  SimpleGrid: ({ children, ...props }: any) => <div data-testid="simple-grid" {...props}>{children}</div>,
  FormControl: ({ children, ...props }: any) => <div data-testid="form-control" {...props}>{children}</div>,
  FormLabel: ({ children, ...props }: any) => <label data-testid="form-label" {...props}>{children}</label>,
  Select: ({ children, value, onChange, placeholder, ...props }: any) => (
    <select data-testid="select" value={value} onChange={onChange} {...props}>
      {placeholder && <option value="">{placeholder}</option>}
      {children}
    </select>
  ),
  Input: ({ value, onChange, placeholder, ...props }: any) => (
    <input
      data-testid="input"
      type="text"
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      {...props}
    />
  ),
  HStack: ({ children, ...props }: any) => <div data-testid="hstack" {...props}>{children}</div>,
  Button: ({ children, onClick, leftIcon, ...props }: any) => (
    <button data-testid="button" onClick={onClick} {...props}>
      {leftIcon}
      {children}
    </button>
  ),
  Text: ({ children, ...props }: any) => <span data-testid="text" {...props}>{children}</span>,
  Badge: ({ children, ...props }: any) => <span data-testid="badge" {...props}>{children}</span>,
  VStack: ({ children, ...props }: any) => <div data-testid="vstack" {...props}>{children}</div>,
  IconButton: ({ onClick, icon, 'aria-label': ariaLabel, ...props }: any) => (
    <button data-testid="icon-button" onClick={onClick} aria-label={ariaLabel} {...props}>
      {icon}
    </button>
  ),
  Collapse: ({ children, in: isOpen, ...props }: any) => (
    isOpen ? <div data-testid="collapse" {...props}>{children}</div> : null
  ),
  useDisclosure: () => ({
    isOpen: true,
    onToggle: jest.fn(),
    onOpen: jest.fn(),
    onClose: jest.fn(),
  }),
}));

// Sample member data for testing
const mockMembers: Member[] = [
  {
    id: '1',
    lidnummer: '12345',
    voornaam: 'Jan',
    achternaam: 'Jansen',
    email: 'jan@example.com',
    telefoon: '0612345678',
    regio: 'Utrecht',
    status: 'Actief',
    lidmaatschap: 'Gewoon lid',
    geboortedatum: '1980-03-15',
  } as Member,
  {
    id: '2',
    lidnummer: '12346',
    voornaam: 'Piet',
    achternaam: 'Pietersen',
    email: 'piet@example.com',
    telefoon: '0687654321',
    regio: 'Zuid-Holland',
    status: 'Actief',
    lidmaatschap: 'Gezins lid',
    geboortedatum: '1975-07-22',
  } as Member,
  {
    id: '3',
    lidnummer: '12347',
    voornaam: 'Klaas',
    achternaam: 'Klaassen',
    email: 'klaas@example.com',
    telefoon: '0698765432',
    regio: 'Utrecht',
    status: 'Opgezegd',
    lidmaatschap: 'Gewoon lid',
    geboortedatum: '1990-03-10',
  } as Member,
  {
    id: '4',
    lidnummer: '12348',
    voornaam: 'Marie',
    achternaam: 'de Vries',
    email: 'marie@example.com',
    telefoon: '0611223344',
    regio: 'Noord-Holland',
    status: 'Actief',
    lidmaatschap: 'Donateur',
    geboortedatum: '1985-12-05',
  } as Member,
];

describe('MemberFilters Component', () => {
  let onChangeMock: jest.Mock;

  beforeEach(() => {
    onChangeMock = jest.fn();
  });

  describe('Rendering', () => {
    test('should render filter controls', () => {
      render(<MemberFilters onChange={onChangeMock} />);

      expect(screen.getByText(/Filters/i)).toBeInTheDocument();
    });

    test('should display member counts when provided', () => {
      render(
        <MemberFilters
          onChange={onChangeMock}
          totalCount={100}
          filteredCount={50}
        />
      );

      expect(screen.getByText(/50 \/ 100 leden/i)).toBeInTheDocument();
    });
  });

  describe('Filter Controls Update Results (Requirement 5.1, 5.2)', () => {
    test('should call onChange when status filter is changed', async () => {
      const user = userEvent.setup();
      render(<MemberFilters onChange={onChangeMock} />);

      const statusSelect = screen.getAllByTestId('select')[0]; // First select is status
      await user.selectOptions(statusSelect, 'Actief');

      await waitFor(() => {
        expect(onChangeMock).toHaveBeenCalledWith(
          expect.objectContaining({ status: 'Actief' })
        );
      });
    });

    test('should call onChange when region filter is changed', async () => {
      const user = userEvent.setup();
      render(<MemberFilters onChange={onChangeMock} />);

      const regionSelect = screen.getAllByTestId('select')[1]; // Second select is region
      await user.selectOptions(regionSelect, 'Utrecht');

      await waitFor(() => {
        expect(onChangeMock).toHaveBeenCalledWith(
          expect.objectContaining({ regio: 'Utrecht' })
        );
      });
    });

    test('should call onChange when membership type filter is changed', async () => {
      const user = userEvent.setup();
      render(<MemberFilters onChange={onChangeMock} />);

      const membershipSelect = screen.getAllByTestId('select')[2]; // Third select is membership
      await user.selectOptions(membershipSelect, 'Gewoon lid');

      await waitFor(() => {
        expect(onChangeMock).toHaveBeenCalledWith(
          expect.objectContaining({ lidmaatschap: 'Gewoon lid' })
        );
      });
    });

    test('should call onChange when birthday month filter is changed', async () => {
      const user = userEvent.setup();
      render(<MemberFilters onChange={onChangeMock} />);

      const monthSelect = screen.getAllByTestId('select')[3]; // Fourth select is birthday month
      await user.selectOptions(monthSelect, '3');

      await waitFor(() => {
        expect(onChangeMock).toHaveBeenCalledWith(
          expect.objectContaining({ birthdayMonth: 3 })
        );
      });
    });

    test('should call onChange when search text is entered', async () => {
      const user = userEvent.setup();
      render(<MemberFilters onChange={onChangeMock} />);

      const searchInput = screen.getByTestId('input');
      await user.type(searchInput, 'Jan');

      await waitFor(() => {
        expect(onChangeMock).toHaveBeenCalledWith(
          expect.objectContaining({ searchText: 'Jan' })
        );
      });
    });

    test('should remove filter when cleared', async () => {
      const user = userEvent.setup();
      render(<MemberFilters onChange={onChangeMock} initialFilters={{ status: 'Actief' }} />);

      const statusSelect = screen.getAllByTestId('select')[0];
      await user.selectOptions(statusSelect, ''); // Select empty option

      await waitFor(() => {
        expect(onChangeMock).toHaveBeenCalledWith({});
      });
    });
  });

  describe('Clear Filters Functionality', () => {
    test('should clear all filters when clear button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <MemberFilters
          onChange={onChangeMock}
          initialFilters={{ status: 'Actief', regio: 'Utrecht' }}
        />
      );

      // Find and click the clear filters button
      const clearButton = screen.getByText(/Wis filters/i);
      await user.click(clearButton);

      await waitFor(() => {
        expect(onChangeMock).toHaveBeenCalledWith({});
      });
    });
  });
});

describe('applyFilters Utility Function', () => {
  describe('Single Filter Tests (Requirement 5.1)', () => {
    test('should filter by status', () => {
      const filters: MemberFiltersType = { status: 'Actief' };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(3);
      expect(result.every(m => m.status === 'Actief')).toBe(true);
    });

    test('should filter by region', () => {
      const filters: MemberFiltersType = { regio: 'Utrecht' };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(2);
      expect(result.every(m => m.regio === 'Utrecht')).toBe(true);
    });

    test('should filter by membership type', () => {
      const filters: MemberFiltersType = { lidmaatschap: 'Gewoon lid' };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(2);
      expect(result.every(m => m.lidmaatschap === 'Gewoon lid')).toBe(true);
    });

    test('should filter by search text (name)', () => {
      const filters: MemberFiltersType = { searchText: 'Jan' };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(1);
      expect(result[0].voornaam).toBe('Jan');
    });

    test('should filter by search text (email)', () => {
      const filters: MemberFiltersType = { searchText: 'piet@example.com' };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(1);
      expect(result[0].email).toBe('piet@example.com');
    });

    test('should filter by search text (phone)', () => {
      const filters: MemberFiltersType = { searchText: '0612345678' };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(1);
      expect(result[0].telefoon).toBe('0612345678');
    });

    test('should filter by birthday month', () => {
      const filters: MemberFiltersType = { birthdayMonth: 3 }; // March
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(2); // Jan (March 15) and Klaas (March 10)
      expect(result.every(m => {
        const month = new Date(m.geboortedatum!).getMonth() + 1;
        return month === 3;
      })).toBe(true);
    });

    test('should be case-insensitive for search text', () => {
      const filters: MemberFiltersType = { searchText: 'MARIE' };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(1);
      expect(result[0].voornaam).toBe('Marie');
    });
  });

  describe('Multiple Filters with AND Logic (Requirement 5.3)', () => {
    test('should combine status and region filters with AND logic', () => {
      const filters: MemberFiltersType = {
        status: 'Actief',
        regio: 'Utrecht',
      };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(1);
      expect(result[0].voornaam).toBe('Jan');
      expect(result[0].status).toBe('Actief');
      expect(result[0].regio).toBe('Utrecht');
    });

    test('should combine status, region, and membership filters with AND logic', () => {
      const filters: MemberFiltersType = {
        status: 'Actief',
        regio: 'Utrecht',
        lidmaatschap: 'Gewoon lid',
      };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(1);
      expect(result[0].voornaam).toBe('Jan');
    });

    test('should combine search text with other filters using AND logic', () => {
      const filters: MemberFiltersType = {
        status: 'Actief',
        searchText: 'Jan',
      };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(1);
      expect(result[0].voornaam).toBe('Jan');
      expect(result[0].status).toBe('Actief');
    });

    test('should return empty array when no members match all filters', () => {
      const filters: MemberFiltersType = {
        status: 'Actief',
        regio: 'Utrecht',
        lidmaatschap: 'Donateur', // No active Utrecht members with Donateur membership
      };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(0);
    });

    test('should combine all filter types with AND logic', () => {
      const filters: MemberFiltersType = {
        status: 'Actief',
        regio: 'Utrecht',
        lidmaatschap: 'Gewoon lid',
        birthdayMonth: 3,
        searchText: 'Jan',
      };
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(1);
      expect(result[0].voornaam).toBe('Jan');
    });
  });

  describe('Edge Cases', () => {
    test('should return all members when no filters are applied', () => {
      const filters: MemberFiltersType = {};
      const result = applyFilters(mockMembers, filters);

      expect(result).toHaveLength(mockMembers.length);
    });

    test('should handle members with missing fields gracefully', () => {
      const membersWithMissingFields: Member[] = [
        {
          id: '5',
          lidnummer: '12349',
          voornaam: 'Test',
          achternaam: 'User',
          // Missing email, telefoon, regio, etc.
        } as Member,
      ];

      const filters: MemberFiltersType = { searchText: 'Test' };
      const result = applyFilters(membersWithMissingFields, filters);

      expect(result).toHaveLength(1);
    });

    test('should handle invalid birth dates gracefully', () => {
      const membersWithInvalidDate: Member[] = [
        {
          id: '6',
          lidnummer: '12350',
          voornaam: 'Invalid',
          achternaam: 'Date',
          geboortedatum: 'invalid-date',
        } as Member,
      ];

      const filters: MemberFiltersType = { birthdayMonth: 3 };
      const result = applyFilters(membersWithInvalidDate, filters);

      expect(result).toHaveLength(0); // Invalid dates are excluded
    });
  });

  describe('Performance (Requirement 5.2)', () => {
    test('should filter large dataset within 200ms', () => {
      // Create a large dataset (1500 members)
      const largeDataset: Member[] = Array.from({ length: 1500 }, (_, i) => ({
        id: `${i}`,
        lidnummer: `${10000 + i}`,
        voornaam: `Member${i}`,
        achternaam: `Test${i}`,
        email: `member${i}@example.com`,
        telefoon: `06${String(i).padStart(8, '0')}`,
        regio: i % 2 === 0 ? 'Utrecht' : 'Zuid-Holland',
        status: i % 3 === 0 ? 'Actief' : 'Opgezegd',
        lidmaatschap: 'Gewoon lid',
        geboortedatum: `1980-${String((i % 12) + 1).padStart(2, '0')}-15`,
      })) as Member[];

      const filters: MemberFiltersType = {
        status: 'Actief',
        regio: 'Utrecht',
      };

      const startTime = performance.now();
      const result = applyFilters(largeDataset, filters);
      const endTime = performance.now();
      const duration = endTime - startTime;

      // Should complete within 200ms (requirement 5.2)
      expect(duration).toBeLessThan(200);
      
      // Should have results (every 6th member: i%2===0 for Utrecht AND i%3===0 for Actief)
      expect(result.length).toBeGreaterThan(0);
    });
  });
});

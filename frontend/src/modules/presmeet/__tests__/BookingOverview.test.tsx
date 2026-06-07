/**
 * BookingOverview component tests.
 *
 * Validates: Requirements 9.1–9.4
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import BookingOverview from '../components/BookingOverview';
import { CartItem, OrderStatus } from '../types/presmeet';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      const translations: Record<string, string> = {
        'overview.title': 'Booking Overview',
        'overview.no_items': 'No items have been added to your booking yet.',
        'overview.grand_total': 'Grand Total',
        'overview.total_paid': 'Total Paid',
        'overview.remaining_balance': 'Remaining Balance',
        'overview.item': 'Item',
        'overview.price': 'Price',
        'overview.items_count': '{{count}} items',
        'product_types.meeting_ticket': 'Meeting Ticket',
        'product_types.party_ticket': 'Party Ticket',
        'product_types.tshirt': 'T-Shirt',
        'product_types.airport_transfer': 'Airport Transfer',
      };
      let result = translations[key] ?? key;
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          result = result.replace(`{{${k}}}`, String(v));
        });
      }
      return result;
    },
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

// Mock Chakra UI — provide simple DOM elements
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  VStack: ({ children }: any) => <div>{children}</div>,
  HStack: ({ children }: any) => <div style={{ display: 'flex' }}>{children}</div>,
  Text: ({ children }: any) => <span>{children}</span>,
  Badge: ({ children }: any) => <span>{children}</span>,
  Table: ({ children }: any) => <table>{children}</table>,
  Thead: ({ children }: any) => <thead>{children}</thead>,
  Tbody: ({ children }: any) => <tbody>{children}</tbody>,
  Tfoot: ({ children }: any) => <tfoot>{children}</tfoot>,
  Tr: ({ children }: any) => <tr>{children}</tr>,
  Th: ({ children }: any) => <th>{children}</th>,
  Td: ({ children }: any) => <td>{children}</td>,
  Alert: ({ children }: any) => <div role="alert">{children}</div>,
  AlertIcon: () => <span />,
  Heading: ({ children }: any) => <h2>{children}</h2>,
}));

describe('BookingOverview', () => {
  const mockItems: CartItem[] = [
    {
      item_id: '1',
      product_type: 'meeting_ticket',
      attributes: { name: 'Jan de Vries', role: 'President' },
      unit_price: 50,
    },
    {
      item_id: '2',
      product_type: 'meeting_ticket',
      attributes: { name: 'Piet Bakker', role: 'Secretary' },
      unit_price: 50,
    },
    {
      item_id: '3',
      product_type: 'party_ticket',
      attributes: { name: 'Jan de Vries', person_type: 'delegate' },
      unit_price: 99.5,
    },
    {
      item_id: '4',
      product_type: 'airport_transfer',
      attributes: { direction: 'pickup', airport: 'AMS', flight: 'KL1234', date: '2025-09-15', time: '10:00', persons: 2 },
      unit_price: 5,
    },
  ];

  it('renders grouped items with correct totals', () => {
    render(
      <BookingOverview items={mockItems} status="draft" totalPaid={0} />
    );

    // Should show group labels
    expect(screen.getByText('Meeting Ticket')).toBeInTheDocument();
    expect(screen.getByText('Party Ticket')).toBeInTheDocument();
    expect(screen.getByText('Airport Transfer')).toBeInTheDocument();

    // Should show individual item labels (Jan de Vries appears in both meeting_ticket and party_ticket)
    expect(screen.getAllByText('Jan de Vries')).toHaveLength(2);
    expect(screen.getByText('Piet Bakker')).toBeInTheDocument();
    expect(screen.getByText('pickup – AMS')).toBeInTheDocument();
  });

  it('shows empty state message when no items', () => {
    render(
      <BookingOverview items={[]} status="draft" totalPaid={0} />
    );

    expect(screen.getByText('No items have been added to your booking yet.')).toBeInTheDocument();
  });

  it('displays grand total correctly', () => {
    // Grand total: 2×50 + 1×99.50 + 2×5 = 100 + 99.50 + 10 = 209.50
    render(
      <BookingOverview items={mockItems} status="submitted" totalPaid={0} />
    );

    // €209.50 appears twice: Grand Total and Remaining Balance (since totalPaid=0)
    expect(screen.getAllByText('€209.50')).toHaveLength(2);
    expect(screen.getByText('Grand Total')).toBeInTheDocument();
  });

  it('shows remaining balance', () => {
    // Grand total 209.50, paid 100 => remaining 109.50
    render(
      <BookingOverview items={mockItems} status="submitted" totalPaid={100} />
    );

    expect(screen.getByText('€109.50')).toBeInTheDocument();
    expect(screen.getByText('Remaining Balance')).toBeInTheDocument();
  });

  it('displays zero grand total when empty', () => {
    render(
      <BookingOverview items={[]} status="draft" totalPaid={0} />
    );

    expect(screen.getByText('€0.00')).toBeInTheDocument();
  });
});

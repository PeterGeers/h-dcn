/**
 * BookingOverview component tests.
 *
 * Validates: Requirements 1.1, 1.5, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 8.3
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import BookingOverview from '../components/BookingOverview';
import { CartItem, OrderStatus, PaymentStatus } from '../types/presmeet';

// Mock pdfGenerator
const mockGenerateBookingPdf = jest.fn();
jest.mock('../utils/pdfGenerator', () => ({
  generateBookingPdf: (...args: any[]) => mockGenerateBookingPdf(...args),
}));

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        'overview.title': 'Booking Overview',
        'overview.no_items': 'No items have been added to your booking yet.',
        'overview.grand_total': 'Grand Total',
        'overview.total_paid': 'Total Paid',
        'overview.remaining_balance': 'Remaining Balance',
        'overview.item': 'Item',
        'overview.price': 'Price',
        'overview.items_count': '{{count}} items',
        'overview.submitted_at': 'Submitted',
        'overview.delegate': 'delegate',
        'overview.download_pdf': 'Download PDF',
        'overview.downloading': 'Downloading...',
        'overview.pdf_error_title': 'PDF generation failed',
        'overview.pdf_error_description': 'Could not generate PDF. Please try again.',
        'product_types.meeting_ticket': 'Meeting Ticket',
        'product_types.party_ticket': 'Party Ticket',
        'product_types.tshirt': 'T-Shirt',
        'product_types.airport_transfer': 'Airport Transfer',
        'transfers.persons': 'persons',
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

// Mock useToast
const mockToast = jest.fn();
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  VStack: ({ children }: any) => <div>{children}</div>,
  HStack: ({ children }: any) => <div style={{ display: 'flex' }}>{children}</div>,
  Text: ({ children }: any) => <span>{children}</span>,
  Badge: ({ children }: any) => <span>{children}</span>,
  Button: ({ children, onClick, leftIcon, isLoading, loadingText, ...props }: any) => (
    <button onClick={onClick} disabled={isLoading} {...props}>
      {leftIcon}
      {isLoading ? loadingText : children}
    </button>
  ),
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
  useToast: () => mockToast,
}));

// Mock @chakra-ui/icons
jest.mock('@chakra-ui/icons', () => ({
  DownloadIcon: () => <span data-testid="download-icon" />,
}));

describe('BookingOverview', () => {
  const defaultProps = {
    status: 'draft' as OrderStatus,
    paymentStatus: 'unpaid' as PaymentStatus,
    totalPaid: 0,
    clubName: 'Test Club',
    clubId: 'test-club-1',
    submittedAt: null as string | null,
  };

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
      <BookingOverview items={mockItems} {...defaultProps} />
    );

    // Should show group labels
    expect(screen.getByText('Meeting Ticket')).toBeInTheDocument();
    expect(screen.getByText('Party Ticket')).toBeInTheDocument();
    expect(screen.getByText('Airport Transfer')).toBeInTheDocument();

    // Should show individual item labels
    expect(screen.getAllByText('Jan de Vries')).toHaveLength(2);
    expect(screen.getByText('Piet Bakker')).toBeInTheDocument();
  });

  it('shows empty state message when no items', () => {
    render(
      <BookingOverview items={[]} {...defaultProps} />
    );

    expect(screen.getByText('No items have been added to your booking yet.')).toBeInTheDocument();
  });

  it('displays grand total correctly', () => {
    // Grand total: 2×50 + 1×99.50 + 2×5 = 100 + 99.50 + 10 = 209.50
    render(
      <BookingOverview items={mockItems} {...defaultProps} status="submitted" submittedAt="2025-01-15" />
    );

    // €209.50 appears in remaining balance (same value since totalPaid=0) and grand total
    expect(screen.getAllByText('€209.50').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Grand Total')).toBeInTheDocument();
  });

  it('shows remaining balance', () => {
    // Grand total 209.50, paid 100 => remaining 109.50
    render(
      <BookingOverview items={mockItems} {...defaultProps} status="submitted" totalPaid={100} submittedAt="2025-01-15" />
    );

    expect(screen.getByText('€109.50')).toBeInTheDocument();
    expect(screen.getByText('Remaining Balance')).toBeInTheDocument();
  });

  it('displays zero grand total when empty', () => {
    render(
      <BookingOverview items={[]} {...defaultProps} />
    );

    expect(screen.getByText('€0.00')).toBeInTheDocument();
  });

  it('displays club name', () => {
    render(
      <BookingOverview items={mockItems} {...defaultProps} clubName="Harley Club Amsterdam" />
    );

    expect(screen.getByText('Harley Club Amsterdam')).toBeInTheDocument();
  });

  it('displays submission date when status is submitted', () => {
    render(
      <BookingOverview
        items={mockItems}
        {...defaultProps}
        status="submitted"
        submittedAt="2025-06-15"
      />
    );

    // The component renders: t('overview.submitted_at') + ": " + formatDate(submittedAt)
    // Text is split across elements so use a regex matcher
    expect(screen.getByText(/Submitted/)).toBeInTheDocument();
    expect(screen.getByText(/2025/)).toBeInTheDocument();
  });

  it('displays submission date when status is locked', () => {
    render(
      <BookingOverview
        items={mockItems}
        {...defaultProps}
        status="locked"
        submittedAt="2025-06-15"
      />
    );

    expect(screen.getByText(/Submitted/)).toBeInTheDocument();
  });

  it('does not display submission date when status is draft', () => {
    render(
      <BookingOverview
        items={mockItems}
        {...defaultProps}
        status="draft"
        submittedAt="2025-06-15"
      />
    );

    expect(screen.queryByText(/Submitted/)).not.toBeInTheDocument();
  });

  it('shows persons × unit_price for airport transfers with persons > 1', () => {
    render(
      <BookingOverview items={mockItems} {...defaultProps} />
    );

    // Transfer with persons=2: 2 × €5.00 = €10.00
    expect(screen.getByText('2 × €5.00 = €10.00')).toBeInTheDocument();
  });

  it('shows persons in label for airport transfers with persons > 1', () => {
    render(
      <BookingOverview items={mockItems} {...defaultProps} />
    );

    // Transfer label text is split: "pickup – AMS" in parent td, "(2 persons)" in child span
    expect(screen.getByText('pickup – AMS')).toBeInTheDocument();
    // The persons annotation span contains "(2 persons)" with the number
    expect(screen.getByText(/persons/)).toBeInTheDocument();
    // The price cell shows the multiplication: "2 × €5.00 = €10.00"
    expect(screen.getByText('2 × €5.00 = €10.00')).toBeInTheDocument();
  });

  it('does not show persons annotation for transfer with persons = 1', () => {
    const singlePersonTransfer: CartItem[] = [
      {
        item_id: '10',
        product_type: 'airport_transfer',
        attributes: { direction: 'dropoff', airport: 'RTM', flight: 'BA123', date: '2025-09-16', time: '14:00', persons: 1 },
        unit_price: 5,
      },
    ];

    render(
      <BookingOverview items={singlePersonTransfer} {...defaultProps} />
    );

    // Should show €5.00 (appears multiple times: group total, line item, grand total, remaining)
    expect(screen.getAllByText('€5.00').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText(/persons/i)).not.toBeInTheDocument();
  });

  // --- PDF Download Button Tests (Requirements 1.1, 1.5) ---

  beforeEach(() => {
    mockGenerateBookingPdf.mockReset();
    mockToast.mockReset();
  });

  it('shows download PDF button when items are present', () => {
    render(
      <BookingOverview items={mockItems} {...defaultProps} />
    );

    expect(screen.getByText('Download PDF')).toBeInTheDocument();
    expect(screen.getByTestId('download-icon')).toBeInTheDocument();
  });

  it('does not show download PDF button when items are empty', () => {
    render(
      <BookingOverview items={[]} {...defaultProps} />
    );

    expect(screen.queryByText('Download PDF')).not.toBeInTheDocument();
  });

  it('calls generateBookingPdf with correct data when button is clicked', () => {
    render(
      <BookingOverview
        items={mockItems}
        {...defaultProps}
        clubName="Harley Club Rotterdam"
        status="submitted"
        paymentStatus="partial"
        totalPaid={50}
        submittedAt="2025-06-15"
      />
    );

    fireEvent.click(screen.getByText('Download PDF'));

    expect(mockGenerateBookingPdf).toHaveBeenCalledTimes(1);
    expect(mockGenerateBookingPdf).toHaveBeenCalledWith({
      clubName: 'Harley Club Rotterdam',
      items: mockItems,
      status: 'submitted',
      paymentStatus: 'partial',
      totalAmount: 209.5, // 2×50 + 99.5 + 2×5
      totalPaid: 50,
      submittedAt: '2025-06-15',
    });
  });

  it('shows toast error notification when PDF generation fails', () => {
    mockGenerateBookingPdf.mockImplementation(() => {
      throw new Error('jsPDF error');
    });

    render(
      <BookingOverview items={mockItems} {...defaultProps} />
    );

    fireEvent.click(screen.getByText('Download PDF'));

    expect(mockToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'PDF generation failed',
        description: 'Could not generate PDF. Please try again.',
        status: 'error',
      })
    );
  });

  it('does not show toast when PDF generation succeeds', () => {
    mockGenerateBookingPdf.mockImplementation(() => {});

    render(
      <BookingOverview items={mockItems} {...defaultProps} />
    );

    fireEvent.click(screen.getByText('Download PDF'));

    expect(mockToast).not.toHaveBeenCalled();
  });
});

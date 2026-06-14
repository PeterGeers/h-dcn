/**
 * Unit tests for BookingSummaryPdf component.
 *
 * Tests:
 * - PDF generation with person-centric data
 * - Download button renders at all order statuses
 * - Filename generation
 *
 * Validates: Requirements 11.10, 11.11
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import BookingSummaryPdf, {
  buildFilename,
  generateBookingSummaryPdf,
} from '../BookingSummaryPdf';
import { Event, Order, Product } from '../../types/presmeet.types';

// --- Mock jsPDF ---

let mockTextCalls: string[] = [];
const mockSave = jest.fn();

jest.mock('jspdf', () => ({
  __esModule: true,
  jsPDF: function MockJsPDF() {
    return {
      setFontSize: jest.fn(),
      setFont: jest.fn(),
      text: (text: string) => {
        mockTextCalls.push(text);
      },
      save: mockSave,
      lastAutoTable: { finalY: 100 },
    };
  },
}));

jest.mock('jspdf-autotable', () => ({
  __esModule: true,
  default: (doc: any) => {
    doc.lastAutoTable = { finalY: 100 };
  },
}));

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, string>) => {
      if (params) {
        let result = key;
        Object.entries(params).forEach(([k, v]) => {
          result = result.replace(`{{${k}}}`, v);
        });
        // For known keys, return a readable label
        const labels: Record<string, string> = {
          'pdf.download_button': 'Download Booking Summary',
          'pdf.club': `Club: ${params.clubId || ''}`,
          'pdf.location': `Location: ${params.location || ''}`,
          'pdf.event_dates': `Event dates: ${params.start || ''} – ${params.end || ''}`,
          'pdf.total': `Total: ${params.amount || ''}`,
          'pdf.payment_status': `Payment status: ${params.status || ''}`,
          'pdf.order_status': `Order status: ${params.status || ''}`,
          'pdf.generated': `Generated: ${params.date || ''}`,
        };
        return labels[key] || result;
      }
      const staticLabels: Record<string, string> = {
        'pdf.download_button': 'Download Booking Summary',
        'pdf.no_items': 'No items in this booking.',
        'pdf.col_person': 'Person',
        'pdf.col_role': 'Role',
        'pdf.col_product': 'Product',
        'pdf.col_variant': 'Variant',
        'pdf.col_fields': 'Fields',
        'pdf.col_price': 'Price',
      };
      return staticLabels[key] || key;
    },
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

/**
 * Mock t function matching useTranslation behavior for direct calls.
 */
const mockT = ((key: string, params?: Record<string, string>) => {
  if (params) {
    const labels: Record<string, string> = {
      'pdf.club': `Club: ${params.clubId || ''}`,
      'pdf.location': `Location: ${params.location || ''}`,
      'pdf.event_dates': `Event dates: ${params.start || ''} – ${params.end || ''}`,
      'pdf.total': `Total: ${params.amount || ''}`,
      'pdf.payment_status': `Payment status: ${params.status || ''}`,
      'pdf.order_status': `Order status: ${params.status || ''}`,
      'pdf.generated': `Generated: ${params.date || ''}`,
    };
    return labels[key] || key;
  }
  const staticLabels: Record<string, string> = {
    'pdf.no_items': 'No items in this booking.',
    'pdf.col_person': 'Person',
    'pdf.col_role': 'Role',
    'pdf.col_product': 'Product',
    'pdf.col_variant': 'Variant',
    'pdf.col_fields': 'Fields',
    'pdf.col_price': 'Price',
  };
  return staticLabels[key] || key;
}) as any;

// --- Test Data ---

const mockEvent: Event = {
  event_id: 'evt-1',
  event_type: 'presmeet',
  name: 'Presidents Meeting 2027',
  location: 'Hotel Amersfoort',
  status: 'open',
  start_date: '2027-06-20',
  end_date: '2027-06-22',
  registration_open: '2027-01-01',
  registration_close: '2027-05-01',
  payment_deadline: '2027-05-15',
  product_ids: ['prod-meeting', 'prod-party'],
  constraints: [],
  created_at: '2026-12-01T08:00:00Z',
  created_by: 'admin@h-dcn.nl',
};

const mockProducts: Product[] = [
  {
    product_id: 'prod-meeting',
    name: 'Meeting Ticket PM2027',
    event_id: 'evt-1',
    event_type: 'presmeet',
    price: 50.0,
    order_item_fields: [
      { id: 'name', label: 'Naam', type: 'text', required: true },
      { id: 'role', label: 'Functie', type: 'text', required: true },
    ],
    variant_schema: null,
    purchase_rules: { min_per_club: 1, max_per_club: 3, order_mode: 'persistent' },
  },
  {
    product_id: 'prod-party',
    name: 'Party Ticket PM2027',
    event_id: 'evt-1',
    event_type: 'presmeet',
    price: 25.0,
    order_item_fields: [
      { id: 'name', label: 'Naam', type: 'text', required: true },
    ],
    variant_schema: null,
    purchase_rules: { max_per_club: 13, order_mode: 'persistent' },
  },
];

const mockOrder: Order = {
  order_id: 'ord-1',
  source_id: 'evt-1',
  member_id: 'member-1',
  club_id: 'club-amsterdam',
  event_id: 'evt-1',
  event_type: 'presmeet',
  status: 'submitted',
  payment_status: 'unpaid',
  total_amount: 125.0,
  total_paid: 0,
  items: [
    {
      product_id: 'prod-meeting',
      variant_id: null,
      item_fields_data: { name: 'Jan de Vries', role: 'President' },
      unit_price: 50.0,
      line_total: 50.0,
    },
    {
      product_id: 'prod-party',
      variant_id: null,
      item_fields_data: { name: 'Jan de Vries' },
      unit_price: 25.0,
      line_total: 25.0,
    },
    {
      product_id: 'prod-meeting',
      variant_id: null,
      item_fields_data: { name: 'Piet Jansen', role: 'Treasurer' },
      unit_price: 50.0,
      line_total: 50.0,
    },
  ],
  delegates: { primary: 'jan@club.nl', secondary: null },
  version: 3,
  status_history: [],
  created_at: '2027-01-10T08:00:00Z',
  updated_at: '2027-01-15T10:30:00Z',
  submitted_at: '2027-01-15T10:30:00Z',
  created_by: 'jan@club.nl',
};

// --- Helpers ---

function renderWithChakra(ui: React.ReactElement) {
  return render(<ChakraProvider>{ui}</ChakraProvider>);
}

// --- Tests ---

describe('BookingSummaryPdf', () => {
  beforeEach(() => {
    mockTextCalls = [];
    mockSave.mockClear();
  });

  describe('buildFilename', () => {
    it('creates a sanitized filename from club_id and event name', () => {
      const result = buildFilename('club-amsterdam', 'Presidents Meeting 2027');
      expect(result).toBe('presmeet-booking-club-amsterdam-presidents-meeting-2027.pdf');
    });

    it('strips special characters from event name', () => {
      const result = buildFilename('club-123', 'PM 2027 (Special!)');
      expect(result).toBe('presmeet-booking-club-123-pm-2027-special.pdf');
    });

    it('handles event name with only special characters', () => {
      const result = buildFilename('club-1', '---');
      expect(result).toBe('presmeet-booking-club-1-.pdf');
    });
  });

  describe('Component rendering', () => {
    it('renders download button', () => {
      renderWithChakra(
        <BookingSummaryPdf order={mockOrder} event={mockEvent} products={mockProducts} />
      );
      expect(screen.getByText('Download Booking Summary')).toBeInTheDocument();
    });

    it.each(['draft', 'submitted', 'locked'] as const)(
      'renders button when order status is %s',
      (status) => {
        const order = { ...mockOrder, status };
        renderWithChakra(
          <BookingSummaryPdf order={order} event={mockEvent} products={mockProducts} />
        );
        expect(screen.getByText('Download Booking Summary')).toBeInTheDocument();
      }
    );

    it('triggers PDF generation on click', () => {
      renderWithChakra(
        <BookingSummaryPdf order={mockOrder} event={mockEvent} products={mockProducts} />
      );
      fireEvent.click(screen.getByText('Download Booking Summary'));
      expect(mockSave).toHaveBeenCalledTimes(1);
    });

    it('generates PDF with correct filename', () => {
      renderWithChakra(
        <BookingSummaryPdf order={mockOrder} event={mockEvent} products={mockProducts} />
      );
      fireEvent.click(screen.getByText('Download Booking Summary'));
      expect(mockSave).toHaveBeenCalledWith(
        'presmeet-booking-club-amsterdam-presidents-meeting-2027.pdf'
      );
    });
  });

  describe('generateBookingSummaryPdf', () => {
    it('includes event name in the PDF', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('Presidents Meeting 2027');
    });

    it('includes club ID in the PDF', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('Club: club-amsterdam');
    });

    it('includes payment status', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('Payment status: unpaid');
    });

    it('includes order status', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('Order status: submitted');
    });

    it('includes total amount', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      // formatCurrency uses nl-NL locale: "€ 125,00"
      const totalText = mockTextCalls.find((t) => t.startsWith('Total:'));
      expect(totalText).toBeDefined();
    });

    it('includes event location', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('Location: Hotel Amersfoort');
    });

    it('includes event dates', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('Event dates: 2027-06-20 – 2027-06-22');
    });

    it('handles empty order items gracefully', () => {
      const emptyOrder = { ...mockOrder, items: [] };
      generateBookingSummaryPdf(emptyOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('No items in this booking.');
    });
  });
});

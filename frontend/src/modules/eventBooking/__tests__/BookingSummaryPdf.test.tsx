/**
 * Unit tests for BookingSummaryPdf component.
 *
 * Tests:
 * - PDF generation with person-centric data
 * - Download button renders at all order statuses
 * - Filename generation
 * - Validation checks at PDF generation time (Req 12.3)
 * - Disclaimer with locale-formatted date-time (Req 12.4)
 * - Draft with no persons shows indication (Req 12.5)
 * - Delegate info included (Req 12.2)
 *
 * Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import BookingSummaryPdf, {
  buildFilename,
  generateBookingSummaryPdf,
  runValidationChecks,
} from '../components/BookingSummaryPdf';
import { Event, Order, Product } from '../types/eventBooking.types';

// --- Mock jsPDF ---

let mockTextCalls: string[] = [];
const mockSave = jest.fn();

jest.mock('jspdf', () => ({
  __esModule: true,
  jsPDF: function MockJsPDF() {
    return {
      setFontSize: jest.fn(),
      setFont: jest.fn(),
      setTextColor: jest.fn(),
      addPage: jest.fn(),
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
        const labels: Record<string, string> = {
          'pdf.download_button': 'Download Booking Summary',
          'pdf.row_label': `${params.rowLabel || 'Club'}: ${params.name || ''}`,
          'pdf.row_label_default': 'Club',
          'pdf.location': `Location: ${params.location || ''}`,
          'pdf.event_dates': `Event dates: ${params.start || ''} – ${params.end || ''}`,
          'pdf.total': `Total: ${params.amount || ''}`,
          'pdf.payment_status': `Payment status: ${params.status || ''}`,
          'pdf.order_status': `Order status: ${params.status || ''}`,
          'pdf.delegate_primary': `Primary delegate: ${params.email || ''}`,
          'pdf.delegate_secondary': `Secondary delegate: ${params.email || ''}`,
          'pdf.delegate_pending': `Pending invitation: ${params.email || ''}`,
          'pdf.generated': `Generated: ${params.date || ''}`,
          'pdf.disclaimer': `Generated on ${params.datetime || ''}. Products and availability subject to change.`,
          'pdf.validation_issues_title': `Validation issues (${params.count || ''}):`,
          'pdf.validation_field_required': `${params.field || ''} is required`,
          'pdf.validation_quantity_exceeded': `${params.product || ''}: ${params.count || ''} selected, max ${params.max || ''} allowed`,
          'pdf.validation_person_unnamed': `Person ${params.index || ''}`,
        };
        return labels[key] || key;
      }
      const staticLabels: Record<string, string> = {
        'pdf.download_button': 'Download Booking Summary',
        'pdf.row_label_default': 'Club',
        'pdf.no_items': 'No items in this booking.',
        'pdf.no_persons_yet': 'No persons have been added yet.',
        'pdf.col_person': 'Person',
        'pdf.col_role': 'Role',
        'pdf.col_product': 'Product',
        'pdf.col_variant': 'Variant',
        'pdf.col_fields': 'Fields',
        'pdf.col_price': 'Price',
        'pdf.validation_valid': '✓ Order is valid at this moment',
        'pdf.validation_name_empty': 'Name is required',
        'pdf.validation_variant_missing': 'Variant selection is required',
        'pdf.validation_variant_invalid': 'Selected variant is invalid',
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
      'pdf.row_label': `${params.rowLabel || 'Club'}: ${params.name || ''}`,
      'pdf.row_label_default': 'Club',
      'pdf.location': `Location: ${params.location || ''}`,
      'pdf.event_dates': `Event dates: ${params.start || ''} – ${params.end || ''}`,
      'pdf.total': `Total: ${params.amount || ''}`,
      'pdf.payment_status': `Payment status: ${params.status || ''}`,
      'pdf.order_status': `Order status: ${params.status || ''}`,
      'pdf.delegate_primary': `Primary delegate: ${params.email || ''}`,
      'pdf.delegate_secondary': `Secondary delegate: ${params.email || ''}`,
      'pdf.delegate_pending': `Pending invitation: ${params.email || ''}`,
      'pdf.generated': `Generated: ${params.date || ''}`,
      'pdf.disclaimer': `Generated on ${params.datetime || ''}. Products and availability subject to change.`,
      'pdf.validation_issues_title': `Validation issues (${params.count || ''}):`,
      'pdf.validation_field_required': `${params.field || ''} is required`,
      'pdf.validation_quantity_exceeded': `${params.product || ''}: ${params.count || ''} selected, max ${params.max || ''} allowed`,
      'pdf.validation_person_unnamed': `Person ${params.index || ''}`,
    };
    return labels[key] || key;
  }
  const staticLabels: Record<string, string> = {
    'pdf.row_label_default': 'Club',
    'pdf.no_items': 'No items in this booking.',
    'pdf.no_persons_yet': 'No persons have been added yet.',
    'pdf.col_person': 'Person',
    'pdf.col_role': 'Role',
    'pdf.col_product': 'Product',
    'pdf.col_variant': 'Variant',
    'pdf.col_fields': 'Fields',
    'pdf.col_price': 'Price',
    'pdf.validation_valid': '✓ Order is valid at this moment',
    'pdf.validation_name_empty': 'Name is required',
    'pdf.validation_variant_missing': 'Variant selection is required',
    'pdf.validation_variant_invalid': 'Selected variant is invalid',
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
    naam: 'Meeting Ticket PM2027',
    event_id: 'evt-1',
    event_type: 'presmeet',
    prijs: 50.0,
    order_item_fields: [
      { id: 'name', label: 'Naam', type: 'text', required: true },
      { id: 'role', label: 'Functie', type: 'text', required: true },
    ],
    variant_schema: null,
    purchase_rules: { min_per_order: 1, max_per_order: 3 },
  },
  {
    product_id: 'prod-party',
    naam: 'Party Ticket PM2027',
    event_id: 'evt-1',
    event_type: 'presmeet',
    prijs: 25.0,
    order_item_fields: [
      { id: 'name', label: 'Naam', type: 'text', required: true },
    ],
    variant_schema: null,
    purchase_rules: { max_per_order: 13 },
  },
];

const mockOrder: Order = {
  order_id: 'ord-1',
  source_id: 'evt-1',
  member_id: 'member-1',
  registry_row_id: 'club-amsterdam',
  registry_row_label: 'Club Amsterdam',
  registry_row_logo_url: null,
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
  delegates: {
    primary: 'jan@club.nl',
    secondary: 'piet@club.nl',
    pending_secondary_email: null,
  },
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
    it('creates a sanitized filename from registry_row_label and event name', () => {
      const result = buildFilename('Club Amsterdam', 'Presidents Meeting 2027');
      expect(result).toBe('booking-club-amsterdam-presidents-meeting-2027.pdf');
    });

    it('strips special characters from event name', () => {
      const result = buildFilename('Club 123', 'PM 2027 (Special!)');
      expect(result).toBe('booking-club-123-pm-2027-special.pdf');
    });

    it('handles event name with only special characters', () => {
      const result = buildFilename('Club 1', '---');
      expect(result).toBe('booking-club-1-unknown.pdf');
    });

    it('falls back to "unknown" when registry_row_label is null', () => {
      const result = buildFilename(null, 'Test Event');
      expect(result).toBe('booking-unknown-test-event.pdf');
    });

    it('falls back to "unknown" when registry_row_label is empty string', () => {
      const result = buildFilename('', 'Test Event');
      expect(result).toBe('booking-unknown-test-event.pdf');
    });

    it('falls back to "unknown" when registry_row_label is undefined', () => {
      const result = buildFilename(undefined, 'Test Event');
      expect(result).toBe('booking-unknown-test-event.pdf');
    });

    it('collapses consecutive hyphens', () => {
      const result = buildFilename('Club---Amsterdam', 'Event   Name');
      expect(result).toBe('booking-club-amsterdam-event-name.pdf');
    });
  });

  describe('Component rendering (Requirement 12.1)', () => {
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
        'booking-club-amsterdam-presidents-meeting-2027.pdf'
      );
    });
  });

  describe('generateBookingSummaryPdf (Requirement 12.2)', () => {
    it('includes event name in the PDF', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('Presidents Meeting 2027');
    });

    it('includes row label with registry_row_label', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT, 'team');
      expect(mockTextCalls).toContain('team: Club Amsterdam');
    });

    it('includes primary delegate email', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('Primary delegate: jan@club.nl');
    });

    it('includes secondary delegate email', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('Secondary delegate: piet@club.nl');
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
      const totalText = mockTextCalls.find((t) => t.startsWith('Total:'));
      expect(totalText).toBeDefined();
    });
  });

  describe('Validation checks (Requirement 12.3)', () => {
    it('shows valid when order passes all checks', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('✓ Order is valid at this moment');
    });

    it('shows validation issues when person name is empty', () => {
      const invalidOrder = {
        ...mockOrder,
        items: [
          {
            product_id: 'prod-meeting',
            variant_id: null,
            item_fields_data: { name: '', role: 'President' },
            unit_price: 50.0,
            line_total: 50.0,
          },
        ],
      };
      generateBookingSummaryPdf(invalidOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls.some((t) => t.includes('Validation issues'))).toBe(true);
    });

    it('detects missing required fields', () => {
      const issues = runValidationChecks(
        {
          ...mockOrder,
          items: [
            {
              product_id: 'prod-meeting',
              variant_id: null,
              item_fields_data: { name: 'Jan', role: '' },
              unit_price: 50.0,
              line_total: 50.0,
            },
          ],
        },
        mockProducts,
        mockT
      );
      // role is required on prod-meeting
      expect(issues.some((i) => i.field === 'Functie')).toBe(true);
    });

    it('detects quantity limit exceeded', () => {
      const orderWithTooMany = {
        ...mockOrder,
        items: [
          { product_id: 'prod-meeting', variant_id: null, item_fields_data: { name: 'A', role: 'R1' }, unit_price: 50, line_total: 50 },
          { product_id: 'prod-meeting', variant_id: null, item_fields_data: { name: 'B', role: 'R2' }, unit_price: 50, line_total: 50 },
          { product_id: 'prod-meeting', variant_id: null, item_fields_data: { name: 'C', role: 'R3' }, unit_price: 50, line_total: 50 },
          { product_id: 'prod-meeting', variant_id: null, item_fields_data: { name: 'D', role: 'R4' }, unit_price: 50, line_total: 50 },
        ],
      };
      const issues = runValidationChecks(orderWithTooMany, mockProducts, mockT);
      expect(issues.some((i) => i.message.includes('selected, max'))).toBe(true);
    });

    it('returns no issues for a valid order', () => {
      const issues = runValidationChecks(mockOrder, mockProducts, mockT);
      expect(issues).toHaveLength(0);
    });
  });

  describe('Disclaimer (Requirement 12.4)', () => {
    it('includes disclaimer with date-time', () => {
      generateBookingSummaryPdf(mockOrder, mockEvent, mockProducts, mockT);
      const disclaimerText = mockTextCalls.find((t) =>
        t.includes('Products and availability subject to change')
      );
      expect(disclaimerText).toBeDefined();
      expect(disclaimerText).toContain('Generated on');
    });
  });

  describe('Draft with no persons (Requirement 12.5)', () => {
    it('shows no-persons indication for empty draft order', () => {
      const emptyDraftOrder: Order = {
        ...mockOrder,
        status: 'draft',
        items: [],
      };
      generateBookingSummaryPdf(emptyDraftOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('No persons have been added yet.');
    });

    it('still includes event name and delegates for empty draft', () => {
      const emptyDraftOrder: Order = {
        ...mockOrder,
        status: 'draft',
        items: [],
      };
      generateBookingSummaryPdf(emptyDraftOrder, mockEvent, mockProducts, mockT);
      expect(mockTextCalls).toContain('Presidents Meeting 2027');
      expect(mockTextCalls).toContain('Primary delegate: jan@club.nl');
    });
  });
});

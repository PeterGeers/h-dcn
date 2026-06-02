/**
 * AdminDashboard component tests.
 *
 * Validates: Requirements 7.1, 7.6, 7.7
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import AdminDashboard from '../components/AdminDashboard';
import { ReportOverview, ReportOrderEntry } from '../types/presmeet';

// Mock presmeetService
const mockGetReport = jest.fn();
const mockGenerateReport = jest.fn();
const mockLockOrders = jest.fn();
const mockUnlockOrder = jest.fn();
const mockGetReportCsv = jest.fn();
const mockRecordPayment = jest.fn();

jest.mock('../services/presmeetApi', () => ({
  presmeetService: {
    getReport: (...args: any[]) => mockGetReport(...args),
    generateReport: (...args: any[]) => mockGenerateReport(...args),
    lockOrders: (...args: any[]) => mockLockOrders(...args),
    unlockOrder: (...args: any[]) => mockUnlockOrder(...args),
    getReportCsv: (...args: any[]) => mockGetReportCsv(...args),
    recordPayment: (...args: any[]) => mockRecordPayment(...args),
  },
}));

// Mock Chakra UI
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  VStack: ({ children }: any) => <div>{children}</div>,
  HStack: ({ children }: any) => <div style={{ display: 'flex' }}>{children}</div>,
  Text: ({ children }: any) => <span>{children}</span>,
  Heading: ({ children }: any) => <h2>{children}</h2>,
  Button: ({ children, onClick, isDisabled, isLoading, ...props }: any) => (
    <button onClick={onClick} disabled={isDisabled || isLoading} {...props}>
      {children}
    </button>
  ),
  Table: ({ children }: any) => <table>{children}</table>,
  Thead: ({ children }: any) => <thead>{children}</thead>,
  Tbody: ({ children }: any) => <tbody>{children}</tbody>,
  Tr: ({ children }: any) => <tr>{children}</tr>,
  Th: ({ children }: any) => <th>{children}</th>,
  Td: ({ children }: any) => <td>{children}</td>,
  Badge: ({ children }: any) => <span>{children}</span>,
  Stat: ({ children }: any) => <div>{children}</div>,
  StatLabel: ({ children }: any) => <span>{children}</span>,
  StatNumber: ({ children }: any) => <span>{children}</span>,
  StatGroup: ({ children }: any) => <div>{children}</div>,
  Spinner: () => <span data-testid="spinner">Loading...</span>,
  Alert: ({ children }: any) => <div role="alert">{children}</div>,
  AlertIcon: () => <span />,
  AlertTitle: ({ children }: any) => <strong>{children}</strong>,
  AlertDescription: ({ children }: any) => <span>{children}</span>,
  Modal: ({ children, isOpen }: any) => isOpen ? <div role="dialog">{children}</div> : null,
  ModalOverlay: () => null,
  ModalContent: ({ children }: any) => <div>{children}</div>,
  ModalHeader: ({ children }: any) => <h3>{children}</h3>,
  ModalBody: ({ children }: any) => <div>{children}</div>,
  ModalFooter: ({ children }: any) => <div>{children}</div>,
  ModalCloseButton: () => <button aria-label="Close" />,
  useDisclosure: () => ({ isOpen: false, onOpen: jest.fn(), onClose: jest.fn() }),
  FormControl: ({ children }: any) => <div>{children}</div>,
  FormLabel: ({ children }: any) => <label>{children}</label>,
  Input: (props: any) => <input {...props} />,
  Textarea: (props: any) => <textarea {...props} />,
  Tooltip: ({ children }: any) => <>{children}</>,
  useToast: () => jest.fn(),
}));

const mockOverview: ReportOverview = {
  generated_at: '2025-09-10T14:30:00Z',
  generated_by: 'admin@h-dcn.nl',
  summary: {
    total_orders: 45,
    by_status: { draft: 10, submitted: 25, locked: 10 },
    by_product_type: {
      meeting_ticket: { draft: 15, submitted: 50, locked: 20 },
      party_ticket: { draft: 20, submitted: 80, locked: 35 },
      tshirt: { draft: 8, submitted: 40, locked: 15 },
      airport_transfer: { draft: 5, submitted: 30, locked: 12 },
    },
  },
  payments: {
    total_charged: 15000.0,
    total_paid: 12500.0,
    total_outstanding: 2500.0,
  },
};

const mockOrders: ReportOrderEntry[] = [
  {
    order_id: 'order-1',
    club_id: 'club_123',
    club_name: 'HD Club Amsterdam',
    status: 'submitted',
    payment_status: 'partial',
    total_amount: 350.0,
    total_paid: 200.0,
    outstanding: 150.0,
    item_counts: {
      meeting_ticket: 2,
      party_ticket: 4,
      tshirt: 3,
      airport_transfer: 1,
    },
    created_at: '2025-08-01T10:00:00Z',
    updated_at: '2025-08-15T12:00:00Z',
    submitted_at: '2025-08-15T12:00:00Z',
  },
  {
    order_id: 'order-2',
    club_id: 'club_456',
    club_name: 'HD Club Rotterdam',
    status: 'locked',
    payment_status: 'paid',
    total_amount: 500.0,
    total_paid: 500.0,
    outstanding: 0.0,
    item_counts: {
      meeting_ticket: 3,
      party_ticket: 6,
      tshirt: 2,
      airport_transfer: 0,
    },
    created_at: '2025-08-02T10:00:00Z',
    updated_at: '2025-08-16T12:00:00Z',
    submitted_at: '2025-08-16T12:00:00Z',
  },
];

describe('AdminDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows access denied for non-admin', () => {
    render(<AdminDashboard isAdmin={false} />);

    expect(screen.getByText('Access Denied')).toBeInTheDocument();
    expect(screen.getByText(/Admin access required/)).toBeInTheDocument();
  });

  it('renders payment statistics', async () => {
    mockGetReport.mockImplementation((type: string) => {
      if (type === 'overview') {
        return Promise.resolve({ success: true, data: mockOverview });
      }
      if (type === 'orders') {
        return Promise.resolve({
          success: true,
          data: { generated_at: '2025-09-10T14:30:00Z', orders: mockOrders },
        });
      }
      return Promise.resolve({ success: false });
    });

    render(<AdminDashboard isAdmin={true} />);

    await waitFor(() => {
      expect(screen.getByText('Payment Statistics')).toBeInTheDocument();
      expect(screen.getByText('€15000.00')).toBeInTheDocument();
      expect(screen.getByText('€12500.00')).toBeInTheDocument();
      expect(screen.getByText('€2500.00')).toBeInTheDocument();
    });
  });

  it('renders order list', async () => {
    mockGetReport.mockImplementation((type: string) => {
      if (type === 'overview') {
        return Promise.resolve({ success: true, data: mockOverview });
      }
      if (type === 'orders') {
        return Promise.resolve({
          success: true,
          data: { generated_at: '2025-09-10T14:30:00Z', orders: mockOrders },
        });
      }
      return Promise.resolve({ success: false });
    });

    render(<AdminDashboard isAdmin={true} />);

    await waitFor(() => {
      expect(screen.getByText('HD Club Amsterdam')).toBeInTheDocument();
      expect(screen.getByText('HD Club Rotterdam')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    mockGetReport.mockImplementation(() => new Promise(() => {})); // never resolves

    render(<AdminDashboard isAdmin={true} />);

    expect(screen.getByText('Loading report data...')).toBeInTheDocument();
  });
});

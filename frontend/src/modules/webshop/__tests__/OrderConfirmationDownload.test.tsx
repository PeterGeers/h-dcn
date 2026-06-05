/**
 * OrderConfirmation Download Button Tests
 *
 * Tests for the download PDF button behavior in the OrderConfirmation component.
 * Validates: Requirements 7.1, 7.5, 7.6
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'confirmation.title': 'Orderbevestiging',
        'confirmation.download_pdf': 'Download PDF',
        'confirmation.downloading': 'Downloaden...',
        'confirmation.download_failed': 'Download mislukt',
        'confirmation.download_error_desc': 'Er is een onverwachte fout opgetreden. Probeer het opnieuw.',
        'confirmation.order_number': 'Ordernummer',
        'confirmation.date': 'Datum',
        'confirmation.customer': 'Klant',
        'confirmation.status': 'Status',
        'confirmation.status_paid': 'Betaald',
        'confirmation.not_available': 'Niet beschikbaar',
        'confirmation.billing_address': 'Factuuradres',
        'confirmation.shipping_address': 'Verzendadres',
        'confirmation.name_not_available': 'Naam niet beschikbaar',
        'confirmation.address_not_available': 'Adres niet beschikbaar',
        'confirmation.postal_not_available': 'Postcode/plaats niet beschikbaar',
        'confirmation.no_address': 'Geen adresgegevens beschikbaar',
        'confirmation.ordered_products': 'Bestelde producten',
        'confirmation.col_product': 'Product',
        'confirmation.col_option': 'Optie',
        'confirmation.col_quantity': 'Aantal',
        'confirmation.col_price': 'Prijs',
        'confirmation.col_total': 'Totaal',
        'confirmation.subtotal': 'Subtotaal',
        'confirmation.total_paid': 'Totaal betaald',
      };
      return translations[key] || key;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

// Mock Chakra UI components
const mockToast = jest.fn();
jest.mock('@chakra-ui/react', () => ({
  Button: ({ children, onClick, isDisabled, isLoading, loadingText, leftIcon, colorScheme, ...props }: any) => (
    <button
      onClick={onClick}
      disabled={isDisabled || isLoading}
      {...props}
    >
      {isLoading ? loadingText : children}
    </button>
  ),
  useToast: () => mockToast,
}));

jest.mock('@chakra-ui/icons', () => ({
  DownloadIcon: () => <span data-testid="download-icon" />,
}));

// Mock the PDF download service
jest.mock('../services/pdfDownloadService', () => ({
  downloadOrderPdf: jest.fn(),
}));

import { downloadOrderPdf } from '../services/pdfDownloadService';
import OrderConfirmation from '../components/OrderConfirmation';

const mockedDownloadOrderPdf = downloadOrderPdf as jest.MockedFunction<typeof downloadOrderPdf>;

const mockOrderData = {
  orderId: 'ORD-TEST-123',
  timestamp: '2025-01-15T14:30:00Z',
  customer_info: {
    name: 'Jan de Vries',
    straat: 'Kerkstraat 10',
    postcode: '1234 AB',
    woonplaats: 'Amsterdam',
    email: 'jan@example.com',
  },
  items: [
    { name: 'Product A', quantity: 2, price: 12.5 },
  ],
  subtotal_amount: '25.00',
  total_amount: '25.00',
};

describe('OrderConfirmation Download Button', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should call downloadOrderPdf with the correct orderId when clicked', async () => {
    mockedDownloadOrderPdf.mockResolvedValue({ success: true });

    render(<OrderConfirmation orderData={mockOrderData} />);

    const downloadButton = screen.getByRole('button', { name: /download pdf/i });
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(mockedDownloadOrderPdf).toHaveBeenCalledWith('ORD-TEST-123');
    });
  });

  test('should show loading state while downloading', async () => {
    // Create a promise that we control to simulate a slow download
    let resolveDownload: (value: { success: boolean }) => void;
    const downloadPromise = new Promise<{ success: boolean }>((resolve) => {
      resolveDownload = resolve;
    });
    mockedDownloadOrderPdf.mockReturnValue(downloadPromise);

    render(<OrderConfirmation orderData={mockOrderData} />);

    const downloadButton = screen.getByRole('button', { name: /download pdf/i });

    await act(async () => {
      fireEvent.click(downloadButton);
    });

    // Button should be disabled while loading and show loading text
    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
      expect(button).toHaveTextContent('Downloaden...');
    });

    // Resolve the download
    await act(async () => {
      resolveDownload!({ success: true });
    });

    // Button should be enabled again after download completes
    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).not.toBeDisabled();
      expect(button).toHaveTextContent('Download PDF');
    });
  });

  test('should show error toast when download fails', async () => {
    mockedDownloadOrderPdf.mockResolvedValue({
      success: false,
      error: {
        code: 'server_error' as const,
        message: 'De PDF kon niet worden gegenereerd. Probeer het later opnieuw.',
        statusCode: 500,
      },
    });

    render(<OrderConfirmation orderData={mockOrderData} />);

    const downloadButton = screen.getByRole('button', { name: /download pdf/i });

    await act(async () => {
      fireEvent.click(downloadButton);
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Download mislukt',
          description: 'De PDF kon niet worden gegenereerd. Probeer het later opnieuw.',
          status: 'error',
        })
      );
    });
  });

  test('should not render anything when orderData is null', () => {
    const { container } = render(<OrderConfirmation orderData={null} />);
    expect(container.innerHTML).toBe('');
  });
});

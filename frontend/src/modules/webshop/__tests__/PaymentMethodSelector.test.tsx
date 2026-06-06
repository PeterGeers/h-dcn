/**
 * PaymentMethodSelector Component Tests
 *
 * Tests for method selection, bank transfer instructions display,
 * and Mollie redirect handling (post-payment messaging).
 * Validates: Requirements 9.1–9.9
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      if (params) {
        return Object.entries(params).reduce(
          (str, [k, v]) => str.replace(`{{${k}}}`, String(v)),
          key
        );
      }
      return key;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

// Mock Chakra UI components - using module-level state for RadioGroup/Radio coordination
jest.mock('@chakra-ui/react', () => {
  // Module-scoped state that RadioGroup and Radio share
  let mockRadioState = { value: '', onChange: (_v: string) => {}, isDisabled: false };

  return {
    Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    VStack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    Text: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    Alert: ({ children, status, ...props }: any) => (
      <div data-testid={`alert-${status}`} role="alert" {...props}>
        {children}
      </div>
    ),
    AlertIcon: () => <span data-testid="alert-icon" />,
    AlertTitle: ({ children, ...props }: any) => <strong {...props}>{children}</strong>,
    AlertDescription: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    Button: ({ children, onClick, ...props }: any) => (
      <button onClick={onClick} {...props}>{children}</button>
    ),
    RadioGroup: ({ children, value, onChange, isDisabled }: any) => {
      mockRadioState = { value: value || '', onChange: onChange || (() => {}), isDisabled: !!isDisabled };
      return <div data-testid="radio-group">{children}</div>;
    },
    Radio: ({ children, value }: any) => (
      <label>
        <input
          type="radio"
          value={value}
          checked={mockRadioState.value === value}
          onChange={() => mockRadioState.onChange(value)}
          disabled={mockRadioState.isDisabled}
        />
        {children}
      </label>
    ),
    Stack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  };
});

import PaymentMethodSelector, {
  PaymentMethodSelectorProps,
} from '../components/PaymentMethodSelector';
import { PaymentReturnResult } from '../services/mollie';

const renderComponent = (props: Partial<PaymentMethodSelectorProps> = {}) => {
  const defaultProps: PaymentMethodSelectorProps = {
    selectedMethod: 'ideal',
    onMethodChange: jest.fn(),
    onRetry: jest.fn(),
    ...props,
  };

  let result: ReturnType<typeof render>;
  act(() => {
    result = render(<PaymentMethodSelector {...defaultProps} />);
  });
  return { ...result!, props: defaultProps };
};

describe('PaymentMethodSelector', () => {
  describe('method selection', () => {
    it('renders all three payment method options', () => {
      renderComponent();
      expect(screen.getByText('iDEAL')).toBeInTheDocument();
      expect(screen.getByText('Creditcard')).toBeInTheDocument();
      expect(screen.getByText('payment.bank_transfer')).toBeInTheDocument();
    });

    it('renders "Betaalmethode" heading', () => {
      renderComponent();
      expect(screen.getByText('payment.method_title')).toBeInTheDocument();
    });

    it('shows iDEAL as selected when selectedMethod is ideal', () => {
      renderComponent({ selectedMethod: 'ideal' });
      const radioButtons = screen.getAllByRole('radio');
      const idealRadio = radioButtons.find(r => (r as HTMLInputElement).value === 'ideal');
      expect(idealRadio).toBeChecked();
    });

    it('shows creditcard as selected when selectedMethod is creditcard', () => {
      renderComponent({ selectedMethod: 'creditcard' });
      const radioButtons = screen.getAllByRole('radio');
      const ccRadio = radioButtons.find(r => (r as HTMLInputElement).value === 'creditcard');
      expect(ccRadio).toBeChecked();
    });

    it('shows bank_transfer as selected when selectedMethod is bank_transfer', () => {
      renderComponent({ selectedMethod: 'bank_transfer' });
      const radioButtons = screen.getAllByRole('radio');
      const btRadio = radioButtons.find(r => (r as HTMLInputElement).value === 'bank_transfer');
      expect(btRadio).toBeChecked();
    });

    it('calls onMethodChange when a different method is selected', () => {
      const onMethodChange = jest.fn();
      renderComponent({ selectedMethod: 'ideal', onMethodChange });

      const radioButtons = screen.getAllByRole('radio');
      const ccRadio = radioButtons.find(r => (r as HTMLInputElement).value === 'creditcard');
      fireEvent.click(ccRadio!);

      expect(onMethodChange).toHaveBeenCalledWith('creditcard');
    });

    it('displays description text for each method', () => {
      renderComponent();
      expect(screen.getByText('payment.ideal_description')).toBeInTheDocument();
      expect(screen.getByText('payment.creditcard_description')).toBeInTheDocument();
      expect(screen.getByText('payment.bank_transfer_description')).toBeInTheDocument();
    });
  });

  describe('bank transfer instructions display', () => {
    it('shows transfer instructions when bank_transfer is selected and instructions are provided', () => {
      renderComponent({
        selectedMethod: 'bank_transfer',
        transferInstructions: {
          reference: 'ORD-2024-001234',
          iban: 'NL00BANK0123456789',
          amount: 45.0,
        },
      });

      expect(screen.getByText('payment.transfer_instructions_title')).toBeInTheDocument();
      expect(screen.getByText('ORD-2024-001234')).toBeInTheDocument();
      expect(screen.getByText('NL00BANK0123456789')).toBeInTheDocument();
      expect(screen.getByText('€45.00')).toBeInTheDocument();
    });

    it('does not show transfer instructions when ideal is selected', () => {
      renderComponent({
        selectedMethod: 'ideal',
        transferInstructions: {
          reference: 'ORD-2024-001234',
          iban: 'NL00BANK0123456789',
          amount: 45.0,
        },
      });

      expect(screen.queryByText('payment.transfer_instructions_title')).not.toBeInTheDocument();
    });

    it('does not show transfer instructions when no instructions are provided', () => {
      renderComponent({
        selectedMethod: 'bank_transfer',
        transferInstructions: undefined,
      });

      expect(screen.queryByText('payment.transfer_instructions_title')).not.toBeInTheDocument();
    });

    it('shows labels for reference, IBAN, and amount', () => {
      renderComponent({
        selectedMethod: 'bank_transfer',
        transferInstructions: {
          reference: 'REF-123',
          iban: 'NL99BANK0000000001',
          amount: 100.5,
        },
      });

      expect(screen.getByText('payment.reference')).toBeInTheDocument();
      expect(screen.getByText('IBAN:')).toBeInTheDocument();
      expect(screen.getByText('payment.amount')).toBeInTheDocument();
    });
  });

  describe('Mollie redirect handling (payment return)', () => {
    it('displays success message for successful payment return', () => {
      const paymentReturn: PaymentReturnResult = {
        status: 'success',
        orderId: 'order-123',
        message: 'Betaling succesvol! Je bestelling is bevestigd.',
        canRetry: false,
      };

      renderComponent({ paymentReturn });

      expect(screen.getByText('payment.return_success_title')).toBeInTheDocument();
      expect(
        screen.getByText('Betaling succesvol! Je bestelling is bevestigd.')
      ).toBeInTheDocument();
    });

    it('displays failed message for failed payment return', () => {
      const paymentReturn: PaymentReturnResult = {
        status: 'failed',
        orderId: 'order-123',
        message: 'De betaling is mislukt. Probeer het opnieuw of kies een andere betaalmethode.',
        canRetry: true,
      };

      renderComponent({ paymentReturn });

      expect(screen.getByText('payment.return_failed_title')).toBeInTheDocument();
      expect(
        screen.getByText(
          'De betaling is mislukt. Probeer het opnieuw of kies een andere betaalmethode.'
        )
      ).toBeInTheDocument();
    });

    it('shows retry button when canRetry is true', () => {
      const paymentReturn: PaymentReturnResult = {
        status: 'failed',
        orderId: null,
        message: 'Betaling mislukt',
        canRetry: true,
      };

      renderComponent({ paymentReturn });
      expect(screen.getByText('payment.retry_button')).toBeInTheDocument();
    });

    it('does not show retry button when canRetry is false', () => {
      const paymentReturn: PaymentReturnResult = {
        status: 'success',
        orderId: 'order-123',
        message: 'Success',
        canRetry: false,
      };

      renderComponent({ paymentReturn });
      expect(screen.queryByText('payment.retry_button')).not.toBeInTheDocument();
    });

    it('calls onRetry when retry button is clicked', () => {
      const onRetry = jest.fn();
      const paymentReturn: PaymentReturnResult = {
        status: 'failed',
        orderId: null,
        message: 'Betaling mislukt',
        canRetry: true,
      };

      renderComponent({ paymentReturn, onRetry });
      fireEvent.click(screen.getByText('payment.retry_button'));
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it('hides payment method selector when payment return is shown', () => {
      const paymentReturn: PaymentReturnResult = {
        status: 'success',
        orderId: 'order-123',
        message: 'Success',
        canRetry: false,
      };

      renderComponent({ paymentReturn });

      // The radio buttons should not be visible when payment return messaging is shown
      expect(screen.queryByText('payment.method_title')).not.toBeInTheDocument();
      expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    });

    it('uses success alert status for successful payment', () => {
      const paymentReturn: PaymentReturnResult = {
        status: 'success',
        orderId: 'order-123',
        message: 'Betaling gelukt',
        canRetry: false,
      };

      renderComponent({ paymentReturn });
      expect(screen.getByTestId('alert-success')).toBeInTheDocument();
    });

    it('uses warning alert status for failed payment', () => {
      const paymentReturn: PaymentReturnResult = {
        status: 'failed',
        orderId: null,
        message: 'Mislukt',
        canRetry: true,
      };

      renderComponent({ paymentReturn });
      expect(screen.getByTestId('alert-warning')).toBeInTheDocument();
    });
  });

  describe('disabled state', () => {
    it('disables radio buttons when isDisabled is true', () => {
      renderComponent({ isDisabled: true });
      const radioButtons = screen.getAllByRole('radio');
      radioButtons.forEach((radio) => {
        expect(radio).toBeDisabled();
      });
    });
  });
});

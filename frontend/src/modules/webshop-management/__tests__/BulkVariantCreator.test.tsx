/**
 * BulkVariantCreator Unit Tests
 *
 * Tests the single-axis bulk variant generator modal:
 * - Locks the axis-name input when exactly one axis exists (Requirement 3.2)
 * - Uses free-text axis input when zero axes exist (Requirement 3.1)
 * - Disables submit when axis empty or zero values entered (Requirement 3.6)
 * - Posts axis_name + normalized (trimmed, de-duped) values (Requirements 3.1, 3.2)
 * - Shows the live preview count of variants to be created (Requirement 3.7)
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-i18next — return readable strings with {{param}} interpolation,
// matching the established pattern in VariantEditModal.test.tsx.
const translationMap: Record<string, string> = {
  'bulkCreate.triggerButton': 'Bulk toevoegen',
  'bulkCreate.title': 'Varianten in bulk aanmaken',
  'bulkCreate.description': 'Varianten voor {{productName}}',
  'bulkCreate.axisLabel': 'As-naam',
  'bulkCreate.axisPlaceholder': 'Bijv. Maat, Kleur...',
  'bulkCreate.valuesLabel': 'Waarden',
  'bulkCreate.valuesPlaceholder': "Eén waarde per regel of gescheiden door komma's",
  'bulkCreate.preview': 'Er worden {{count}} varianten aangemaakt',
  'bulkCreate.axisEmpty': 'As-naam is verplicht',
  'bulkCreate.cancel': 'Annuleren',
  'bulkCreate.submit': 'Aanmaken',
  'bulkCreate.submitting': 'Bezig...',
  'bulkCreate.toast.successTitle': 'Varianten aangemaakt',
  'bulkCreate.toast.successDesc': '{{created}} aangemaakt, {{skipped}} overgeslagen',
  'bulkCreate.toast.errorTitle': 'Fout bij aanmaken',
  'bulkCreate.toast.unknownError': 'Onbekende fout',
};
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      const value = translationMap[key] || key;
      if (params) {
        return Object.entries(params).reduce(
          (str, [k, v]) => str.replace(`{{${k}}}`, String(v)),
          value
        );
      }
      return value;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

// Mock Chakra UI icons — @chakra-ui/icons calls createIcon() from the real
// @chakra-ui/react at import time, which the lightweight Chakra mock below does
// not provide. Same pattern as MemberFilters.test.tsx / ProductCard.test.tsx.
jest.mock('@chakra-ui/icons', () => ({
  AddIcon: () => <span data-testid="add-icon" />,
}));

// Mock toast
const mockToast = jest.fn();

// Mock Chakra UI — lightweight components. useDisclosure uses real React state
// so the trigger button genuinely opens/closes the modal.
jest.mock('@chakra-ui/react', () => {
  const ReactActual = require('react');
  return {
    useDisclosure: () => {
      const [isOpen, setIsOpen] = ReactActual.useState(false);
      return {
        isOpen,
        onOpen: () => setIsOpen(true),
        onClose: () => setIsOpen(false),
      };
    },
    useToast: () => mockToast,
    Modal: ({ children, isOpen }: any) =>
      isOpen ? <div data-testid="modal">{children}</div> : null,
    ModalOverlay: () => <div data-testid="modal-overlay" />,
    ModalContent: ({ children }: any) => <div data-testid="modal-content">{children}</div>,
    ModalHeader: ({ children }: any) => <h2 data-testid="modal-header">{children}</h2>,
    ModalBody: ({ children }: any) => <div data-testid="modal-body">{children}</div>,
    ModalFooter: ({ children }: any) => <div data-testid="modal-footer">{children}</div>,
    ModalCloseButton: ({ isDisabled }: any) => (
      <button aria-label="Close" disabled={isDisabled} />
    ),
    Button: ({
      children,
      onClick,
      isLoading,
      isDisabled,
      loadingText,
      colorScheme,
      variant,
      ...props
    }: any) => (
      <button onClick={onClick} disabled={isDisabled || isLoading} {...props}>
        {isLoading ? loadingText || 'Loading...' : children}
      </button>
    ),
    FormControl: ({ children }: any) => <div>{children}</div>,
    FormLabel: ({ children }: any) => <label>{children}</label>,
    VStack: ({ children }: any) => <div>{children}</div>,
    Text: ({ children }: any) => <span>{children}</span>,
    Input: ({ value, onChange, placeholder, isReadOnly, bg, cursor, size, ...props }: any) => (
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        readOnly={isReadOnly}
        {...props}
      />
    ),
    Textarea: ({ value, onChange, placeholder, rows, size, ...props }: any) => (
      <textarea
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        rows={rows}
        {...props}
      />
    ),
  };
});

// Mock adminApi.bulkCreateVariants
const mockBulkCreateVariants = jest.fn();
jest.mock('../services/adminApi', () => ({
  bulkCreateVariants: (...args: any[]) => mockBulkCreateVariants(...args),
}));

import { BulkVariantCreator } from '../components/BulkVariantCreator';
import { AdminVariant } from '../types/admin.types';

// --- Test helpers ---

const createMockVariant = (
  attributes: Record<string, string>,
  overrides: Partial<AdminVariant> = {}
): AdminVariant => ({
  product_id: `var_${Math.random().toString(36).slice(2)}`,
  parent_id: 'prod_123',
  variant_attributes: attributes,
  prijs: null,
  stock: 10,
  sold_count: 0,
  allow_oversell: false,
  active: true,
  ...overrides,
});

const defaultProps = {
  productId: 'prod_123',
  productName: 'T-shirt',
  existingVariants: [] as AdminVariant[],
  onSuccess: jest.fn(),
};

/** Render the component and click the trigger button to open the modal. */
const openModal = (props = defaultProps) => {
  const utils = render(<BulkVariantCreator {...props} />);
  const trigger = screen.getByText('Bulk toevoegen');
  fireEvent.click(trigger);
  return utils;
};

describe('BulkVariantCreator', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockBulkCreateVariants.mockResolvedValue({
      created: 0,
      skipped: [],
      default_variant_removed: false,
    });
  });

  describe('Trigger button', () => {
    it('renders the trigger button and does not show the modal initially', () => {
      render(<BulkVariantCreator {...defaultProps} />);
      expect(screen.getByText('Bulk toevoegen')).toBeInTheDocument();
      expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
    });

    it('opens the modal when the trigger is clicked', () => {
      openModal();
      expect(screen.getByTestId('modal')).toBeInTheDocument();
    });

    it('disables the trigger when isDisabled is true', () => {
      render(<BulkVariantCreator {...defaultProps} isDisabled />);
      expect(screen.getByText('Bulk toevoegen')).toBeDisabled();
    });
  });

  describe('Axis input locking (Requirements 3.1, 3.2)', () => {
    it('locks the axis-name input and pre-fills it when exactly one axis exists', () => {
      const existingVariants = [
        createMockVariant({ Maat: 'S' }),
        createMockVariant({ Maat: 'M' }),
      ];
      openModal({ ...defaultProps, existingVariants });

      const axisInput = screen.getByPlaceholderText('Bijv. Maat, Kleur...') as HTMLInputElement;
      expect(axisInput).toHaveValue('Maat');
      expect(axisInput).toHaveAttribute('readonly');
    });

    it('uses a free-text (editable) axis input when zero axes exist', () => {
      openModal({ ...defaultProps, existingVariants: [] });

      const axisInput = screen.getByPlaceholderText('Bijv. Maat, Kleur...') as HTMLInputElement;
      expect(axisInput).toHaveValue('');
      expect(axisInput).not.toHaveAttribute('readonly');

      fireEvent.change(axisInput, { target: { value: 'Kleur' } });
      expect(axisInput).toHaveValue('Kleur');
    });
  });

  describe('Submit disabling (Requirement 3.6)', () => {
    it('disables submit when the axis name is empty', () => {
      openModal({ ...defaultProps, existingVariants: [] });

      // Enter values but leave the axis empty.
      const valuesInput = screen.getByPlaceholderText("Eén waarde per regel of gescheiden door komma's");
      fireEvent.change(valuesInput, { target: { value: 'S\nM\nL' } });

      expect(screen.getByText('Aanmaken')).toBeDisabled();
    });

    it('disables submit when zero values remain after normalization', () => {
      openModal({ ...defaultProps, existingVariants: [] });

      const axisInput = screen.getByPlaceholderText('Bijv. Maat, Kleur...');
      fireEvent.change(axisInput, { target: { value: 'Maat' } });

      // Only whitespace / empty lines -> normalizes to zero values.
      const valuesInput = screen.getByPlaceholderText("Eén waarde per regel of gescheiden door komma's");
      fireEvent.change(valuesInput, { target: { value: '   \n\n  ' } });

      expect(screen.getByText('Aanmaken')).toBeDisabled();
    });

    it('enables submit once an axis name and at least one value are present', () => {
      openModal({ ...defaultProps, existingVariants: [] });

      const axisInput = screen.getByPlaceholderText('Bijv. Maat, Kleur...');
      fireEvent.change(axisInput, { target: { value: 'Maat' } });

      const valuesInput = screen.getByPlaceholderText("Eén waarde per regel of gescheiden door komma's");
      fireEvent.change(valuesInput, { target: { value: 'S' } });

      expect(screen.getByText('Aanmaken')).not.toBeDisabled();
    });
  });

  describe('Submission (Requirements 3.1, 3.2)', () => {
    it('posts axis_name and normalized (trimmed, de-duped) values', async () => {
      openModal({ ...defaultProps, existingVariants: [] });

      const axisInput = screen.getByPlaceholderText('Bijv. Maat, Kleur...');
      fireEvent.change(axisInput, { target: { value: '  Maat  ' } });

      // Includes whitespace, blank lines, and a duplicate.
      const valuesInput = screen.getByPlaceholderText("Eén waarde per regel of gescheiden door komma's");
      fireEvent.change(valuesInput, {
        target: { value: ' S \nM\n\nS\n  L  ' },
      });

      await act(async () => {
        fireEvent.click(screen.getByText('Aanmaken'));
      });

      await waitFor(() => {
        expect(mockBulkCreateVariants).toHaveBeenCalledWith('prod_123', {
          axis_name: 'Maat',
          values: ['S', 'M', 'L'],
        });
      });
    });

    it('accepts comma-separated values (split on commas and newlines)', async () => {
      openModal({ ...defaultProps, existingVariants: [] });

      fireEvent.change(screen.getByPlaceholderText('Bijv. Maat, Kleur...'), {
        target: { value: 'Maat' },
      });

      // Mixed comma + newline input with spaces and a duplicate.
      fireEvent.change(
        screen.getByPlaceholderText("Eén waarde per regel of gescheiden door komma's"),
        { target: { value: 'S, M , L\nXL, S' } }
      );

      await act(async () => {
        fireEvent.click(screen.getByText('Aanmaken'));
      });

      await waitFor(() => {
        expect(mockBulkCreateVariants).toHaveBeenCalledWith('prod_123', {
          axis_name: 'Maat',
          values: ['S', 'M', 'L', 'XL'],
        });
      });
    });

    it('posts the locked axis name when one axis already exists', async () => {
      const existingVariants = [createMockVariant({ Kleur: 'Rood' })];
      openModal({ ...defaultProps, existingVariants });

      const valuesInput = screen.getByPlaceholderText("Eén waarde per regel of gescheiden door komma's");
      fireEvent.change(valuesInput, { target: { value: 'Blauw\nGroen' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Aanmaken'));
      });

      await waitFor(() => {
        expect(mockBulkCreateVariants).toHaveBeenCalledWith('prod_123', {
          axis_name: 'Kleur',
          values: ['Blauw', 'Groen'],
        });
      });
    });

    it('calls onSuccess after a successful submission', async () => {
      const onSuccess = jest.fn();
      openModal({ ...defaultProps, existingVariants: [], onSuccess });

      fireEvent.change(screen.getByPlaceholderText('Bijv. Maat, Kleur...'), {
        target: { value: 'Maat' },
      });
      fireEvent.change(screen.getByPlaceholderText("Eén waarde per regel of gescheiden door komma's"), {
        target: { value: 'S\nM' },
      });

      await act(async () => {
        fireEvent.click(screen.getByText('Aanmaken'));
      });

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
    });
  });

  describe('Live preview count (Requirement 3.7)', () => {
    it('shows the count of distinct values that would be created', () => {
      openModal({ ...defaultProps, existingVariants: [] });

      const valuesInput = screen.getByPlaceholderText("Eén waarde per regel of gescheiden door komma's");
      // 3 distinct values after normalization (S duplicated, blank ignored).
      fireEvent.change(valuesInput, { target: { value: 'S\nM\nS\n\nL' } });

      expect(
        screen.getByText('Er worden 3 varianten aangemaakt')
      ).toBeInTheDocument();
    });

    it('excludes values that already exist for the locked axis', () => {
      const existingVariants = [
        createMockVariant({ Maat: 'S' }),
        createMockVariant({ Maat: 'M' }),
      ];
      openModal({ ...defaultProps, existingVariants });

      const valuesInput = screen.getByPlaceholderText("Eén waarde per regel of gescheiden door komma's");
      // S and M already exist; only L and XL are new -> 2.
      fireEvent.change(valuesInput, { target: { value: 'S\nM\nL\nXL' } });

      expect(
        screen.getByText('Er worden 2 varianten aangemaakt')
      ).toBeInTheDocument();
    });
  });
});

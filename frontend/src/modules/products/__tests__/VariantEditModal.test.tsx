/**
 * VariantEditModal Unit Tests — Create Mode
 *
 * Tests:
 * - Zero-axes state renders free text inputs (Requirement 3.1)
 * - At-MAX_AXES state restricts axis to dropdown only (Requirement 4.2)
 * - 409 error displays toast message (Requirement 12.2)
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock toast
const mockToast = jest.fn();

// Mock Chakra UI
jest.mock('@chakra-ui/react', () => ({
  Modal: ({ children, isOpen }: any) => (isOpen ? <div data-testid="modal">{children}</div> : null),
  ModalOverlay: () => <div data-testid="modal-overlay" />,
  ModalContent: ({ children }: any) => <div data-testid="modal-content">{children}</div>,
  ModalHeader: ({ children }: any) => <h2 data-testid="modal-header">{children}</h2>,
  ModalBody: ({ children }: any) => <div data-testid="modal-body">{children}</div>,
  ModalFooter: ({ children }: any) => <div data-testid="modal-footer">{children}</div>,
  ModalCloseButton: () => <button aria-label="Close" />,
  Button: ({ children, onClick, isLoading, isDisabled, ...props }: any) => (
    <button onClick={onClick} disabled={isDisabled || isLoading} {...props}>
      {isLoading ? 'Loading...' : children}
    </button>
  ),
  FormControl: ({ children }: any) => <div>{children}</div>,
  FormLabel: ({ children }: any) => <label>{children}</label>,
  NumberInput: ({ children, value, onChange }: any) => <div>{children}</div>,
  NumberInputField: ({ placeholder, ...props }: any) => (
    <input type="number" placeholder={placeholder} {...props} />
  ),
  Switch: ({ isChecked, onChange, id }: any) => (
    <input type="checkbox" checked={isChecked} onChange={onChange} id={id} />
  ),
  HStack: ({ children }: any) => <div>{children}</div>,
  VStack: ({ children }: any) => <div>{children}</div>,
  Text: ({ children }: any) => <span>{children}</span>,
  Badge: ({ children }: any) => <span data-testid="badge">{children}</span>,
  Spinner: () => <span data-testid="spinner" />,
  Box: ({ children }: any) => <div>{children}</div>,
  Input: ({ value, onChange, placeholder, isDisabled, ...props }: any) => (
    <input
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      disabled={isDisabled}
      {...props}
    />
  ),
  Select: ({ children, value, onChange, placeholder, isDisabled, ...props }: any) => (
    <select value={value} onChange={onChange} disabled={isDisabled} {...props}>
      {placeholder && <option value="">{placeholder}</option>}
      {children}
    </select>
  ),
  useToast: () => mockToast,
}));

// Mock AddStockForm (used in edit mode, not relevant for create mode tests)
jest.mock('../../webshop-management/components/AddStockForm', () => ({
  AddStockForm: () => <div data-testid="add-stock-form" />,
}));

// Mock adminApi
const mockCreateVariant = jest.fn();
const mockUpdateVariant = jest.fn();
jest.mock('../../webshop-management/services/adminApi', () => ({
  createVariant: (...args: any[]) => mockCreateVariant(...args),
  updateVariant: (...args: any[]) => mockUpdateVariant(...args),
}));

import { VariantEditModal } from '../components/VariantEditModal';
import { AdminVariant } from '../../webshop-management/types/admin.types';

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
  isOpen: true,
  onClose: jest.fn(),
  productId: 'prod_123',
  variant: null as AdminVariant | null,
  existingVariants: [] as AdminVariant[],
  onSuccess: jest.fn(),
  parentPrice: 10,
};

describe('VariantEditModal — Create Mode', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Zero-axes state (Requirement 3.1)', () => {
    it('renders free text input for axis name when no variants exist', () => {
      render(<VariantEditModal {...defaultProps} existingVariants={[]} />);

      // In zero-axes mode, a free text input with placeholder for axis name should render
      const axisInput = screen.getByPlaceholderText('Bijv. Maat, Kleur...');
      expect(axisInput).toBeInTheDocument();
      expect(axisInput.tagName).toBe('INPUT');
    });

    it('renders free text input for value when no variants exist', () => {
      render(<VariantEditModal {...defaultProps} existingVariants={[]} />);

      const valueInput = screen.getByPlaceholderText('Bijv. S, Rood, 42...');
      expect(valueInput).toBeInTheDocument();
      expect(valueInput.tagName).toBe('INPUT');
    });

    it('does NOT render a dropdown/select for axis name in zero-axes state', () => {
      render(<VariantEditModal {...defaultProps} existingVariants={[]} />);

      // There should be no select element for the axis name (only free text input)
      const selects = screen.queryAllByRole('combobox');
      // Filter out any select that might be for other purposes
      const axisSelects = selects.filter(
        (s) => !s.querySelector('option[value=""]')?.textContent?.includes('Kies een as')
          || s.querySelectorAll('option').length <= 1
      );
      // Verify no select with axis options is present
      expect(screen.queryByText('Kies een as...')).not.toBeInTheDocument();
    });
  });

  describe('At-MAX_AXES state (Requirement 4.2)', () => {
    const variantsWithTwoAxes: AdminVariant[] = [
      createMockVariant({ Maat: 'S', Kleur: 'Rood' }),
      createMockVariant({ Maat: 'M', Kleur: 'Blauw' }),
    ];

    it('renders dropdown for axis name when MAX_AXES axes exist', () => {
      render(
        <VariantEditModal
          {...defaultProps}
          existingVariants={variantsWithTwoAxes}
        />
      );

      // At MAX_AXES, a dropdown with existing axes should render
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();

      // Should contain the existing axis names as options
      const options = select.querySelectorAll('option');
      const optionTexts = Array.from(options).map((o) => o.textContent);
      expect(optionTexts).toContain('Maat');
      expect(optionTexts).toContain('Kleur');
    });

    it('does NOT offer a "Nieuw..." free text option at MAX_AXES', () => {
      render(
        <VariantEditModal
          {...defaultProps}
          existingVariants={variantsWithTwoAxes}
        />
      );

      // "Nieuw..." option should NOT be present in the dropdown
      expect(screen.queryByText('Nieuw...')).not.toBeInTheDocument();
    });

    it('does NOT render a free text input for axis name at MAX_AXES', () => {
      render(
        <VariantEditModal
          {...defaultProps}
          existingVariants={variantsWithTwoAxes}
        />
      );

      // The free-text axis name input should not be present
      expect(screen.queryByPlaceholderText('Bijv. Maat, Kleur...')).not.toBeInTheDocument();
      expect(screen.queryByPlaceholderText('Nieuwe as-naam...')).not.toBeInTheDocument();
    });

    it('still renders free text input for value at MAX_AXES', () => {
      render(
        <VariantEditModal
          {...defaultProps}
          existingVariants={variantsWithTwoAxes}
        />
      );

      // Value input is always free text
      const valueInput = screen.getByPlaceholderText('Bijv. S, Rood, 42...');
      expect(valueInput).toBeInTheDocument();
    });
  });

  describe('409 error displays toast (Requirement 12.2)', () => {
    it('displays "Variant bestaat al" toast on 409 response', async () => {
      const error409 = {
        response: {
          status: 409,
          data: { message: 'Duplicate variant attributes' },
        },
      };
      mockCreateVariant.mockRejectedValueOnce(error409);

      render(<VariantEditModal {...defaultProps} existingVariants={[]} />);

      // Fill in axis name and value
      const axisInput = screen.getByPlaceholderText('Bijv. Maat, Kleur...');
      const valueInput = screen.getByPlaceholderText('Bijv. S, Rood, 42...');

      fireEvent.change(axisInput, { target: { value: 'Maat' } });
      fireEvent.change(valueInput, { target: { value: 'S' } });

      // Click submit button
      const submitButton = screen.getByText('Aanmaken');
      await act(async () => {
        fireEvent.click(submitButton);
      });

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Variant bestaat al',
            status: 'error',
          })
        );
      });
    });

    it('includes backend error message in toast description', async () => {
      const error409 = {
        response: {
          status: 409,
          data: { message: 'Variant met Maat=S bestaat al voor dit product' },
        },
      };
      mockCreateVariant.mockRejectedValueOnce(error409);

      render(<VariantEditModal {...defaultProps} existingVariants={[]} />);

      const axisInput = screen.getByPlaceholderText('Bijv. Maat, Kleur...');
      const valueInput = screen.getByPlaceholderText('Bijv. S, Rood, 42...');

      fireEvent.change(axisInput, { target: { value: 'Maat' } });
      fireEvent.change(valueInput, { target: { value: 'S' } });

      const submitButton = screen.getByText('Aanmaken');
      await act(async () => {
        fireEvent.click(submitButton);
      });

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Variant bestaat al',
            description: 'Variant met Maat=S bestaat al voor dit product',
            status: 'error',
          })
        );
      });
    });

    it('does not close the modal on 409 error', async () => {
      const onClose = jest.fn();
      const error409 = {
        response: {
          status: 409,
          data: { message: 'Duplicate' },
        },
      };
      mockCreateVariant.mockRejectedValueOnce(error409);

      render(
        <VariantEditModal
          {...defaultProps}
          onClose={onClose}
          existingVariants={[]}
        />
      );

      const axisInput = screen.getByPlaceholderText('Bijv. Maat, Kleur...');
      const valueInput = screen.getByPlaceholderText('Bijv. S, Rood, 42...');

      fireEvent.change(axisInput, { target: { value: 'Maat' } });
      fireEvent.change(valueInput, { target: { value: 'S' } });

      const submitButton = screen.getByText('Aanmaken');
      await act(async () => {
        fireEvent.click(submitButton);
      });

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalled();
      });

      // Modal should stay open — onClose should NOT have been called
      expect(onClose).not.toHaveBeenCalled();
    });
  });
});

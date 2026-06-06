/**
 * VariantSelector Component Tests
 *
 * Tests for axis rendering, selection interaction, variant resolution,
 * stock display, and out-of-stock state.
 * Validates: Requirements 15.1–15.8
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

// Mock Chakra UI components
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  VStack: ({ children, role, ...props }: any) => (
    <div role={role} {...props}>{children}</div>
  ),
  HStack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  FormControl: ({ children, isDisabled, ...props }: any) => (
    <fieldset disabled={isDisabled} {...props}>{children}</fieldset>
  ),
  FormLabel: ({ children, ...props }: any) => <label {...props}>{children}</label>,
  Select: ({ children, placeholder, value, onChange, 'aria-label': ariaLabel, ...props }: any) => (
    <select value={value} onChange={onChange} aria-label={ariaLabel} {...props}>
      {placeholder && <option value="">{placeholder}</option>}
      {children}
    </select>
  ),
  Text: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  Badge: ({ children, ...props }: any) => <span {...props}>{children}</span>,
}));

import VariantSelector, { resolveVariant, VariantSelectorProps } from '../components/VariantSelector';
import { VariantRecord, VariantSchema } from '../types/unifiedProduct.types';

// --- Test helpers ---

function createVariant(
  attributes: Record<string, string>,
  stock = 10,
  allowOversell = false
): VariantRecord {
  const attrStr = Object.values(attributes).join('_');
  return {
    product_id: `var_${attrStr}`,
    parent_id: 'prod_test',
    tenant: 'h-dcn',
    name: `Test - ${attrStr}`,
    variant_attributes: attributes,
    price: 25.0,
    stock,
    sold_count: 0,
    allow_oversell: allowOversell,
    active: true,
  };
}

const renderComponent = (props: Partial<VariantSelectorProps> = {}) => {
  const defaultProps: VariantSelectorProps = {
    variantSchema: { Maat: ['S', 'M', 'L'] },
    variants: [
      createVariant({ Maat: 'S' }, 10),
      createVariant({ Maat: 'M' }, 5),
      createVariant({ Maat: 'L' }, 0),
    ],
    onVariantSelect: jest.fn(),
    ...props,
  };

  let result: ReturnType<typeof render>;
  act(() => {
    result = render(<VariantSelector {...defaultProps} />);
  });
  return { ...result!, props: defaultProps };
};

describe('VariantSelector', () => {
  describe('axis rendering', () => {
    it('renders a select for each axis in the variant schema', () => {
      renderComponent({
        variantSchema: { Maat: ['S', 'M', 'L'], Kleur: ['Rood', 'Blauw'] },
        variants: [],
      });

      expect(screen.getByLabelText('Selecteer Maat')).toBeInTheDocument();
      expect(screen.getByLabelText('Selecteer Kleur')).toBeInTheDocument();
    });

    it('renders axis name as label', () => {
      renderComponent({
        variantSchema: { Maat: ['S', 'M', 'L'] },
        variants: [],
      });

      expect(screen.getByText('Maat')).toBeInTheDocument();
    });

    it('renders option values for each axis', () => {
      renderComponent({
        variantSchema: { Maat: ['S', 'M', 'L'] },
        variants: [],
      });

      const select = screen.getByLabelText('Selecteer Maat');
      expect(select).toContainHTML('<option value="S">S</option>');
      expect(select).toContainHTML('<option value="M">M</option>');
      expect(select).toContainHTML('<option value="L">L</option>');
    });

    it('includes placeholder option', () => {
      renderComponent({
        variantSchema: { Maat: ['S', 'M'] },
        variants: [],
      });

      expect(screen.getByText('variant.select_placeholder')).toBeInTheDocument();
    });

    it('shows prompt to select all options when not all selected', () => {
      renderComponent({
        variantSchema: { Maat: ['S', 'M'], Kleur: ['Rood'] },
        variants: [],
      });

      expect(
        screen.getByText('variant.select_all_prompt')
      ).toBeInTheDocument();
    });
  });

  describe('selection interaction', () => {
    it('calls onVariantSelect with null initially (no selection)', () => {
      const onVariantSelect = jest.fn();
      renderComponent({ onVariantSelect });

      expect(onVariantSelect).toHaveBeenCalledWith(null);
    });

    it('calls onVariantSelect with null when only some axes are selected', () => {
      const onVariantSelect = jest.fn();
      renderComponent({
        variantSchema: { Maat: ['S', 'M'], Kleur: ['Rood', 'Blauw'] },
        variants: [createVariant({ Maat: 'S', Kleur: 'Rood' })],
        onVariantSelect,
      });

      act(() => {
        fireEvent.change(screen.getByLabelText('Selecteer Maat'), {
          target: { value: 'S' },
        });
      });

      // Should still be null since Kleur isn't selected
      expect(onVariantSelect).toHaveBeenLastCalledWith(null);
    });

    it('resolves variant when all axes are selected', () => {
      const variant = createVariant({ Maat: 'S' }, 10);
      const onVariantSelect = jest.fn();
      renderComponent({
        variantSchema: { Maat: ['S', 'M'] },
        variants: [variant, createVariant({ Maat: 'M' }, 5)],
        onVariantSelect,
      });

      act(() => {
        fireEvent.change(screen.getByLabelText('Selecteer Maat'), {
          target: { value: 'S' },
        });
      });

      expect(onVariantSelect).toHaveBeenLastCalledWith(variant);
    });

    it('re-resolves on axis change', () => {
      const variantS = createVariant({ Maat: 'S' }, 10);
      const variantM = createVariant({ Maat: 'M' }, 5);
      const onVariantSelect = jest.fn();
      renderComponent({
        variantSchema: { Maat: ['S', 'M'] },
        variants: [variantS, variantM],
        onVariantSelect,
      });

      act(() => {
        fireEvent.change(screen.getByLabelText('Selecteer Maat'), {
          target: { value: 'S' },
        });
      });
      expect(onVariantSelect).toHaveBeenLastCalledWith(variantS);

      act(() => {
        fireEvent.change(screen.getByLabelText('Selecteer Maat'), {
          target: { value: 'M' },
        });
      });
      expect(onVariantSelect).toHaveBeenLastCalledWith(variantM);
    });
  });

  describe('variant resolution', () => {
    it('resolves variant matching all axis selections', () => {
      const variant = createVariant({ Maat: 'M', Kleur: 'Blauw' }, 7);
      const onVariantSelect = jest.fn();
      renderComponent({
        variantSchema: { Maat: ['S', 'M'], Kleur: ['Rood', 'Blauw'] },
        variants: [
          createVariant({ Maat: 'S', Kleur: 'Rood' }),
          createVariant({ Maat: 'S', Kleur: 'Blauw' }),
          createVariant({ Maat: 'M', Kleur: 'Rood' }),
          variant,
        ],
        onVariantSelect,
      });

      act(() => {
        fireEvent.change(screen.getByLabelText('Selecteer Maat'), {
          target: { value: 'M' },
        });
        fireEvent.change(screen.getByLabelText('Selecteer Kleur'), {
          target: { value: 'Blauw' },
        });
      });

      expect(onVariantSelect).toHaveBeenLastCalledWith(variant);
    });

    it('shows "Combinatie niet beschikbaar" when no variant matches', () => {
      const onVariantSelect = jest.fn();
      renderComponent({
        variantSchema: { Maat: ['S', 'M'], Kleur: ['Rood', 'Blauw'] },
        variants: [createVariant({ Maat: 'S', Kleur: 'Rood' })],
        onVariantSelect,
      });

      act(() => {
        fireEvent.change(screen.getByLabelText('Selecteer Maat'), {
          target: { value: 'M' },
        });
        fireEvent.change(screen.getByLabelText('Selecteer Kleur'), {
          target: { value: 'Blauw' },
        });
      });

      expect(screen.getByText('variant.combination_unavailable')).toBeInTheDocument();
      expect(onVariantSelect).toHaveBeenLastCalledWith(null);
    });
  });

  describe('stock display', () => {
    it('displays stock count when variant is resolved and in stock', () => {
      renderComponent({
        variantSchema: { Maat: ['S'] },
        variants: [createVariant({ Maat: 'S' }, 10)],
      });

      act(() => {
        fireEvent.change(screen.getByLabelText('Selecteer Maat'), {
          target: { value: 'S' },
        });
      });

      expect(screen.getByText('variant.in_stock')).toBeInTheDocument();
    });
  });

  describe('out-of-stock state', () => {
    it('shows "Niet op voorraad" when stock is 0 and allow_oversell is false', () => {
      renderComponent({
        variantSchema: { Maat: ['L'] },
        variants: [createVariant({ Maat: 'L' }, 0, false)],
      });

      act(() => {
        fireEvent.change(screen.getByLabelText('Selecteer Maat'), {
          target: { value: 'L' },
        });
      });

      expect(screen.getByText('variant.out_of_stock')).toBeInTheDocument();
    });

    it('shows stock count (0) when allow_oversell is true', () => {
      renderComponent({
        variantSchema: { Maat: ['L'] },
        variants: [createVariant({ Maat: 'L' }, 0, true)],
      });

      act(() => {
        fireEvent.change(screen.getByLabelText('Selecteer Maat'), {
          target: { value: 'L' },
        });
      });

      // When allow_oversell is true, stock=0 should NOT show out of stock
      expect(screen.queryByText('variant.out_of_stock')).not.toBeInTheDocument();
      expect(screen.getByText('variant.in_stock')).toBeInTheDocument();
    });
  });

  describe('resolveVariant utility function', () => {
    const schema: VariantSchema = { Maat: ['S', 'M'], Kleur: ['Rood', 'Blauw'] };
    const variants = [
      createVariant({ Maat: 'S', Kleur: 'Rood' }),
      createVariant({ Maat: 'S', Kleur: 'Blauw' }),
      createVariant({ Maat: 'M', Kleur: 'Rood' }),
      createVariant({ Maat: 'M', Kleur: 'Blauw' }),
    ];

    it('returns matching variant when all axes selected', () => {
      const result = resolveVariant({ Maat: 'S', Kleur: 'Rood' }, variants, schema);
      expect(result).toBe(variants[0]);
    });

    it('returns null when not all axes have selections', () => {
      const result = resolveVariant({ Maat: 'S' }, variants, schema);
      expect(result).toBeNull();
    });

    it('returns null when selections are empty strings', () => {
      const result = resolveVariant({ Maat: '', Kleur: '' }, variants, schema);
      expect(result).toBeNull();
    });

    it('returns null when no variant matches the selections', () => {
      const result = resolveVariant({ Maat: 'XL', Kleur: 'Rood' }, variants, schema);
      expect(result).toBeNull();
    });
  });

  describe('disabled state', () => {
    it('disables selects when isDisabled is true', () => {
      renderComponent({
        variantSchema: { Maat: ['S', 'M'] },
        variants: [],
        isDisabled: true,
      });

      const fieldset = screen.getByLabelText('Selecteer Maat').closest('fieldset');
      expect(fieldset).toBeDisabled();
    });
  });
});

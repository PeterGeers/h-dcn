/**
 * VariantSelector Component Tests
 *
 * Tests for axis rendering, selection interaction, variant resolution,
 * stock display, and out-of-stock state.
 * Validates: Requirements 5.1, 5.2, 5.3
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

import VariantSelector, { resolveVariant, VariantSelectorProps } from '../../../components/VariantSelector';
import { VariantRecord, VariantSchema } from '../types/unifiedProduct.types';

// --- Test helpers ---

function createVariant(
  attributes: Record<string, string>,
  stock = 10,
  allowOversell = false,
  active = true
): VariantRecord {
  const attrStr = Object.values(attributes).join('_');
  return {
    product_id: `var_${attrStr}`,
    parent_id: 'prod_test',
    name: `Test - ${attrStr}`,
    variant_attributes: attributes,
    price: 25.0,
    stock,
    sold_count: 0,
    allow_oversell: allowOversell,
    active,
  };
}

const renderComponent = (props: Partial<VariantSelectorProps> = {}) => {
  const defaultProps: VariantSelectorProps = {
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
    it('renders a select for each axis derived from variant records', () => {
      renderComponent({
        variants: [
          createVariant({ Maat: 'S', Kleur: 'Rood' }),
          createVariant({ Maat: 'M', Kleur: 'Blauw' }),
        ],
      });

      expect(screen.getByLabelText('Selecteer Maat')).toBeInTheDocument();
      expect(screen.getByLabelText('Selecteer Kleur')).toBeInTheDocument();
    });

    it('renders axis name as label', () => {
      renderComponent({
        variants: [createVariant({ Maat: 'S' })],
      });

      expect(screen.getByText('Maat')).toBeInTheDocument();
    });

    it('renders option values for each axis', () => {
      renderComponent({
        variants: [
          createVariant({ Maat: 'S' }),
          createVariant({ Maat: 'M' }),
          createVariant({ Maat: 'L' }),
        ],
      });

      const select = screen.getByLabelText('Selecteer Maat');
      expect(select).toContainHTML('<option value="S">S</option>');
      expect(select).toContainHTML('<option value="M">M</option>');
      expect(select).toContainHTML('<option value="L">L</option>');
    });

    it('includes placeholder option', () => {
      renderComponent({
        variants: [createVariant({ Maat: 'S' }), createVariant({ Maat: 'M' })],
      });

      expect(screen.getByText('variant.select_placeholder')).toBeInTheDocument();
    });

    it('shows prompt to select all options when not all selected', () => {
      renderComponent({
        variants: [
          createVariant({ Maat: 'S', Kleur: 'Rood' }),
          createVariant({ Maat: 'M', Kleur: 'Blauw' }),
        ],
      });

      expect(
        screen.getByText('variant.select_all_prompt')
      ).toBeInTheDocument();
    });

    it('excludes inactive variants from axis display', () => {
      renderComponent({
        variants: [
          createVariant({ Maat: 'S' }, 10, false, true),
          createVariant({ Maat: 'M' }, 10, false, true),
          createVariant({ Maat: 'XL' }, 10, false, false), // inactive — should not appear
          createVariant({ Maat: 'XXL' }, 5, false, false), // inactive — should not appear
        ],
      });

      const select = screen.getByLabelText('Selecteer Maat');
      expect(select).toContainHTML('<option value="S">S</option>');
      expect(select).toContainHTML('<option value="M">M</option>');
      expect(select).not.toContainHTML('<option value="XL">XL</option>');
      expect(select).not.toContainHTML('<option value="XXL">XXL</option>');
    });

    it('correctly aggregates axis values from multiple active records without duplicates', () => {
      // Two variants share Maat: 'S' but have different Kleur values
      // Axis "Maat" should show S, M (deduplicated), Kleur should show Rood, Blauw, Groen
      renderComponent({
        variants: [
          createVariant({ Maat: 'S', Kleur: 'Rood' }, 10, false, true),
          createVariant({ Maat: 'S', Kleur: 'Blauw' }, 5, false, true),
          createVariant({ Maat: 'M', Kleur: 'Rood' }, 8, false, true),
          createVariant({ Maat: 'M', Kleur: 'Groen' }, 3, false, true),
        ],
      });

      const maatSelect = screen.getByLabelText('Selecteer Maat');
      const kleurSelect = screen.getByLabelText('Selecteer Kleur');

      // Maat should have exactly S and M (no duplicates despite 2 variants with S and 2 with M)
      expect(maatSelect).toContainHTML('<option value="S">S</option>');
      expect(maatSelect).toContainHTML('<option value="M">M</option>');
      const maatOptions = maatSelect.querySelectorAll('option[value="S"]');
      expect(maatOptions).toHaveLength(1); // No duplicate S

      // Kleur should aggregate Rood, Blauw, Groen from all active variants
      expect(kleurSelect).toContainHTML('<option value="Rood">Rood</option>');
      expect(kleurSelect).toContainHTML('<option value="Blauw">Blauw</option>');
      expect(kleurSelect).toContainHTML('<option value="Groen">Groen</option>');
      const roodOptions = kleurSelect.querySelectorAll('option[value="Rood"]');
      expect(roodOptions).toHaveLength(1); // No duplicate Rood
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
        variants: [
          createVariant({ Maat: 'S', Kleur: 'Rood' }),
          createVariant({ Maat: 'M', Kleur: 'Blauw' }),
        ],
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
        variants: [
          createVariant({ Maat: 'S', Kleur: 'Rood' }),
          createVariant({ Maat: 'M', Kleur: 'Blauw' }),
        ],
        onVariantSelect,
      });

      act(() => {
        fireEvent.change(screen.getByLabelText('Selecteer Maat'), {
          target: { value: 'M' },
        });
        fireEvent.change(screen.getByLabelText('Selecteer Kleur'), {
          target: { value: 'Rood' },
        });
      });

      expect(screen.getByText('variant.combination_unavailable')).toBeInTheDocument();
      expect(onVariantSelect).toHaveBeenLastCalledWith(null);
    });
  });

  describe('stock display', () => {
    it('displays stock count when variant is resolved and in stock', () => {
      renderComponent({
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
        variants: [createVariant({ Maat: 'S' }), createVariant({ Maat: 'M' })],
        isDisabled: true,
      });

      const fieldset = screen.getByLabelText('Selecteer Maat').closest('fieldset');
      expect(fieldset).toBeDisabled();
    });
  });
});

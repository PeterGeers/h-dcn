import { determineFormMode, validateAxisInput, FormMode } from '../variantFormHelpers';
import { AdminVariant } from '../../../webshop-management/types/admin.types';

/**
 * Unit tests for variantFormHelpers: determineFormMode and validateAxisInput.
 */

// Helper to create a minimal AdminVariant with given variant_attributes
function makeVariant(attributes: Record<string, string>): AdminVariant {
  return {
    product_id: 'var_test',
    parent_id: 'parent_test',
    variant_attributes: attributes,
    stock: 0,
    sold_count: 0,
    allow_oversell: false,
    active: true,
  };
}

describe('determineFormMode', () => {
  it('returns "zero-axes" when no variants exist', () => {
    expect(determineFormMode([])).toBe('zero-axes');
  });

  it('returns "zero-axes" when variants have empty variant_attributes', () => {
    const variants = [makeVariant({})];
    expect(determineFormMode(variants)).toBe('zero-axes');
  });

  it('returns "under-max" when 1 distinct axis exists (MAX_AXES=2)', () => {
    const variants = [
      makeVariant({ Maat: 'S' }),
      makeVariant({ Maat: 'M' }),
    ];
    expect(determineFormMode(variants)).toBe('under-max');
  });

  it('returns "at-max" when MAX_AXES (2) distinct axes exist', () => {
    const variants = [
      makeVariant({ Maat: 'S', Kleur: 'Rood' }),
      makeVariant({ Maat: 'M', Kleur: 'Blauw' }),
    ];
    expect(determineFormMode(variants)).toBe('at-max');
  });

  it('returns "at-max" when more than MAX_AXES axes exist', () => {
    // Edge case: somehow 3 axes exist (shouldn't happen but function handles it)
    const variants = [
      makeVariant({ Maat: 'S', Kleur: 'Rood', Stof: 'Katoen' }),
    ];
    expect(determineFormMode(variants)).toBe('at-max');
  });

  it('counts distinct axes across multiple variants', () => {
    // One variant has Maat, another has Kleur — combined is 2 axes = at-max
    const variants = [
      makeVariant({ Maat: 'S' }),
      makeVariant({ Kleur: 'Rood' }),
    ];
    expect(determineFormMode(variants)).toBe('at-max');
  });
});

describe('validateAxisInput', () => {
  it('returns true for non-empty axis name and value', () => {
    expect(validateAxisInput('Maat', 'S')).toBe(true);
  });

  it('returns false for empty axis name', () => {
    expect(validateAxisInput('', 'S')).toBe(false);
  });

  it('returns false for empty value', () => {
    expect(validateAxisInput('Maat', '')).toBe(false);
  });

  it('returns false for whitespace-only axis name', () => {
    expect(validateAxisInput('   ', 'S')).toBe(false);
  });

  it('returns false for whitespace-only value', () => {
    expect(validateAxisInput('Maat', '   ')).toBe(false);
  });

  it('returns false when both are empty', () => {
    expect(validateAxisInput('', '')).toBe(false);
  });

  it('returns true for strings with surrounding whitespace but non-empty content', () => {
    expect(validateAxisInput('  Maat  ', '  S  ')).toBe(true);
  });
});

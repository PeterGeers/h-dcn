import { sortSizeValues, sortVariants, SIZE_ORDER } from '../utils/sizeSorter';
import { AdminVariant } from '../types/admin.types';

describe('sortSizeValues', () => {
  it('sorts recognized clothing sizes in standard order', () => {
    const input = ['XL', 'S', 'XXL', 'M', 'XS', 'L'];
    expect(sortSizeValues(input)).toEqual(['XS', 'S', 'M', 'L', 'XL', 'XXL']);
  });

  it('handles case-insensitive matching', () => {
    const input = ['xl', 'S', 'xxl', 'm', 'Xs', 'L'];
    expect(sortSizeValues(input)).toEqual(['Xs', 'S', 'm', 'L', 'xl', 'xxl']);
  });

  it('places recognized sizes before unrecognized non-numeric values', () => {
    const input = ['Custom', 'M', 'Special', 'L', 'S'];
    expect(sortSizeValues(input)).toEqual(['S', 'M', 'L', 'Custom', 'Special']);
  });

  it('sorts unrecognized non-numeric values alphabetically (case-insensitive)', () => {
    const input = ['Zebra', 'apple', 'Banana'];
    expect(sortSizeValues(input)).toEqual(['apple', 'Banana', 'Zebra']);
  });

  it('sorts numeric values in ascending numeric order (not lexicographic)', () => {
    const input = ['42', '9', '100', '38', '10'];
    expect(sortSizeValues(input)).toEqual(['9', '10', '38', '42', '100']);
  });

  it('places numeric values after non-numeric values', () => {
    const input = ['42', 'M', 'Custom', '38', 'L'];
    expect(sortSizeValues(input)).toEqual(['M', 'L', 'Custom', '38', '42']);
  });

  it('handles a mixed list with all three categories', () => {
    const input = ['42', 'XL', 'Custom', '38', 'S', 'Alpha', 'XXS', '9'];
    expect(sortSizeValues(input)).toEqual([
      'XXS', 'S', 'XL', 'Alpha', 'Custom', '9', '38', '42',
    ]);
  });

  it('returns an empty array for empty input', () => {
    expect(sortSizeValues([])).toEqual([]);
  });

  it('handles all extended sizes (3XL, 4XL, 5XL)', () => {
    const input = ['5XL', '3XL', '4XL', 'XXL'];
    expect(sortSizeValues(input)).toEqual(['XXL', '3XL', '4XL', '5XL']);
  });

  it('does not mutate the input array', () => {
    const input = ['L', 'S', 'M'];
    const original = [...input];
    sortSizeValues(input);
    expect(input).toEqual(original);
  });
});

describe('sortVariants', () => {
  const makeVariant = (attrs: Record<string, string>): AdminVariant => ({
    product_id: `var_${Object.values(attrs).join('_')}`,
    parent_id: 'parent_1',
    variant_attributes: attrs,
    stock: 10,
    sold_count: 0,
    allow_oversell: false,
    active: true,
  });

  it('sorts variants by first axis using size sorter logic', () => {
    const variants = [
      makeVariant({ Maat: 'XL' }),
      makeVariant({ Maat: 'S' }),
      makeVariant({ Maat: 'L' }),
      makeVariant({ Maat: 'M' }),
    ];

    const sorted = sortVariants(variants);
    expect(sorted.map((v) => v.variant_attributes.Maat)).toEqual([
      'S', 'M', 'L', 'XL',
    ]);
  });

  it('sorts subsequent axes alphabetically', () => {
    const variants = [
      makeVariant({ Maat: 'M', Kleur: 'Rood' }),
      makeVariant({ Maat: 'M', Kleur: 'Blauw' }),
      makeVariant({ Maat: 'M', Kleur: 'Groen' }),
    ];

    const sorted = sortVariants(variants);
    expect(sorted.map((v) => v.variant_attributes.Kleur)).toEqual([
      'Blauw', 'Groen', 'Rood',
    ]);
  });

  it('sorts by first axis then by second axis', () => {
    const variants = [
      makeVariant({ Maat: 'L', Kleur: 'Rood' }),
      makeVariant({ Maat: 'S', Kleur: 'Blauw' }),
      makeVariant({ Maat: 'S', Kleur: 'Rood' }),
      makeVariant({ Maat: 'L', Kleur: 'Blauw' }),
    ];

    const sorted = sortVariants(variants);
    expect(sorted.map((v) => `${v.variant_attributes.Maat}-${v.variant_attributes.Kleur}`)).toEqual([
      'S-Blauw', 'S-Rood', 'L-Blauw', 'L-Rood',
    ]);
  });

  it('handles numeric sizes in first axis', () => {
    const variants = [
      makeVariant({ Maat: '42' }),
      makeVariant({ Maat: '38' }),
      makeVariant({ Maat: '40' }),
    ];

    const sorted = sortVariants(variants);
    expect(sorted.map((v) => v.variant_attributes.Maat)).toEqual([
      '38', '40', '42',
    ]);
  });

  it('returns a copy when no variants have attributes', () => {
    const variants = [makeVariant({})];
    const sorted = sortVariants(variants);
    expect(sorted).toEqual(variants);
    expect(sorted).not.toBe(variants);
  });

  it('does not mutate the input array', () => {
    const variants = [makeVariant({ Maat: 'L' }), makeVariant({ Maat: 'S' })];
    const original = [...variants];
    sortVariants(variants);
    expect(variants).toEqual(original);
  });
});

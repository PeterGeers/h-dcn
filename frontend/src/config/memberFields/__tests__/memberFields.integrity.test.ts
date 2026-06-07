/**
 * Property-Based Test: Frontend split preserves field registry
 *
 * Verifies the reassembled MEMBER_FIELDS contains identical keys and values
 * as the original monolithic file after splitting into group-specific partials.
 *
 * Testing framework: Jest + fast-check
 * **Validates: Requirements 1.2**
 */

import * as fc from 'fast-check';
import { MEMBER_FIELDS } from '../index';
import {
  personalFields,
  addressFields,
  membershipFields,
  motorFields,
  financialFields,
  administrativeFields,
} from '../fields';
import type { FieldDefinition, FieldGroup } from '../types';

// ============================================================================
// Constants
// ============================================================================

const REQUIRED_PROPERTIES: (keyof FieldDefinition)[] = [
  'key',
  'label',
  'dataType',
  'inputType',
  'group',
  'order',
];

const EXPECTED_COUNTS: Record<FieldGroup, number> = {
  personal: 12,
  address: 4,
  membership: 10,
  motor: 4,
  financial: 2,
  administrative: 5,
};

const TOTAL_FIELD_COUNT = Object.values(EXPECTED_COUNTS).reduce((a, b) => a + b, 0); // 37

const GROUP_TO_PARTIAL: Record<FieldGroup, Record<string, FieldDefinition>> = {
  personal: personalFields,
  address: addressFields,
  membership: membershipFields,
  motor: motorFields,
  financial: financialFields,
  administrative: administrativeFields,
};

// ============================================================================
// Property 2: Frontend split preserves field registry
// **Validates: Requirements 1.2**
// ============================================================================

describe('Property 2: Frontend split preserves field registry', () => {
  const allFieldKeys = Object.keys(MEMBER_FIELDS);
  const fieldKeyArbitrary = fc.constantFrom(...allFieldKeys);

  it('MEMBER_FIELDS contains the expected total number of fields (37)', () => {
    expect(Object.keys(MEMBER_FIELDS)).toHaveLength(TOTAL_FIELD_COUNT);
  });

  it('each field group has the expected number of fields', () => {
    const groups: FieldGroup[] = ['personal', 'address', 'membership', 'motor', 'financial', 'administrative'];

    for (const group of groups) {
      const fieldsInGroup = Object.values(MEMBER_FIELDS).filter(f => f.group === group);
      expect(fieldsInGroup).toHaveLength(EXPECTED_COUNTS[group]);
    }
  });

  it('every field has all required properties (key, label, dataType, inputType, group, order)', () => {
    fc.assert(
      fc.property(fieldKeyArbitrary, (key) => {
        const field = MEMBER_FIELDS[key];
        return REQUIRED_PROPERTIES.every(
          (prop) => field[prop] !== undefined && field[prop] !== null
        );
      }),
      { numRuns: 200 }
    );
  });

  it('every field has a non-empty key property (data key is defined)', () => {
    fc.assert(
      fc.property(fieldKeyArbitrary, (key) => {
        const field = MEMBER_FIELDS[key];
        return typeof field.key === 'string' && field.key.length > 0;
      }),
      { numRuns: 200 }
    );
  });

  it('every field group value matches the partial file it was extracted from', () => {
    fc.assert(
      fc.property(fieldKeyArbitrary, (key) => {
        const field = MEMBER_FIELDS[key];
        const expectedPartial = GROUP_TO_PARTIAL[field.group];
        return key in expectedPartial;
      }),
      { numRuns: 200 }
    );
  });

  it('no field keys are duplicated across partials', () => {
    const allPartialKeys = [
      ...Object.keys(personalFields),
      ...Object.keys(addressFields),
      ...Object.keys(membershipFields),
      ...Object.keys(motorFields),
      ...Object.keys(financialFields),
      ...Object.keys(administrativeFields),
    ];
    const uniqueKeys = new Set(allPartialKeys);
    expect(allPartialKeys).toHaveLength(uniqueKeys.size);
  });

  it('reassembled MEMBER_FIELDS contains all keys from every partial', () => {
    const partials = [
      personalFields,
      addressFields,
      membershipFields,
      motorFields,
      financialFields,
      administrativeFields,
    ];

    for (const partial of partials) {
      for (const key of Object.keys(partial)) {
        expect(MEMBER_FIELDS).toHaveProperty(key);
      }
    }
  });

  it('field definitions in MEMBER_FIELDS are identical to those in their source partial', () => {
    fc.assert(
      fc.property(fieldKeyArbitrary, (key) => {
        const field = MEMBER_FIELDS[key];
        const sourcePartial = GROUP_TO_PARTIAL[field.group];
        const sourceField = sourcePartial[key];
        // Deep equality check
        return JSON.stringify(field) === JSON.stringify(sourceField);
      }),
      { numRuns: 200 }
    );
  });

  it('group property is always a valid FieldGroup value', () => {
    const validGroups: FieldGroup[] = ['personal', 'address', 'membership', 'motor', 'financial', 'administrative'];

    fc.assert(
      fc.property(fieldKeyArbitrary, (key) => {
        return validGroups.includes(MEMBER_FIELDS[key].group);
      }),
      { numRuns: 200 }
    );
  });
});

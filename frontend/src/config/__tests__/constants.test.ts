import { MAX_AXES } from '../constants';

/**
 * Unit test for application-wide constants.
 *
 * Asserts the single-axis product decision: a product supports exactly one
 * variant axis at a time, so MAX_AXES must equal 1.
 *
 * **Validates: Requirements 1.1**
 */
describe('MAX_AXES', () => {
  it('equals 1 (single-axis product decision)', () => {
    expect(MAX_AXES).toBe(1);
  });
});

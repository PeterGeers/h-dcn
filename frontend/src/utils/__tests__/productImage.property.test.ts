import * as fc from 'fast-check';
import {
  getPrimaryImageUrl,
  normalizeProductImages,
  ProductImageFields,
} from '../productImage';

// Feature: webshop-table-improvements
// Property tests for the shared product image helper (utils/productImage.ts).
// Uses fast-check with a minimum of 100 iterations per property.

const NUM_RUNS = 100;

const FULL_BUCKET_HOST = 'https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com';
const INCOMPLETE_BUCKET_PREFIX = 'https://my-hdcn-bucke';

/**
 * Generator for arbitrary "image-ish" entries: real strings (possibly empty),
 * plus non-string junk that the helper must defend against.
 */
const imageEntryArb: fc.Arbitrary<unknown> = fc.oneof(
  fc.string(),
  fc.constant(''),
  fc.constant(null),
  fc.constant(undefined),
  fc.integer(),
  fc.boolean(),
  fc.object(),
  fc.array(fc.string()),
);

/**
 * Generator for an arbitrary product image-fields shape. Independently chooses
 * whether to supply `images` and/or legacy `image`, each as array / single
 * value / absent, so malformed and mixed inputs are well covered.
 */
const productArb: fc.Arbitrary<ProductImageFields> = fc.record(
  {
    images: fc.option(
      fc.oneof(fc.array(imageEntryArb), imageEntryArb),
      { nil: undefined },
    ),
    image: fc.option(
      fc.oneof(fc.array(imageEntryArb), imageEntryArb),
      { nil: undefined },
    ),
  },
  { requiredKeys: [] },
);

describe('productImage helper — property tests', () => {
  /**
   * Property 1: Helper returns null or a non-empty string.
   * getPrimaryImageUrl always returns either null or a non-empty string,
   * never an empty string and never throwing, for any input shape.
   *
   * **Validates: Requirements 5.1, 5.4, 4.5**
   */
  it('Property 1: getPrimaryImageUrl returns null or a non-empty string', () => {
    fc.assert(
      fc.property(productArb, (product) => {
        const result = getPrimaryImageUrl(product);
        if (result === null) {
          return true;
        }
        return typeof result === 'string' && result.length > 0;
      }),
      { numRuns: NUM_RUNS },
    );
  });

  /**
   * Property 2: No usable image yields null.
   * When the product has no usable image — i.e. normalizeProductImages
   * produces an empty list — getPrimaryImageUrl returns null. Conversely,
   * when there is at least one usable image, it returns that first image.
   *
   * **Validates: Requirements 4.5, 5.4**
   */
  it('Property 2: no usable image yields null', () => {
    fc.assert(
      fc.property(productArb, (product) => {
        const normalized = normalizeProductImages(product);
        const primary = getPrimaryImageUrl(product);
        if (normalized.length === 0) {
          return primary === null;
        }
        return primary === normalized[0];
      }),
      { numRuns: NUM_RUNS },
    );
  });

  /**
   * Property 2b: explicitly empty / unusable inputs produce null.
   * Covers absent, null, empty array, and non-string-only inputs.
   *
   * **Validates: Requirements 4.5, 5.4**
   */
  it('Property 2b: absent / empty / non-string-only inputs yield null', () => {
    const unusableArb: fc.Arbitrary<ProductImageFields> = fc.oneof(
      fc.constant<ProductImageFields>({}),
      fc.constant<ProductImageFields>({ images: [] }),
      fc.constant<ProductImageFields>({ images: null }),
      fc.constant<ProductImageFields>({ image: undefined }),
      fc.constant<ProductImageFields>({ images: '' }),
      // array made only of non-usable entries
      fc
        .array(
          fc.oneof(
            fc.constant(''),
            fc.constant(null),
            fc.constant(undefined),
            fc.integer(),
            fc.boolean(),
          ),
        )
        .map((arr) => ({ images: arr } as ProductImageFields)),
    );

    fc.assert(
      fc.property(unusableArb, (product) => getPrimaryImageUrl(product) === null),
      { numRuns: NUM_RUNS },
    );
  });

  /**
   * Property 3: Bucket URL correction.
   * The incomplete `https://my-hdcn-bucke` prefix is corrected to the full
   * host, while already-correct URLs are left untouched. Built as a
   * suffix appended to each prefix so both inputs describe the same image.
   *
   * **Validates: Requirements 5.3**
   */
  it('Property 3: incomplete bucket prefix is corrected, correct URLs untouched', () => {
    // suffix must not itself start the full-host continuation that would make
    // the incomplete-prefixed string accidentally already-correct.
    const suffixArb = fc
      .string()
      .filter((s) => !s.startsWith('t.s3.eu-west-1.amazonaws.com'));

    fc.assert(
      fc.property(suffixArb, (suffix) => {
        const incomplete = INCOMPLETE_BUCKET_PREFIX + suffix;
        const correct = FULL_BUCKET_HOST + suffix;

        // Already-correct URL is returned unchanged.
        const correctOut = normalizeProductImages({ images: [correct] });
        if (correctOut.length !== 1 || correctOut[0] !== correct) {
          return false;
        }

        // Incomplete URL is rewritten to the corrected form.
        const fixedOut = normalizeProductImages({ images: [incomplete] });
        if (fixedOut.length !== 1 || fixedOut[0] !== correct) {
          return false;
        }

        // The corrected output is fully qualified with the complete host.
        return fixedOut[0].startsWith(FULL_BUCKET_HOST);
      }),
      { numRuns: NUM_RUNS },
    );
  });

  /**
   * Property 3b: unrelated URLs are passed through unchanged.
   *
   * **Validates: Requirements 5.3**
   */
  it('Property 3b: unrelated non-empty strings pass through unchanged', () => {
    const otherUrlArb = fc
      .string({ minLength: 1 })
      .filter(
        (s) =>
          !s.startsWith(INCOMPLETE_BUCKET_PREFIX) && !s.startsWith(FULL_BUCKET_HOST),
      );

    fc.assert(
      fc.property(otherUrlArb, (url) => {
        const out = normalizeProductImages({ images: [url] });
        return out.length === 1 && out[0] === url;
      }),
      { numRuns: NUM_RUNS },
    );
  });
});

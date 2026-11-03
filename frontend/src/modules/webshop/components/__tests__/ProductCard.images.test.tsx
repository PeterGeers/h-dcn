import {
  normalizeProductImages,
  ProductImageFields,
} from '../../../../utils/productImage';

// Feature: webshop-table-improvements — Task 2.2 "Test image-list parity".
//
// ProductCard.tsx used to normalize product images with an inline block
// (~lines 138–168 before the refactor). That logic was extracted verbatim into
// `utils/productImage.ts` (`normalizeProductImages`) and ProductCard now calls
// the helper. These tests pin down that the helper produces the SAME image list
// the original inline block produced, across the four input categories called
// out by the task: array input, legacy string input, bucket-prefix fix, and
// empty / malformed input.
//
// `originalInlineNormalize` below is a faithful copy of the pre-refactor inline
// logic. It is the oracle: every assertion compares the helper against it.

const FULL_BUCKET_HOST = 'https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com';
const INCOMPLETE_BUCKET_PREFIX = 'https://my-hdcn-bucke';

/**
 * Faithful reproduction of the image-normalization block that used to live
 * inline in ProductCard.tsx, before it was replaced by a call to
 * `normalizeProductImages`. Kept here solely as a parity oracle.
 */
function originalInlineNormalize(product: ProductImageFields): string[] {
  // Handle both 'image' and 'images' properties from the API.
  let images: string[] = [];
  const imageData = product.images || product.image;

  if (imageData) {
    if (Array.isArray(imageData)) {
      images = imageData as string[];
    } else if (typeof imageData === 'string') {
      images = [imageData];
    }
  }

  // Fix image URLs if they're incomplete, or use them as-is if complete.
  return images
    .map((img) => {
      if (typeof img === 'string') {
        if (img.startsWith(FULL_BUCKET_HOST)) {
          return img;
        }
        if (img.startsWith(INCOMPLETE_BUCKET_PREFIX)) {
          return img.replace(INCOMPLETE_BUCKET_PREFIX, FULL_BUCKET_HOST);
        }
      }
      return img;
    })
    .filter((img): img is string => Boolean(img) && typeof img === 'string');
}

/**
 * Assert the helper and the original inline logic agree for a given input, and
 * return the shared result so individual tests can also assert concrete values.
 */
function expectParity(product: ProductImageFields): string[] {
  const expected = originalInlineNormalize(product);
  const actual = normalizeProductImages(product);
  expect(actual).toEqual(expected);
  return actual;
}

describe('ProductCard image-list parity (normalizeProductImages vs original inline logic)', () => {
  describe('array input', () => {
    it('passes a multi-entry fully-qualified images array through in order', () => {
      const images = [
        `${FULL_BUCKET_HOST}/products/a.jpg`,
        `${FULL_BUCKET_HOST}/products/b.jpg`,
        'https://cdn.example.com/c.png',
      ];
      const result = expectParity({ images });
      expect(result).toEqual(images);
    });

    it('preserves order and does not deduplicate', () => {
      const images = [
        'https://cdn.example.com/x.png',
        'https://cdn.example.com/x.png',
        'https://cdn.example.com/y.png',
      ];
      const result = expectParity({ images });
      expect(result).toEqual(images);
    });

    it('prefers images over the legacy image field when both are present', () => {
      const result = expectParity({
        images: ['https://cdn.example.com/from-images.png'],
        image: 'https://cdn.example.com/from-image.png',
      });
      expect(result).toEqual(['https://cdn.example.com/from-images.png']);
    });

    it('reads the legacy image field when it is itself an array', () => {
      const image = [
        'https://cdn.example.com/legacy-1.png',
        'https://cdn.example.com/legacy-2.png',
      ];
      const result = expectParity({ image });
      expect(result).toEqual(image);
    });
  });

  describe('legacy string input', () => {
    it('wraps a single images string into a one-element list', () => {
      const result = expectParity({ images: 'https://cdn.example.com/single.png' });
      expect(result).toEqual(['https://cdn.example.com/single.png']);
    });

    it('wraps a single legacy image string into a one-element list', () => {
      const result = expectParity({ image: 'https://cdn.example.com/legacy.png' });
      expect(result).toEqual(['https://cdn.example.com/legacy.png']);
    });

    it('prefers a non-empty images string over the legacy image field', () => {
      const result = expectParity({
        images: 'https://cdn.example.com/primary.png',
        image: 'https://cdn.example.com/secondary.png',
      });
      expect(result).toEqual(['https://cdn.example.com/primary.png']);
    });
  });

  describe('bucket-prefix fix', () => {
    it('rewrites the incomplete bucket prefix to the full host', () => {
      const incomplete = `${INCOMPLETE_BUCKET_PREFIX}t/products/photo.jpg`;
      const result = expectParity({ images: [incomplete] });
      expect(result).toEqual([
        `${FULL_BUCKET_HOST}t/products/photo.jpg`,
      ]);
    });

    it('leaves an already-correct full-host URL untouched', () => {
      const correct = `${FULL_BUCKET_HOST}/products/photo.jpg`;
      const result = expectParity({ images: [correct] });
      expect(result).toEqual([correct]);
    });

    it('rewrites a legacy single-string incomplete URL', () => {
      const incomplete = `${INCOMPLETE_BUCKET_PREFIX}t/legacy.jpg`;
      const result = expectParity({ image: incomplete });
      expect(result).toEqual([`${FULL_BUCKET_HOST}t/legacy.jpg`]);
    });

    it('fixes a mix of incomplete, correct, and unrelated URLs in place', () => {
      const images = [
        `${INCOMPLETE_BUCKET_PREFIX}t/one.jpg`,
        `${FULL_BUCKET_HOST}/two.jpg`,
        'https://cdn.example.com/three.png',
      ];
      const result = expectParity({ images });
      expect(result).toEqual([
        `${FULL_BUCKET_HOST}t/one.jpg`,
        `${FULL_BUCKET_HOST}/two.jpg`,
        'https://cdn.example.com/three.png',
      ]);
    });
  });

  describe('empty / malformed input', () => {
    it('returns an empty list for an empty product object', () => {
      const result = expectParity({});
      expect(result).toEqual([]);
    });

    it('returns an empty list for an empty images array', () => {
      const result = expectParity({ images: [] });
      expect(result).toEqual([]);
    });

    it('returns an empty list when images is null', () => {
      const result = expectParity({ images: null });
      expect(result).toEqual([]);
    });

    it('returns an empty list when images is undefined and image is undefined', () => {
      const result = expectParity({ images: undefined, image: undefined });
      expect(result).toEqual([]);
    });

    it('returns an empty list for an empty string', () => {
      const result = expectParity({ images: '' });
      expect(result).toEqual([]);
    });

    it('drops non-string and empty-string entries from an array', () => {
      const result = expectParity({
        images: [
          '',
          null,
          undefined,
          42,
          true,
          { url: 'nope' },
          'https://cdn.example.com/keep.png',
        ] as unknown as string[],
      });
      expect(result).toEqual(['https://cdn.example.com/keep.png']);
    });

    it('returns an empty list when every entry is unusable', () => {
      const result = expectParity({
        images: ['', null, undefined, 0, false] as unknown as string[],
      });
      expect(result).toEqual([]);
    });

    it('ignores a non-string, non-array images value', () => {
      const result = expectParity({ images: 42 as unknown as string[] });
      expect(result).toEqual([]);
    });
  });
});

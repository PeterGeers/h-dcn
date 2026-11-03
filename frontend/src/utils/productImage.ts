/**
 * Shared product image normalization.
 *
 * Mirrors the image-normalization logic that used to live inline in
 * `frontend/src/modules/webshop/components/ProductCard.tsx`. Extracted into a
 * single, pure, property-testable helper so that the webshop table and the
 * product card stay consistent.
 *
 * Handles:
 * - the `images` array and the legacy `image` field (string or string[]);
 * - the bucket URL fix `https://my-hdcn-bucke` →
 *   `https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com` (already-correct URLs
 *   are left untouched);
 * - defensively dropping non-string and empty-string entries.
 *
 * These functions are pure and never throw on malformed input.
 */

const FULL_BUCKET_HOST = 'https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com';
const INCOMPLETE_BUCKET_PREFIX = 'https://my-hdcn-bucke';

/** Minimal shape the helper reads — accepts a product or just its image fields. */
export interface ProductImageFields {
  images?: unknown; // expected string[] but defensively typed
  image?: unknown; // legacy: string | string[]
}

/**
 * Normalize a product's image data to a list of usable, fully-qualified URLs.
 *
 * - Accepts `images` (array) or the legacy `image` (string | string[]).
 * - Flattens to a string list, dropping non-string / empty entries.
 * - Applies the bucket URL fix (see module docs).
 *
 * Pure and property-testable. Never throws on malformed input.
 */
export function normalizeProductImages(product: ProductImageFields): string[] {
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
 * Return the first usable, fully-qualified image URL for a product, or `null`
 * when none exists.
 */
export function getPrimaryImageUrl(product: ProductImageFields): string | null {
  return normalizeProductImages(product)[0] ?? null;
}

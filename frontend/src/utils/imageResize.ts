/**
 * Image Resize Utility
 *
 * Client-side image resizing using canvas. Resizes images before upload to:
 * - Stay within API Gateway's 6MB payload limit (~4.5MB after base64)
 * - Reduce S3 storage costs
 * - Improve page load performance
 *
 * Usage:
 *   const resized = await resizeImage(file, { maxWidth: 1200, maxHeight: 1200 });
 *   // resized is a new File object, ready for upload
 */

export interface ResizeOptions {
  /** Maximum width in pixels */
  maxWidth: number;
  /** Maximum height in pixels */
  maxHeight: number;
  /** JPEG/WebP quality 0-1 (default: 0.85) */
  quality?: number;
  /** Output format (default: 'jpeg'). Use 'png' for transparency. */
  format?: 'jpeg' | 'png' | 'webp';
}

/**
 * Resize an image file if it exceeds the specified dimensions.
 * If the image is already smaller than maxWidth/maxHeight, it is returned as-is
 * (no quality loss from re-encoding).
 *
 * @param file - The original File from an <input type="file">
 * @param options - Resize configuration (maxWidth, maxHeight, quality, format)
 * @returns A new File object (resized) or the original if no resize was needed
 */
export async function resizeImage(file: File, options: ResizeOptions): Promise<File> {
  const { maxWidth, maxHeight, quality = 0.85, format = 'jpeg' } = options;

  // Load image into an HTMLImageElement
  const img = await loadImage(file);

  // Check if resize is needed
  if (img.width <= maxWidth && img.height <= maxHeight) {
    // Image is already small enough — return original to avoid quality loss
    return file;
  }

  // Calculate new dimensions maintaining aspect ratio
  const { width, height } = calculateDimensions(img.width, img.height, maxWidth, maxHeight);

  // Draw resized image on canvas
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('Canvas context not available');
  }

  ctx.drawImage(img, 0, 0, width, height);

  // Convert canvas to blob
  const mimeType = `image/${format}`;
  const blob = await canvasToBlob(canvas, mimeType, quality);

  // Create a new File with the resized data
  const extension = format === 'jpeg' ? 'jpg' : format;
  const baseName = file.name.replace(/\.[^.]+$/, '');
  const newFileName = `${baseName}.${extension}`;

  return new File([blob], newFileName, { type: mimeType });
}

/**
 * Load a File into an HTMLImageElement.
 */
function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(img.src);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(img.src);
      reject(new Error('Failed to load image'));
    };
    img.src = URL.createObjectURL(file);
  });
}

/**
 * Calculate new dimensions maintaining aspect ratio.
 */
function calculateDimensions(
  originalWidth: number,
  originalHeight: number,
  maxWidth: number,
  maxHeight: number
): { width: number; height: number } {
  let width = originalWidth;
  let height = originalHeight;

  if (width > maxWidth) {
    height = Math.round(height * (maxWidth / width));
    width = maxWidth;
  }

  if (height > maxHeight) {
    width = Math.round(width * (maxHeight / height));
    height = maxHeight;
  }

  return { width, height };
}

/**
 * Convert a canvas to a Blob.
 */
function canvasToBlob(canvas: HTMLCanvasElement, mimeType: string, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error('Canvas toBlob failed'));
        }
      },
      mimeType,
      quality
    );
  });
}

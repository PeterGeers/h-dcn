/**
 * Event Poster Upload Service
 *
 * Uploads event poster files (PDF, PNG, JPG) to S3 via the s3_file_manager backend.
 * Reuses the same upload pattern as product images.
 *
 * Storage path: event-posters/{event_id}.{ext}
 * Max size: 10MB
 */

import { fetchAuthSession } from 'aws-amplify/auth';
import { resizeImage } from '../../../utils/imageResize';

const DEFAULT_DATA_BUCKET = process.env.REACT_APP_DATA_BUCKET || 'h-dcn-data-506221081911';
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'application/pdf'];

async function getSessionAuth(): Promise<{ authToken: string; groups: string[] }> {
  const session = await fetchAuthSession();
  const token = session.tokens?.accessToken?.toString();
  const groups = (session.tokens?.accessToken?.payload?.['cognito:groups'] as string[] | undefined) ?? [];
  return { authToken: token || '', groups };
}

export interface PosterUploadResult {
  url: string;
  key: string;
  size: number;
}

/**
 * Validate a file before upload.
 * Returns an error message or null if valid.
 */
export function validatePosterFile(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) {
    return 'Ongeldig bestandstype. Toegestaan: PDF, PNG, JPG.';
  }
  if (file.size > MAX_FILE_SIZE) {
    return `Bestand te groot (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum: 10MB.`;
  }
  return null;
}

/**
 * Upload an event poster file to S3.
 *
 * @param file - The file to upload (PDF, PNG, or JPG)
 * @param eventId - Optional event ID for naming. If not provided, uses timestamp.
 * @returns The public S3 URL of the uploaded file
 */
export async function uploadEventPoster(file: File, eventId?: string): Promise<PosterUploadResult> {
  // Validate
  const validationError = validatePosterFile(file);
  if (validationError) {
    throw new Error(validationError);
  }

  // Determine file key
  const fileExtension = file.name.split('.').pop()?.toLowerCase() || 'jpg';
  const fileName = eventId
    ? `event-posters/${eventId}.${fileExtension}`
    : `event-posters/${Date.now()}-${file.name.replace(/[^a-zA-Z0-9._-]/g, '_')}`;

  // Resize image files (not PDFs) to max 1920×1080
  let uploadFile = file;
  if (file.type.startsWith('image/')) {
    uploadFile = await resizeImage(file, { maxWidth: 1920, maxHeight: 1080, quality: 0.85 });
  }

  // Convert to base64
  const fileBuffer = await uploadFile.arrayBuffer();
  const uint8Array = new Uint8Array(fileBuffer);
  let binaryString = '';
  for (let i = 0; i < uint8Array.length; i++) {
    binaryString += String.fromCharCode(uint8Array[i]);
  }
  const base64String = btoa(binaryString);

  // Get auth
  const { authToken, groups } = await getSessionAuth();

  // Upload via s3_file_manager API
  const apiUrl = `${API_BASE_URL}/s3/files`;

  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Enhanced-Groups': JSON.stringify(groups),
  };
  if (authToken) {
    requestHeaders['Authorization'] = `Bearer ${authToken}`;
  }

  const requestBody = {
    bucketName: DEFAULT_DATA_BUCKET,
    fileKey: fileName,
    fileData: base64String,
    contentType: uploadFile.type,
    cacheControl: 'public, max-age=86400', // Cache for 1 day (posters may be updated)
  };

  const response = await fetch(apiUrl, {
    method: 'POST',
    headers: requestHeaders,
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Upload mislukt: ${response.status}`);
  }

  const result = await response.json();

  return {
    url: result.fileUrl,
    key: fileName,
    size: uint8Array.length,
  };
}

/**
 * Get the expected poster URL for an event (for display when already uploaded).
 */
export function getEventPosterUrl(eventId: string, extension: string = 'jpg'): string {
  const region = 'eu-west-1';
  return `https://${DEFAULT_DATA_BUCKET}.s3.${region}.amazonaws.com/event-posters/${eventId}.${extension}`;
}

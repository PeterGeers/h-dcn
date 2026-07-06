/**
 * Poster Analysis Service
 *
 * Uploads an event poster image to the analyze-poster endpoint.
 * The backend uses Gemini AI (vision/multimodal) to extract event metadata
 * (name, dates, location, info) from the poster image.
 *
 * No authentication required for this endpoint.
 */

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod';

export interface PosterAnalysisResult {
  name: string;
  start_date: string;
  end_date: string;
  location: string;
  info: string;
}

/**
 * Convert a File object to a base64-encoded string.
 */
async function fileToBase64(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const uint8Array = new Uint8Array(buffer);
  let binaryString = '';
  for (let i = 0; i < uint8Array.length; i++) {
    binaryString += String.fromCharCode(uint8Array[i]);
  }
  return btoa(binaryString);
}

/**
 * Analyze a poster image using the AI-powered endpoint.
 *
 * Sends the image as base64 to POST /analyze-poster.
 * Returns structured event metadata extracted from the poster.
 *
 * @param imageFile - The poster image file to analyze
 * @returns Extracted event metadata (name, dates, location, info)
 * @throws Error if analysis fails or the response is invalid
 */
export async function analyzePoster(imageFile: File): Promise<PosterAnalysisResult> {
  const base64Data = await fileToBase64(imageFile);
  const mimeType = imageFile.type || 'image/jpeg';

  const response = await fetch(`${API_BASE_URL}/analyze-poster`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      image_data: base64Data,
      mime_type: mimeType,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = errorData.message || errorData.error || `Analysis failed: ${response.status}`;
    throw new Error(message);
  }

  const result = await response.json();

  return {
    name: result.name || '',
    start_date: result.start_date || '',
    end_date: result.end_date || '',
    location: result.location || '',
    info: result.info || '',
  };
}

/**
 * PDF Download Service for Order Confirmations
 *
 * Handles downloading order confirmation PDFs from the backend API.
 * The backend returns base64-encoded PDF content via API Gateway.
 */

import { getAuthHeadersForGet } from '../../../utils/authHeaders';
import i18next from 'i18next';

export type PdfDownloadErrorCode = 'unauthorized' | 'forbidden' | 'not_found' | 'server_error' | 'timeout' | 'network_error';

export interface PdfDownloadResult {
  success: boolean;
  error?: {
    code: PdfDownloadErrorCode;
    message: string;
    statusCode?: number;
  };
}

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';
const PDF_TIMEOUT_MS = 30000;

/**
 * Download an order confirmation PDF.
 *
 * Sends an authenticated GET request to /orders/{orderId}/pdf,
 * converts the base64 response to a Blob, and triggers a browser download.
 */
export async function downloadOrderPdf(orderId: string): Promise<PdfDownloadResult> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), PDF_TIMEOUT_MS);

  try {
    const headers = await getAuthHeadersForGet();

    const response = await fetch(`${API_BASE_URL}/orders/${encodeURIComponent(orderId)}/pdf`, {
      method: 'GET',
      headers: {
        ...headers,
        'Accept': 'application/pdf',
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      return handleErrorResponse(response.status);
    }

    // API Gateway returns base64-encoded PDF content
    const contentType = response.headers.get('Content-Type');

    let pdfBlob: Blob;

    if (contentType && contentType.includes('application/pdf')) {
      // Direct binary response (when binary media types are configured)
      const arrayBuffer = await response.arrayBuffer();
      pdfBlob = new Blob([arrayBuffer], { type: 'application/pdf' });
    } else {
      // Base64-encoded response (API Gateway default for binary)
      const base64Data = await response.text();
      const binaryString = atob(base64Data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      pdfBlob = new Blob([bytes], { type: 'application/pdf' });
    }

    triggerDownload(pdfBlob, `orderbevestiging-${orderId}.pdf`);

    return { success: true };
  } catch (error: unknown) {
    clearTimeout(timeoutId);

    if (error instanceof Error && error.name === 'AbortError') {
      return {
        success: false,
        error: {
          code: 'timeout',
          message: i18next.t('errors.pdf_timeout', { ns: 'webshop', defaultValue: 'Het downloaden van de PDF duurde te lang. Probeer het opnieuw.' }),
        },
      };
    }

    // Auth header retrieval failure
    if (error instanceof Error && error.message === 'Authentication required') {
      return {
        success: false,
        error: {
          code: 'unauthorized',
          message: i18next.t('errors.pdf_unauthorized', { ns: 'webshop', defaultValue: 'Je bent niet ingelogd. Log opnieuw in om de PDF te downloaden.' }),
          statusCode: 401,
        },
      };
    }

    return {
      success: false,
      error: {
        code: 'network_error',
        message: i18next.t('errors.pdf_network', { ns: 'webshop', defaultValue: 'Er is een netwerkfout opgetreden. Controleer je internetverbinding en probeer het opnieuw.' }),
      },
    };
  }
}

function handleErrorResponse(statusCode: number): PdfDownloadResult {
  switch (statusCode) {
    case 401:
      return {
        success: false,
        error: {
          code: 'unauthorized',
          message: i18next.t('errors.pdf_unauthorized', { ns: 'webshop', defaultValue: 'Je bent niet geautoriseerd om deze PDF te downloaden.' }),
          statusCode: 401,
        },
      };
    case 403:
      return {
        success: false,
        error: {
          code: 'forbidden',
          message: i18next.t('errors.pdf_forbidden', { ns: 'webshop', defaultValue: 'Je hebt geen toegang tot deze orderbevestiging.' }),
          statusCode: 403,
        },
      };
    case 404:
      return {
        success: false,
        error: {
          code: 'not_found',
          message: i18next.t('errors.pdf_not_found', { ns: 'webshop', defaultValue: 'De bestelling is niet gevonden.' }),
          statusCode: 404,
        },
      };
    default:
      return {
        success: false,
        error: {
          code: 'server_error',
          message: i18next.t('errors.pdf_server_error', { ns: 'webshop', defaultValue: 'De PDF kon niet worden gegenereerd. Probeer het later opnieuw.' }),
          statusCode,
        },
      };
  }
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

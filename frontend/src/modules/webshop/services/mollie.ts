/**
 * Mollie Payment Service
 *
 * Handles the Mollie payment flow for the H-DCN webshop.
 * Replaces the previous Stripe integration (stripe.ts).
 *
 * The frontend does NOT call Mollie directly — all payment creation
 * goes through the backend's POST /orders endpoint which returns
 * a checkout_url for redirect-based payment.
 *
 * Requirements: 9.2, 9.5, 9.8, 9.9
 */

import { ApiService, ApiResponse } from '../../../services/apiService';
import i18next from 'i18next';

// Payment method types supported by Mollie
export type MolliePaymentMethod = 'ideal' | 'creditcard';

// Response from backend when creating an order with online payment
export interface MolliePaymentResponse {
  order_id: string;
  payment_status: 'pending';
  checkout_url: string;
}

// Response from backend when creating a bank transfer order
export interface TransferInstructionsResponse {
  order_id: string;
  payment_status: 'unpaid';
  transfer_instructions: {
    reference: string;
    iban: string;
    amount: number;
  };
}

// Union type for order creation responses
export type OrderPaymentResponse = MolliePaymentResponse | TransferInstructionsResponse;

// Payment return statuses the user can arrive with after Mollie redirect
export type PaymentReturnStatus = 'success' | 'failed' | 'expired' | 'cancelled' | 'pending';

// Result of handling payment return
export interface PaymentReturnResult {
  status: PaymentReturnStatus;
  orderId: string | null;
  message: string;
  canRetry: boolean;
}

/**
 * Create a Mollie payment by submitting the order to the backend.
 *
 * The backend's POST /orders endpoint creates the order, initiates a Mollie
 * payment session, and returns the checkout_url for browser redirect.
 *
 * @param orderId - The cart/order ID to create payment for
 * @param method - The Mollie payment method ('ideal' or 'creditcard')
 * @returns API response containing checkout_url on success
 */
export async function createMolliePayment(
  orderId: string,
  method: MolliePaymentMethod
): Promise<ApiResponse<MolliePaymentResponse>> {
  if (!orderId || typeof orderId !== 'string') {
    return {
      success: false,
      error: 'Invalid order ID',
    };
  }

  const sanitizedOrderId = orderId.replace(/[^a-zA-Z0-9_-]/g, '');
  if (sanitizedOrderId !== orderId) {
    return {
      success: false,
      error: 'Order ID contains invalid characters',
    };
  }

  if (!(await ApiService.isAuthenticated())) {
    return {
      success: false,
      error: 'Authentication required',
    };
  }

  return ApiService.post<MolliePaymentResponse>('/orders', {
    cart_id: orderId,
    payment_method: method,
  });
}

/**
 * Redirect the browser to the Mollie-hosted payment page.
 *
 * After calling createMolliePayment and receiving a checkout_url,
 * use this function to redirect the user to Mollie's payment page.
 *
 * @param checkoutUrl - The Mollie checkout URL from the backend response
 */
export function handleMollieRedirect(checkoutUrl: string): void {
  if (!checkoutUrl || typeof checkoutUrl !== 'string') {
    throw new Error('Invalid checkout URL');
  }

  // Validate URL format for security
  try {
    const url = new URL(checkoutUrl);
    if (url.protocol !== 'https:') {
      throw new Error('Checkout URL must use HTTPS');
    }
    if (!url.hostname.includes('mollie.com')) {
      throw new Error('Checkout URL must be a Mollie domain');
    }
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error('Invalid checkout URL format');
    }
    throw error;
  }

  window.location.href = checkoutUrl;
}

/**
 * Handle the user returning from Mollie's payment page.
 *
 * After payment, Mollie redirects the user back to our return URL
 * with a status indicator. This function determines the appropriate
 * messaging and actions based on the payment outcome.
 *
 * @param status - The payment return status from the redirect URL
 * @param orderId - Optional order ID from the redirect URL parameters
 * @returns Payment return result with messaging and retry capability
 */
export function handlePaymentReturn(
  status: PaymentReturnStatus,
  orderId?: string | null
): PaymentReturnResult {
  switch (status) {
    case 'success':
      return {
        status: 'success',
        orderId: orderId || null,
        message: i18next.t('payment.return_success_message', { ns: 'webshop', defaultValue: 'Betaling succesvol! Je bestelling is bevestigd.' }),
        canRetry: false,
      };

    case 'failed':
      return {
        status: 'failed',
        orderId: orderId || null,
        message: i18next.t('payment.return_failed_message', { ns: 'webshop', defaultValue: 'De betaling is mislukt. Probeer het opnieuw of kies een andere betaalmethode.' }),
        canRetry: true,
      };

    case 'expired':
      return {
        status: 'expired',
        orderId: orderId || null,
        message: i18next.t('payment.return_expired_message', { ns: 'webshop', defaultValue: 'De betaling is verlopen. Probeer het opnieuw of kies een andere betaalmethode.' }),
        canRetry: true,
      };

    case 'cancelled':
      return {
        status: 'cancelled',
        orderId: orderId || null,
        message: i18next.t('payment.return_cancelled_message', { ns: 'webshop', defaultValue: 'De betaling is geannuleerd. Probeer het opnieuw of kies een andere betaalmethode.' }),
        canRetry: true,
      };

    case 'pending':
      return {
        status: 'pending',
        orderId: orderId || null,
        message: i18next.t('payment.return_pending_message', { ns: 'webshop', defaultValue: 'De betaling wordt verwerkt. Je ontvangt een bevestiging zodra de betaling is afgerond.' }),
        canRetry: false,
      };

    default:
      return {
        status: 'pending',
        orderId: orderId || null,
        message: i18next.t('payment.return_unknown_message', { ns: 'webshop', defaultValue: 'De status van je betaling wordt gecontroleerd.' }),
        canRetry: true,
      };
  }
}

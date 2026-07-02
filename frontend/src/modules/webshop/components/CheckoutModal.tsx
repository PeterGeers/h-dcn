import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  Button,
  Text,
  Alert,
  AlertIcon,
  Box,
  Select,
  HStack,
  Divider,
} from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import PaymentMethodSelector from './PaymentMethodSelector';
import { validateItemFields, ItemFieldError } from './ItemFieldsForm';
import { orderService, parameterService } from '../services/api';
import { handleMollieRedirect, handlePaymentReturn, PaymentReturnResult } from '../services/mollie';
import {
  PaymentMethod,
  TransferInstructions,
  OrderItemField,
  ItemFieldsEntry,
} from '../types/unifiedProduct.types';
import { processDeliveryOptions, getDefaultDeliveryOptions } from '../utils/deliveryOptionsProcessor';
import { formatPrice, toPrice } from '../../../utils/formatPrice';

interface CartItem {
  product_id?: string;
  name?: string;
  price?: number;
  quantity: number;
  variant_id?: string;
  variant_attributes?: Record<string, string>;
  item_fields_data?: ItemFieldsEntry[];
  order_item_fields?: OrderItemField[];
}

interface DeliveryOption {
  value: string;
  label: string;
  cost?: string;
}

interface CheckoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  cartItems: CartItem[];
  onPaymentSuccess: (paymentData: any) => void;
  userEmail: string;
  orderId?: string;
  /** @deprecated Use orderId instead */
  cartId?: string;
}

const CheckoutModal: React.FC<CheckoutModalProps> = ({
  isOpen,
  onClose,
  cartItems,
  onPaymentSuccess,
  userEmail,
  orderId,
  cartId,
}) => {
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('ideal');
  const [transferInstructions, setTransferInstructions] = useState<TransferInstructions | undefined>(undefined);
  const [paymentReturn, setPaymentReturn] = useState<PaymentReturnResult | undefined>(undefined);
  const [itemFieldErrors, setItemFieldErrors] = useState<ItemFieldError[]>([]);
  const [deliveryOptions, setDeliveryOptions] = useState<DeliveryOption[]>([]);
  const [selectedDelivery, setSelectedDelivery] = useState<string>('');
  const [conflictError, setConflictError] = useState<boolean>(false);
  const [orderNumber, setOrderNumber] = useState<string | undefined>(undefined);
  const { t } = useTranslation('webshop');

  // Use orderId prop, fall back to cartId for backward compat
  const activeOrderId = orderId || cartId;

  const totalAmount = cartItems.reduce(
    (sum, item) => sum + (Number(item.price || 0) * item.quantity),
    0
  );

  const deliveryOption = deliveryOptions.find((opt) => opt.value === selectedDelivery);
  const deliveryCost = deliveryOption ? parseFloat(deliveryOption.cost || '0') : 0;
  const finalTotal = totalAmount + deliveryCost;

  // Check if any cart items have order_item_fields that need validation
  const itemsWithFields = cartItems.filter(
    (item) => item.order_item_fields && item.order_item_fields.length > 0
  );

  useEffect(() => {
    const loadDeliveryOptions = async () => {
      try {
        const response = await parameterService.getParameter('leveropties');
        const optionsString = response.data?.value || response.data || '[]';
        const processedOptions = processDeliveryOptions(optionsString);
        setDeliveryOptions(processedOptions);
        if (processedOptions.length > 0) {
          setSelectedDelivery(processedOptions[0].value);
        }
      } catch {
        const defaultOptions = getDefaultDeliveryOptions();
        setDeliveryOptions(defaultOptions);
        setSelectedDelivery(defaultOptions[0]?.value || 'standard');
      }
    };

    if (isOpen) {
      loadDeliveryOptions();
      checkPaymentReturn();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const checkPaymentReturn = useCallback(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const status = urlParams.get('payment_status');
    const returnOrderId = urlParams.get('order_id');

    if (status) {
      const result = handlePaymentReturn(
        status as any,
        returnOrderId
      );
      setPaymentReturn(result);
      // Clean up URL params
      const url = new URL(window.location.href);
      url.searchParams.delete('payment_status');
      url.searchParams.delete('order_id');
      window.history.replaceState({}, '', url.toString());
    }
  }, []);

  /**
   * Validates all item fields across all cart items that have order_item_fields defined.
   * Returns true if validation passes, false otherwise.
   */
  const validateAllItemFields = (): boolean => {
    const allErrors: ItemFieldError[] = [];

    for (const item of itemsWithFields) {
      const fields = item.order_item_fields!;
      const values = item.item_fields_data || [];
      const errors = validateItemFields(fields, values, item.quantity);
      allErrors.push(...errors);
    }

    setItemFieldErrors(allErrors);
    return allErrors.length === 0;
  };

  /**
   * Submit the draft order and then initiate payment.
   * Flow: submitOrder → payOrder → handle response (redirect or transfer instructions).
   * Handles 409 Conflict by showing refresh+retry UI.
   */
  const handleSubmit = async () => {
    setError(null);
    setConflictError(false);

    if (!activeOrderId) {
      setError(t('checkout.no_order_error', { defaultValue: 'Geen bestelling gevonden. Probeer opnieuw.' }));
      return;
    }

    // Validate item fields before submission
    if (itemsWithFields.length > 0) {
      const isValid = validateAllItemFields();
      if (!isValid) {
        setError(t('checkout.fields_required', { defaultValue: 'Vul alle verplichte velden in voordat je de bestelling plaatst.' }));
        return;
      }
    }

    setIsProcessing(true);

    try {
      // Step 1: Submit the draft order (validates all items)
      const submitResponse = await orderService.submitOrder(activeOrderId, {
        delivery_option: deliveryOption?.label || '',
        delivery_cost: deliveryCost,
      });

      if (!submitResponse.success) {
        // Check for 409 Conflict (order was modified)
        const statusCode = (submitResponse as any).status || (submitResponse as any).statusCode;
        const errorMessage = submitResponse.error || '';

        if (statusCode === 409 || errorMessage.toLowerCase().includes('conflict') || errorMessage.toLowerCase().includes('version')) {
          setConflictError(true);
          setError(t('checkout.conflict_error', {
            defaultValue: 'De bestelling is ondertussen gewijzigd. Vernieuw en probeer opnieuw.',
          }));
          setIsProcessing(false);
          return;
        }

        setError(submitResponse.error || t('checkout.submit_error', { defaultValue: 'Er is een fout opgetreden bij het indienen van de bestelling.' }));
        setIsProcessing(false);
        return;
      }

      // Capture order_number from submit response
      const submittedOrderNumber = submitResponse.data?.order_number;
      if (submittedOrderNumber) {
        setOrderNumber(submittedOrderNumber);
      }

      // Step 2: Initiate payment on the submitted order
      const payResponse = await orderService.payOrder(activeOrderId, {
        payment_method: paymentMethod,
      });

      if (!payResponse.success) {
        setError(payResponse.error || t('checkout.payment_error_desc', { defaultValue: 'Er is een probleem opgetreden.' }));
        setIsProcessing(false);
        return;
      }

      const payData = payResponse.data;

      // Handle Mollie redirect for online payments (ideal / creditcard)
      if (payData?.checkout_url) {
        handleMollieRedirect(payData.checkout_url);
        // Browser will redirect, no further action needed
        return;
      }

      // Handle bank transfer response
      if (paymentMethod === 'bank_transfer' && payData?.transfer_instructions) {
        setTransferInstructions(payData.transfer_instructions);
        setSuccess(true);
        setIsProcessing(false);

        onPaymentSuccess({
          paymentMethodId: 'bank_transfer',
          amount: finalTotal,
          items: cartItems,
          deliveryOption: deliveryOption || null,
          orderId: activeOrderId,
          orderNumber: submittedOrderNumber,
          paymentMethod: 'bank_transfer',
          transferInstructions: payData.transfer_instructions,
        });
        return;
      }

      // Fallback: order submitted + payment initiated successfully
      setSuccess(true);
      setIsProcessing(false);
      onPaymentSuccess({
        paymentMethodId: paymentMethod,
        amount: finalTotal,
        items: cartItems,
        deliveryOption: deliveryOption || null,
        orderId: activeOrderId,
        orderNumber: submittedOrderNumber,
        paymentMethod,
      });
    } catch (err: any) {
      // Check for 409 Conflict in exception (axios throws on 4xx)
      const status = err?.response?.status || err?.status;
      if (status === 409) {
        setConflictError(true);
        setError(t('checkout.conflict_error', {
          defaultValue: 'De bestelling is ondertussen gewijzigd. Vernieuw en probeer opnieuw.',
        }));
        setIsProcessing(false);
        return;
      }

      setError(err?.message || t('checkout.submit_error', { defaultValue: 'Er is een fout opgetreden bij het indienen van de bestelling.' }));
      setIsProcessing(false);
    }
  };

  /**
   * Handle 409 conflict: refresh order state and retry submit+pay.
   */
  const handleConflictRetry = async () => {
    setConflictError(false);
    setError(null);
    // Re-attempt submit+pay (parent component should have refreshed order state)
    await handleSubmit();
  };

  const handleRetry = () => {
    setPaymentReturn(undefined);
    setError(null);
    setSuccess(false);
    setTransferInstructions(undefined);
    setConflictError(false);
    setOrderNumber(undefined);
  };

  const handleClose = () => {
    setError(null);
    setSuccess(false);
    setIsProcessing(false);
    setPaymentReturn(undefined);
    setTransferInstructions(undefined);
    setItemFieldErrors([]);
    setConflictError(false);
    setOrderNumber(undefined);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="lg">
      <ModalOverlay />
      <ModalContent bg="black" color="white" borderWidth="3px" borderColor="orange.500">
        <ModalHeader>
          {t('checkout.payment_title', { defaultValue: 'Afrekenen' })}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          {error && (
            <Alert status="error" mb={4} bg="red.600" color="white">
              <AlertIcon />
              <Box flex="1">
                <Text>{error}</Text>
                {conflictError && (
                  <Button
                    size="sm"
                    mt={2}
                    leftIcon={<RepeatIcon />}
                    colorScheme="orange"
                    onClick={handleConflictRetry}
                    isLoading={isProcessing}
                  >
                    {t('checkout.refresh_retry', { defaultValue: 'Vernieuwen en opnieuw proberen' })}
                  </Button>
                )}
              </Box>
            </Alert>
          )}

          {/* Payment return messaging (after Mollie redirect) */}
          {paymentReturn && (
            <Box mb={4}>
              <PaymentMethodSelector
                selectedMethod={paymentMethod}
                onMethodChange={setPaymentMethod}
                paymentReturn={paymentReturn}
                onRetry={handleRetry}
                isDisabled={isProcessing}
              />
            </Box>
          )}

          {/* Success state with bank transfer instructions */}
          {success && transferInstructions && (
            <Alert status="info" mb={4} borderRadius="md" flexDirection="column" alignItems="flex-start" p={4}>
              <AlertIcon />
              <Text fontWeight="bold" mb={2}>
                {t('checkout.order_placed', { defaultValue: 'Bestelling geplaatst!' })}
              </Text>
              {orderNumber && (
                <Box mb={3} p={3} bg="orange.100" borderRadius="md" width="full">
                  <Text fontSize="sm" color="gray.600">
                    {t('checkout.order_number_label', { defaultValue: 'Bestelnummer' })}
                  </Text>
                  <Text fontSize="xl" fontWeight="bold" color="orange.700">
                    {orderNumber}
                  </Text>
                </Box>
              )}
              <Text mb={2}>
                {t('checkout.transfer_instructions', { defaultValue: 'Maak het bedrag over met de volgende gegevens:' })}
              </Text>
              <VStack align="flex-start" spacing={1}>
                <Text>
                  <Text as="span" fontWeight="bold">
                    {t('checkout.reference', { defaultValue: 'Kenmerk' })}:
                  </Text>{' '}
                  {transferInstructions.reference}
                </Text>
                <Text>
                  <Text as="span" fontWeight="bold">IBAN:</Text>{' '}
                  {transferInstructions.iban}
                </Text>
                <Text>
                  <Text as="span" fontWeight="bold">
                    {t('checkout.amount', { defaultValue: 'Bedrag' })}:
                  </Text>{' '}
                  €{transferInstructions.amount.toFixed(2)}
                </Text>
              </VStack>
              <Button mt={4} colorScheme="orange" onClick={handleClose}>
                {t('checkout.close', { defaultValue: 'Sluiten' })}
              </Button>
            </Alert>
          )}

          {/* Success without bank transfer (should not normally appear since Mollie redirects) */}
          {success && !transferInstructions && (
            <Alert status="success" mb={4} bg="green.600" color="white" flexDirection="column" alignItems="flex-start" p={4}>
              <HStack mb={2}>
                <AlertIcon />
                <Text fontWeight="bold">
                  {t('checkout.payment_processing', {
                    defaultValue: 'Bestelling succesvol geplaatst!',
                  })}
                </Text>
              </HStack>
              {orderNumber && (
                <Box p={3} bg="green.700" borderRadius="md" width="full">
                  <Text fontSize="sm" color="green.200">
                    {t('checkout.order_number_label', { defaultValue: 'Bestelnummer' })}
                  </Text>
                  <Text fontSize="xl" fontWeight="bold" color="white">
                    {orderNumber}
                  </Text>
                </Box>
              )}
            </Alert>
          )}

          {/* Main checkout form (hidden when success or paymentReturn is shown) */}
          {!success && !paymentReturn && (
            <VStack spacing={5} align="stretch">
              {/* Order summary */}
              <Box>
                <Text fontWeight="bold" mb={2}>
                  {t('checkout.summary', { defaultValue: 'Overzicht' })}
                </Text>
                {cartItems.map((item, idx) => (
                  <HStack key={idx} justify="space-between" mb={1}>
                    <Text fontSize="sm">
                      {item.name} x {item.quantity}
                    </Text>
                    <Text fontSize="sm">
                      {formatPrice(toPrice(item.price) * item.quantity)}
                    </Text>
                  </HStack>
                ))}
              </Box>

              {/* Item fields validation errors summary */}
              {itemFieldErrors.length > 0 && (
                <Alert status="warning" borderRadius="md" bg="orange.800" color="white">
                  <AlertIcon />
                  <Box>
                    <Text fontWeight="bold" fontSize="sm">
                      {t('checkout.fields_incomplete', { defaultValue: 'Niet alle velden zijn correct ingevuld:' })}
                    </Text>
                    {itemFieldErrors.slice(0, 5).map((err, idx) => (
                      <Text key={idx} fontSize="xs">
                        • Item {err.itemIndex + 1}, veld &quot;{err.fieldId}&quot;: {err.message}
                      </Text>
                    ))}
                    {itemFieldErrors.length > 5 && (
                      <Text fontSize="xs">
                        ...en {itemFieldErrors.length - 5} andere fouten
                      </Text>
                    )}
                  </Box>
                </Alert>
              )}

              {/* Delivery options */}
              {deliveryOptions.length > 0 && (
                <Box>
                  <Text mb={2} fontWeight="medium">
                    {t('checkout.delivery_option', { defaultValue: 'Leveroptie' })}:
                  </Text>
                  <Select
                    value={selectedDelivery}
                    onChange={(e) => setSelectedDelivery(e.target.value)}
                    bg="white"
                    color="black"
                  >
                    {deliveryOptions.map((option, index) => (
                      <option key={index} value={option.value}>
                        {option.label} - €{parseFloat(option.cost || '0').toFixed(2)}
                      </option>
                    ))}
                  </Select>
                </Box>
              )}

              <Divider borderColor="gray.600" />

              {/* Payment method selector */}
              <PaymentMethodSelector
                selectedMethod={paymentMethod}
                onMethodChange={setPaymentMethod}
                transferInstructions={
                  paymentMethod === 'bank_transfer'
                    ? { reference: '...', iban: 'NL00BANK0123456789', amount: finalTotal }
                    : undefined
                }
                onRetry={handleRetry}
                isDisabled={isProcessing}
              />

              <Divider borderColor="gray.600" />

              {/* Totals */}
              <VStack spacing={2} width="full">
                <HStack justify="space-between" width="full">
                  <Text>{t('checkout.subtotal', { defaultValue: 'Subtotaal' })}:</Text>
                  <Text>€{totalAmount.toFixed(2)}</Text>
                </HStack>
                {deliveryCost > 0 && (
                  <HStack justify="space-between" width="full">
                    <Text>{t('checkout.shipping', { defaultValue: 'Verzending' })}:</Text>
                    <Text>€{deliveryCost.toFixed(2)}</Text>
                  </HStack>
                )}
                <HStack justify="space-between" width="full">
                  <Text fontSize="lg" fontWeight="bold">
                    {t('checkout.total', { defaultValue: 'Totaal' })}:
                  </Text>
                  <Text fontSize="lg" fontWeight="bold">
                    €{finalTotal.toFixed(2)}
                  </Text>
                </HStack>
              </VStack>

              {/* Submit button */}
              <Button
                bg="orange.500"
                color="white"
                _hover={{ bg: 'orange.500', opacity: 0.8 }}
                width="full"
                size="lg"
                onClick={handleSubmit}
                isLoading={isProcessing}
                loadingText={t('checkout.processing', { defaultValue: 'Verwerken...' })}
                disabled={isProcessing}
              >
                {paymentMethod === 'bank_transfer'
                  ? t('checkout.place_order', { defaultValue: 'Bestelling plaatsen' })
                  : t('checkout.pay_button', {
                      amount: finalTotal.toFixed(2),
                      defaultValue: `Betaal €${finalTotal.toFixed(2)}`,
                    })}
              </Button>
            </VStack>
          )}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default CheckoutModal;

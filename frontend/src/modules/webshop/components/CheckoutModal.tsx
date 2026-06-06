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

interface CartItem {
  product_id?: string;
  name?: string;
  naam?: string;
  price?: number;
  quantity: number;
  selectedOption?: string;
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
  cartId?: string;
}

const CheckoutModal: React.FC<CheckoutModalProps> = ({
  isOpen,
  onClose,
  cartItems,
  onPaymentSuccess,
  userEmail,
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
  const { t } = useTranslation('webshop');

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
      // Check for payment return status from URL params
      checkPaymentReturn();
    }
  }, [isOpen]);

  const checkPaymentReturn = useCallback(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const status = urlParams.get('payment_status');
    const orderId = urlParams.get('order_id');

    if (status) {
      const result = handlePaymentReturn(
        status as any,
        orderId
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

  const handleSubmit = async () => {
    setError(null);

    // Validate item fields before submission
    if (itemsWithFields.length > 0) {
      const isValid = validateAllItemFields();
      if (!isValid) {
        setError('Vul alle verplichte velden in voordat je de bestelling plaatst.');
        return;
      }
    }

    setIsProcessing(true);

    try {
      // Build order items with item_fields_data
      const orderItems = cartItems.map((item) => ({
        product_id: item.product_id || '',
        variant_id: item.variant_id || '',
        quantity: item.quantity,
        item_fields_data: item.item_fields_data || undefined,
      }));

      const orderData: any = {
        cart_id: cartId,
        payment_method: paymentMethod,
        items: orderItems,
      };

      // Add delivery option if selected
      if (selectedDelivery && deliveryOption) {
        orderData.delivery_option = deliveryOption;
      }

      const response = await orderService.createOrder(orderData);

      if (!response.success) {
        setError(response.error || 'Er is een fout opgetreden bij het plaatsen van de bestelling.');
        setIsProcessing(false);
        return;
      }

      const data = response.data;

      // Handle Mollie redirect for online payments (ideal / creditcard)
      if (data?.checkout_url) {
        handleMollieRedirect(data.checkout_url);
        // Browser will redirect, no further action needed
        return;
      }

      // Handle bank transfer response
      if (paymentMethod === 'bank_transfer' && data?.transfer_instructions) {
        setTransferInstructions(data.transfer_instructions);
        setSuccess(true);
        setIsProcessing(false);

        // Notify parent of success
        onPaymentSuccess({
          paymentMethodId: 'bank_transfer',
          amount: finalTotal,
          items: cartItems,
          deliveryOption: deliveryOption || null,
          orderId: data.order_id,
          paymentMethod: 'bank_transfer',
          transferInstructions: data.transfer_instructions,
        });
        return;
      }

      // Fallback: order created successfully without redirect
      setSuccess(true);
      setIsProcessing(false);
      onPaymentSuccess({
        paymentMethodId: paymentMethod,
        amount: finalTotal,
        items: cartItems,
        deliveryOption: deliveryOption || null,
        orderId: data?.order_id,
        paymentMethod,
      });
    } catch (err: any) {
      setError(err?.message || 'Er is een fout opgetreden bij het plaatsen van de bestelling.');
      setIsProcessing(false);
    }
  };

  const handleRetry = () => {
    setPaymentReturn(undefined);
    setError(null);
    setSuccess(false);
    setTransferInstructions(undefined);
  };

  const handleClose = () => {
    setError(null);
    setSuccess(false);
    setIsProcessing(false);
    setPaymentReturn(undefined);
    setTransferInstructions(undefined);
    setItemFieldErrors([]);
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
              {error}
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
              <Text fontWeight="bold" mb={2}>Bestelling geplaatst!</Text>
              <Text mb={2}>
                Maak het bedrag over met de volgende gegevens:
              </Text>
              <VStack align="flex-start" spacing={1}>
                <Text>
                  <Text as="span" fontWeight="bold">Kenmerk:</Text>{' '}
                  {transferInstructions.reference}
                </Text>
                <Text>
                  <Text as="span" fontWeight="bold">IBAN:</Text>{' '}
                  {transferInstructions.iban}
                </Text>
                <Text>
                  <Text as="span" fontWeight="bold">Bedrag:</Text>{' '}
                  €{transferInstructions.amount.toFixed(2)}
                </Text>
              </VStack>
              <Button mt={4} colorScheme="orange" onClick={handleClose}>
                Sluiten
              </Button>
            </Alert>
          )}

          {/* Success without bank transfer (should not normally appear since Mollie redirects) */}
          {success && !transferInstructions && (
            <Alert status="success" mb={4} bg="green.600" color="white">
              <AlertIcon />
              {t('checkout.payment_processing', {
                defaultValue: 'Bestelling succesvol geplaatst!',
              })}
            </Alert>
          )}

          {/* Main checkout form (hidden when success or paymentReturn is shown) */}
          {!success && !paymentReturn && (
            <VStack spacing={5} align="stretch">
              {/* Order summary */}
              <Box>
                <Text fontWeight="bold" mb={2}>
                  Overzicht
                </Text>
                {cartItems.map((item, idx) => (
                  <HStack key={idx} justify="space-between" mb={1}>
                    <Text fontSize="sm">
                      {item.name || item.naam} x {item.quantity}
                    </Text>
                    <Text fontSize="sm">
                      €{(Number(item.price || 0) * item.quantity).toFixed(2)}
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
                      Niet alle velden zijn correct ingevuld:
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

import React from 'react';
import {
  Box,
  VStack,
  Text,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Button,
  RadioGroup,
  Radio,
  Stack,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { PaymentMethod, TransferInstructions } from '../types/unifiedProduct.types';
import { PaymentReturnResult } from '../services/mollie';

export interface PaymentMethodSelectorProps {
  /** Currently selected payment method */
  selectedMethod: PaymentMethod;
  /** Callback when user selects a different payment method */
  onMethodChange: (method: PaymentMethod) => void;
  /** Bank transfer instructions (shown when bank_transfer is selected) */
  transferInstructions?: TransferInstructions;
  /** Payment return result after Mollie redirect */
  paymentReturn?: PaymentReturnResult;
  /** Callback to retry payment after failure */
  onRetry: () => void;
  /** Whether the selector is disabled (e.g., during submission) */
  isDisabled?: boolean;
}

/**
 * PaymentMethodSelector renders payment method options and handles
 * post-payment messaging for the H-DCN webshop checkout flow.
 *
 * Supports:
 * - iDEAL (Mollie redirect)
 * - Creditcard (Mollie redirect)
 * - Overschrijving / bank transfer (manual, shows instructions)
 *
 * Requirements: 9.1–9.9
 */
const PaymentMethodSelector: React.FC<PaymentMethodSelectorProps> = ({
  selectedMethod,
  onMethodChange,
  transferInstructions,
  paymentReturn,
  onRetry,
  isDisabled = false,
}) => {
  const { t } = useTranslation('webshop');

  // Show payment return messaging if present
  if (paymentReturn) {
    return (
      <Box>
        <Alert
          status={paymentReturn.status === 'success' ? 'success' : 'warning'}
          variant="left-accent"
          borderRadius="md"
          flexDirection="column"
          alignItems="flex-start"
          p={4}
        >
          <AlertIcon />
          <AlertTitle mt={2}>
            {paymentReturn.status === 'success'
              ? t('payment.return_success_title')
              : t('payment.return_failed_title')}
          </AlertTitle>
          <AlertDescription mt={1}>{paymentReturn.message}</AlertDescription>
          {paymentReturn.canRetry && (
            <Button
              mt={3}
              size="sm"
              colorScheme="orange"
              onClick={onRetry}
            >
              {t('payment.retry_button')}
            </Button>
          )}
        </Alert>
      </Box>
    );
  }

  return (
    <VStack align="stretch" spacing={4}>
      <Text fontWeight="bold" fontSize="md">
        {t('payment.method_title')}
      </Text>

      <RadioGroup
        value={selectedMethod}
        onChange={(value) => onMethodChange(value as PaymentMethod)}
        isDisabled={isDisabled}
      >
        <Stack spacing={3}>
          <Radio value="ideal" colorScheme="orange">
            <Box>
              <Text fontWeight="medium">iDEAL</Text>
              <Text fontSize="sm" color="gray.500">
                {t('payment.ideal_description')}
              </Text>
            </Box>
          </Radio>

          <Radio value="creditcard" colorScheme="orange">
            <Box>
              <Text fontWeight="medium">Creditcard</Text>
              <Text fontSize="sm" color="gray.500">
                {t('payment.creditcard_description')}
              </Text>
            </Box>
          </Radio>

          <Radio value="bank_transfer" colorScheme="orange">
            <Box>
              <Text fontWeight="medium">{t('payment.bank_transfer')}</Text>
              <Text fontSize="sm" color="gray.500">
                {t('payment.bank_transfer_description')}
              </Text>
            </Box>
          </Radio>
        </Stack>
      </RadioGroup>

      {/* Bank transfer instructions */}
      {selectedMethod === 'bank_transfer' && transferInstructions && (
        <Alert status="info" variant="left-accent" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle fontSize="sm">{t('payment.transfer_instructions_title')}</AlertTitle>
            <AlertDescription fontSize="sm">
              <VStack align="flex-start" spacing={1} mt={1}>
                <Text>
                  <Text as="span" fontWeight="bold">{t('payment.reference')}</Text>{' '}
                  {transferInstructions.reference}
                </Text>
                <Text>
                  <Text as="span" fontWeight="bold">IBAN:</Text>{' '}
                  {transferInstructions.iban}
                </Text>
                <Text>
                  <Text as="span" fontWeight="bold">{t('payment.amount')}</Text>{' '}
                  €{transferInstructions.amount.toFixed(2)}
                </Text>
              </VStack>
            </AlertDescription>
          </Box>
        </Alert>
      )}
    </VStack>
  );
};

export default PaymentMethodSelector;

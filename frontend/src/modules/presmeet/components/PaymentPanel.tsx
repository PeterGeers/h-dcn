/**
 * PaymentPanel — Displays payment status and initiates Mollie payment.
 *
 * Shows the outstanding amount (total_amount - total_paid), a payment status
 * badge (unpaid/partial/paid), and a "Pay" button that calls the v3
 * presmeetApi.pay() endpoint. On success, redirects to Mollie's checkout_url.
 *
 * Validates: Requirements 7, 11
 */

import React, { useState } from 'react';
import {
  Badge,
  Box,
  Button,
  HStack,
  Heading,
  Text,
  VStack,
  useToast,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { Order, PaymentStatus } from '../types/presmeet.types';
import { presmeetApi } from '../services/presmeetApi';
import { calculateOutstanding, formatCurrency } from '../utils/priceCalculator';

// --- Constants ---

const PAYMENT_STATUS_COLOR: Record<PaymentStatus, string> = {
  unpaid: 'red',
  partial: 'yellow',
  paid: 'green',
};

// --- Props ---

export interface PaymentPanelProps {
  order: Order;
  onPaymentInitiated?: () => void;
}

// --- Component ---

const PaymentPanel: React.FC<PaymentPanelProps> = ({ order, onPaymentInitiated }) => {
  const { t } = useTranslation('eventBooking');
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  const outstanding = calculateOutstanding(order.total_amount, order.total_paid);
  const hasOutstandingBalance = outstanding > 0;
  const isPayDisabled = !hasOutstandingBalance || isLoading;

  const handlePay = async () => {
    setIsLoading(true);
    try {
      const response = await presmeetApi.pay(order.order_id);
      if (response.checkout_url) {
        onPaymentInitiated?.();
        window.location.href = response.checkout_url;
      }
    } catch (error: unknown) {
      const message =
        error instanceof Error
          ? error.message
          : t('payment.payment_error_desc');

      toast({
        title: t('payment.payment_failed'),
        description: message,
        status: 'error',
        duration: 6000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const PAYMENT_STATUS_LABEL: Record<PaymentStatus, string> = {
    unpaid: t('payment.status_unpaid'),
    partial: t('payment.status_partial'),
    paid: t('payment.status_paid'),
  };

  return (
    <Box borderWidth="1px" borderRadius="lg" p={5}>
      <HStack justify="space-between" mb={4}>
        <Heading size="md">{t('payment.title')}</Heading>
        <Badge
          colorScheme={PAYMENT_STATUS_COLOR[order.payment_status]}
          fontSize="sm"
          px={2}
          py={1}
          borderRadius="md"
        >
          {PAYMENT_STATUS_LABEL[order.payment_status]}
        </Badge>
      </HStack>

      <VStack spacing={3} align="stretch">
        {/* Amount breakdown */}
        <HStack justify="space-between">
          <Text color="gray.600">{t('payment.total_amount')}</Text>
          <Text fontWeight="medium">{formatCurrency(order.total_amount)}</Text>
        </HStack>

        <HStack justify="space-between">
          <Text color="gray.600">{t('payment.already_paid')}</Text>
          <Text fontWeight="medium" color="green.600">
            {formatCurrency(order.total_paid)}
          </Text>
        </HStack>

        <HStack justify="space-between" pt={2} borderTopWidth="1px">
          <Text fontWeight="bold">{t('payment.outstanding')}</Text>
          <Text
            fontWeight="bold"
            color={hasOutstandingBalance ? 'red.600' : 'green.600'}
          >
            {formatCurrency(outstanding)}
          </Text>
        </HStack>

        {/* Pay button or fully paid message */}
        {hasOutstandingBalance ? (
          <Button
            colorScheme="blue"
            size="lg"
            width="full"
            mt={2}
            isDisabled={isPayDisabled}
            isLoading={isLoading}
            loadingText={t('payment.redirecting_to_payment')}
            onClick={handlePay}
          >
            {t('payment.pay_button', { amount: formatCurrency(outstanding) })}
          </Button>
        ) : (
          order.total_amount > 0 && (
            <Text color="green.600" fontWeight="medium" textAlign="center" mt={2}>
              {t('payment.fully_paid_short')}
            </Text>
          )
        )}
      </VStack>
    </Box>
  );
};

export default PaymentPanel;

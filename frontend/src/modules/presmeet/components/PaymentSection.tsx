import React, { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Tooltip,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Heading,
  useToast,
} from '@chakra-ui/react';
import {
  OrderStatus,
  PaymentStatus,
  PaymentRecord,
} from '../types/presmeet';
import { presmeetService } from '../services/presmeetApi';

// --- Helpers ---

const PAYMENT_STATUS_COLOR: Record<PaymentStatus, string> = {
  unpaid: 'red',
  partial: 'yellow',
  paid: 'green',
};

function formatEur(amount: number): string {
  return `€${amount.toFixed(2)}`;
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('nl-NL', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// --- Types ---

export interface PaymentSectionProps {
  orderId: string;
  orderStatus: OrderStatus;
  paymentStatus: PaymentStatus;
  totalAmount: number;
  totalPaid: number;
  payments?: PaymentRecord[];
}

// --- Component ---

const PaymentSection: React.FC<PaymentSectionProps> = ({
  orderId,
  orderStatus,
  paymentStatus,
  totalAmount,
  totalPaid,
  payments = [],
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  const remainingBalance = Math.max(0, totalAmount - totalPaid);
  const isDraft = orderStatus === 'draft';
  const isFullyPaid = remainingBalance === 0 && totalAmount > 0;

  const handlePayNow = async () => {
    setIsLoading(true);
    try {
      const response = await presmeetService.createPayment(orderId);
      if (response.success && response.data?.checkout_url) {
        window.location.href = response.data.checkout_url;
      } else {
        toast({
          title: 'Payment Error',
          description: response.error || 'Could not initiate payment. Please try again.',
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    } catch {
      toast({
        title: 'Payment Error',
        description: 'An unexpected error occurred. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box>
      <HStack mb={4} justify="space-between">
        <Heading size="md">Payment</Heading>
        <Badge
          colorScheme={PAYMENT_STATUS_COLOR[paymentStatus]}
          fontSize="sm"
          px={2}
          py={1}
        >
          {paymentStatus}
        </Badge>
      </HStack>

      <VStack spacing={4} align="stretch">
        {/* Amount summary */}
        <Box borderWidth="1px" borderRadius="md" p={4}>
          <VStack spacing={2} align="stretch">
            <HStack justify="space-between">
              <Text>Total Amount</Text>
              <Text fontWeight="medium">{formatEur(totalAmount)}</Text>
            </HStack>
            <HStack justify="space-between">
              <Text>Total Paid</Text>
              <Text fontWeight="medium" color="green.500">
                {formatEur(totalPaid)}
              </Text>
            </HStack>
            <HStack justify="space-between" pt={2} borderTopWidth="1px">
              <Text fontWeight="bold">Remaining Balance</Text>
              <Text fontWeight="bold" color={remainingBalance > 0 ? 'red.500' : 'green.500'}>
                {formatEur(remainingBalance)}
              </Text>
            </HStack>
          </VStack>
        </Box>

        {/* Pay Now button */}
        {!isFullyPaid && (
          <Tooltip
            label="Order must be submitted before payment"
            isDisabled={!isDraft}
            hasArrow
          >
            <Box>
              <Button
                colorScheme="blue"
                size="lg"
                width="full"
                isDisabled={isDraft}
                isLoading={isLoading}
                loadingText="Redirecting..."
                onClick={handlePayNow}
              >
                Pay Now ({formatEur(remainingBalance)})
              </Button>
            </Box>
          </Tooltip>
        )}

        {isFullyPaid && (
          <Text color="green.500" fontWeight="medium" textAlign="center">
            ✓ Fully paid
          </Text>
        )}

        {/* Payment history */}
        {payments.length > 0 && (
          <Box>
            <Text fontWeight="bold" mb={2}>
              Payment History
            </Text>
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>Date</Th>
                  <Th>Description</Th>
                  <Th>Status</Th>
                  <Th isNumeric>Amount</Th>
                </Tr>
              </Thead>
              <Tbody>
                {payments.map((payment) => (
                  <Tr key={payment.payment_id}>
                    <Td>{formatDate(payment.created_at)}</Td>
                    <Td>{payment.description || '—'}</Td>
                    <Td>
                      <Badge
                        colorScheme={payment.status === 'paid' ? 'green' : 'gray'}
                        size="sm"
                      >
                        {payment.status}
                      </Badge>
                    </Td>
                    <Td isNumeric>{formatEur(payment.amount)}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        )}
      </VStack>
    </Box>
  );
};

export default PaymentSection;

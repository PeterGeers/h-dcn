/**
 * PaymentsTab — Displays payment aggregates and order payment list.
 *
 * Top section: Aggregate stats cards (Total Charged, Total Paid, Total Outstanding)
 * Bottom section: Order payment list table with payment status badges
 *
 * Validates: Requirements 5.1, 5.2
 */

import React from 'react';
import {
  Box,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Spinner,
  Alert,
  AlertIcon,
  Text,
} from '@chakra-ui/react';
import { useAdminPayments } from '../hooks/useAdminPayments';
import { PaymentRecordForm } from './PaymentRecordForm';
import { useAdminPermissions } from '../hooks/useAdminPermissions';

interface PaymentsTabProps {
  tenant: string;
}

function getPaymentStatusBadge(status: 'paid' | 'partial' | 'unpaid') {
  switch (status) {
    case 'paid':
      return <Badge colorScheme="green">Betaald</Badge>;
    case 'partial':
      return <Badge colorScheme="yellow">Deels betaald</Badge>;
    case 'unpaid':
      return <Badge colorScheme="red">Onbetaald</Badge>;
    default:
      return <Badge>{status}</Badge>;
  }
}

function formatCurrency(amount: number): string {
  return `€ ${(Number(amount) || 0).toFixed(2)}`;
}

export const PaymentsTab: React.FC<PaymentsTabProps> = ({ tenant }) => {
  const { aggregates, orderPayments, loading, error, recordPayment } =
    useAdminPayments(tenant);
  const { canMutate } = useAdminPermissions();

  if (loading) {
    return (
      <Box p={4} textAlign="center">
        <Spinner size="lg" color="orange.400" />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert status="error" borderRadius="md">
        <AlertIcon />
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      {/* Aggregate Stats */}
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={6}>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal Gefactureerd</StatLabel>
          <StatNumber color="white">{formatCurrency(aggregates.totalCharged)}</StatNumber>
          <StatHelpText color="gray.400">Alle bestellingen</StatHelpText>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal Betaald</StatLabel>
          <StatNumber color="green.300">{formatCurrency(aggregates.totalPaid)}</StatNumber>
          <StatHelpText color="gray.400">Ontvangen betalingen</StatHelpText>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal Openstaand</StatLabel>
          <StatNumber color="red.300">{formatCurrency(aggregates.totalOutstanding)}</StatNumber>
          <StatHelpText color="gray.400">Nog te ontvangen</StatHelpText>
        </Stat>
      </SimpleGrid>

      {/* Manual Payment Recording Form */}
      {canMutate && <PaymentRecordForm onSubmit={recordPayment} />}

      {/* Order Payment List */}
      <Box bg="gray.800" borderRadius="md" overflowX="auto" mt={6}>
        <Text fontSize="lg" fontWeight="bold" color="white" p={4} pb={2}>
          Betalingen per bestelling
        </Text>
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              <Th color="gray.400">Bestelling ID</Th>
              <Th color="gray.400">Tenant</Th>
              <Th color="gray.400">Klant</Th>
              <Th color="gray.400" isNumeric>Totaal</Th>
              <Th color="gray.400" isNumeric>Betaald</Th>
              <Th color="gray.400" isNumeric>Openstaand</Th>
              <Th color="gray.400">Status</Th>
            </Tr>
          </Thead>
          <Tbody>
            {orderPayments.length === 0 ? (
              <Tr>
                <Td colSpan={7} textAlign="center" color="gray.500">
                  Geen betalingsgegevens gevonden
                </Td>
              </Tr>
            ) : (
              orderPayments.map((order) => (
                <Tr key={order.order_id}>
                  <Td color="white" fontFamily="mono" fontSize="xs">
                    {order.order_id.substring(0, 8)}...
                  </Td>
                  <Td>
                    <Badge colorScheme={order.tenant === 'presmeet' ? 'purple' : 'blue'}>
                      {order.tenant}
                    </Badge>
                  </Td>
                  <Td color="white">{order.customer}</Td>
                  <Td color="white" isNumeric>{formatCurrency(order.total)}</Td>
                  <Td color="green.300" isNumeric>{formatCurrency(order.paid)}</Td>
                  <Td color="red.300" isNumeric>{formatCurrency(order.outstanding)}</Td>
                  <Td>{getPaymentStatusBadge(order.payment_status)}</Td>
                </Tr>
              ))
            )}
          </Tbody>
        </Table>
      </Box>
    </Box>
  );
};

export default PaymentsTab;

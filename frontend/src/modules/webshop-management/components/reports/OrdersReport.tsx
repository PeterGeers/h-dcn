/**
 * OrdersReport — Order list with details, invoice-style single-order view, totals.
 *
 * Validates: Requirements 11.8, 11.9, 11.10
 */

import React, { useState } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  Badge,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Button,
  Divider,
  HStack,
} from '@chakra-ui/react';
import { ReportResponse, AdminOrder } from '../../types/admin.types';
import { formatCurrency, formatDate } from '../ReportsTab';

interface OrdersReportProps {
  report: ReportResponse;
}

const PAYMENT_STATUS_COLOR: Record<string, string> = {
  paid: 'green',
  partial: 'yellow',
  unpaid: 'red',
};

export const OrdersReport: React.FC<OrdersReportProps> = ({ report }) => {
  const { orders = [] } = report;
  const [selectedOrder, setSelectedOrder] = useState<AdminOrder | null>(null);

  const totalPaid = orders.reduce((sum, o) => sum + o.amount_paid, 0);
  const totalOutstanding = orders.reduce((sum, o) => sum + o.outstanding, 0);
  const totalRevenue = orders.reduce((sum, o) => sum + o.total_amount, 0);

  if (selectedOrder) {
    return (
      <OrderInvoiceView
        order={selectedOrder}
        onBack={() => setSelectedOrder(null)}
      />
    );
  }

  return (
    <Box>
      {/* Totals Overview */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4} mb={6}>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Aantal bestellingen</StatLabel>
          <StatNumber color="white">{orders.length}</StatNumber>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totale omzet</StatLabel>
          <StatNumber color="white">{formatCurrency(totalRevenue)}</StatNumber>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal betaald</StatLabel>
          <StatNumber color="green.300">{formatCurrency(totalPaid)}</StatNumber>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal openstaand</StatLabel>
          <StatNumber color="red.300">{formatCurrency(totalOutstanding)}</StatNumber>
        </Stat>
      </SimpleGrid>

      {/* Order List */}
      <Box bg="gray.800" borderRadius="md" p={4}>
        <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
          Bestellingen ({orders.length})
        </Text>
        {orders.length === 0 ? (
          <Text color="gray.400">Geen bestellingen gevonden.</Text>
        ) : (
          <Box overflowX="auto">
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th color="gray.400">Order ID</Th>
                  <Th color="gray.400">Klant / Club</Th>
                  <Th color="gray.400">Status</Th>
                  <Th color="gray.400">Betaling</Th>
                  <Th color="gray.400" isNumeric>Items</Th>
                  <Th color="gray.400" isNumeric>Totaal</Th>
                  <Th color="gray.400" isNumeric>Betaald</Th>
                  <Th color="gray.400" isNumeric>Openstaand</Th>
                  <Th color="gray.400">Datum</Th>
                  <Th color="gray.400"></Th>
                </Tr>
              </Thead>
              <Tbody>
                {orders.map((order) => (
                  <Tr key={order.order_id} _hover={{ bg: 'gray.700' }}>
                    <Td>
                      <Text fontSize="xs" fontFamily="mono" color="white">
                        {order.order_id.slice(0, 12)}…
                      </Text>
                    </Td>
                    <Td>
                      <Text fontSize="sm" color="white">{order.customer_name}</Text>
                      {order.club_name && (
                        <Text fontSize="xs" color="gray.400">{order.club_name}</Text>
                      )}
                    </Td>
                    <Td>
                      <Badge fontSize="xs" colorScheme="blue">{order.status}</Badge>
                    </Td>
                    <Td>
                      <Badge
                        fontSize="xs"
                        colorScheme={PAYMENT_STATUS_COLOR[order.payment_status] || 'gray'}
                      >
                        {order.payment_status}
                      </Badge>
                    </Td>
                    <Td color="white" isNumeric fontSize="sm">{order.items.length}</Td>
                    <Td color="white" isNumeric fontSize="sm">{formatCurrency(order.total_amount)}</Td>
                    <Td color="white" isNumeric fontSize="sm">{formatCurrency(order.amount_paid)}</Td>
                    <Td color="white" isNumeric fontSize="sm">{formatCurrency(order.outstanding)}</Td>
                    <Td color="white" fontSize="xs">{formatDate(order.created_at)}</Td>
                    <Td>
                      <Button
                        size="xs"
                        variant="ghost"
                        colorScheme="orange"
                        onClick={() => setSelectedOrder(order)}
                      >
                        Details
                      </Button>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        )}
      </Box>
    </Box>
  );
};

// --- Invoice-style single order view ---

interface OrderInvoiceViewProps {
  order: AdminOrder;
  onBack: () => void;
}

const OrderInvoiceView: React.FC<OrderInvoiceViewProps> = ({ order, onBack }) => {
  const subtotal = order.items.reduce((sum, item) => sum + item.unit_price * item.quantity, 0);

  return (
    <Box>
      <Button size="sm" variant="outline" colorScheme="orange" mb={4} onClick={onBack}>
        ← Terug naar overzicht
      </Button>

      {/* Order Header */}
      <Box bg="gray.800" borderRadius="md" p={4} mb={4}>
        <HStack justify="space-between" mb={3}>
          <Box>
            <Text fontSize="lg" fontWeight="bold" color="white">
              Order: {order.order_id.slice(0, 12)}…
            </Text>
            <Text fontSize="sm" color="gray.400">
              {order.customer_name}
              {order.club_name && ` — ${order.club_name}`}
            </Text>
          </Box>
          <Box textAlign="right">
            <Badge colorScheme="blue" mb={1}>{order.status}</Badge>
            <br />
            <Badge
              colorScheme={PAYMENT_STATUS_COLOR[order.payment_status] || 'gray'}
            >
              {order.payment_status}
            </Badge>
          </Box>
        </HStack>
        <Text fontSize="xs" color="gray.400">
          Aangemaakt: {formatDate(order.created_at)}
          {order.submitted_at && ` | Ingediend: ${formatDate(order.submitted_at)}`}
        </Text>
      </Box>

      {/* Line Items */}
      <Box bg="gray.800" borderRadius="md" p={4} mb={4}>
        <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
          Orderregels
        </Text>
        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th color="gray.400">Product</Th>
                <Th color="gray.400">Variant</Th>
                <Th color="gray.400" isNumeric>Aantal</Th>
                <Th color="gray.400" isNumeric>Stuksprijs</Th>
                <Th color="gray.400" isNumeric>Regeltotaal</Th>
              </Tr>
            </Thead>
            <Tbody>
              {order.items.map((item, idx) => (
                <Tr key={idx}>
                  <Td color="white">{item.name}</Td>
                  <Td color="white" fontSize="sm">
                    {item.variant_attributes
                      ? Object.entries(item.variant_attributes)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(', ')
                      : '—'}
                  </Td>
                  <Td color="white" isNumeric>{item.quantity}</Td>
                  <Td color="white" isNumeric>{formatCurrency(item.unit_price)}</Td>
                  <Td color="white" isNumeric fontWeight="medium">
                    {formatCurrency(item.unit_price * item.quantity)}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </Box>

      {/* Payment History */}
      {order.payments && order.payments.length > 0 && (
        <Box bg="gray.800" borderRadius="md" p={4} mb={4}>
          <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
            Betalingen ({order.payments.length})
          </Text>
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th color="gray.400">Datum</Th>
                <Th color="gray.400" isNumeric>Bedrag</Th>
                <Th color="gray.400">Omschrijving</Th>
                <Th color="gray.400">Geregistreerd door</Th>
              </Tr>
            </Thead>
            <Tbody>
              {order.payments.map((payment) => (
                <Tr key={payment.payment_id}>
                  <Td color="white" fontSize="sm">{formatDate(payment.date)}</Td>
                  <Td color="green.300" isNumeric>{formatCurrency(payment.amount)}</Td>
                  <Td color="white" fontSize="sm">{payment.description || '—'}</Td>
                  <Td color="gray.400" fontSize="xs">{payment.recorded_by}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}

      {/* Summary */}
      <Box bg="gray.700" borderRadius="md" p={4}>
        <SimpleGrid columns={2} spacing={2} maxW="300px" ml="auto">
          <Text color="gray.300" fontSize="sm">Subtotaal:</Text>
          <Text color="white" fontSize="sm" textAlign="right">{formatCurrency(subtotal)}</Text>
          <Text color="gray.300" fontSize="sm" fontWeight="bold">Totaal:</Text>
          <Text color="white" fontSize="sm" fontWeight="bold" textAlign="right">
            {formatCurrency(order.total_amount)}
          </Text>
          <Divider gridColumn="span 2" borderColor="gray.600" />
          <Text color="gray.300" fontSize="sm">Betaald:</Text>
          <Text color="green.300" fontSize="sm" textAlign="right">
            {formatCurrency(order.amount_paid)}
          </Text>
          <Text color="gray.300" fontSize="sm">Openstaand:</Text>
          <Text color="red.300" fontSize="sm" textAlign="right">
            {formatCurrency(order.outstanding)}
          </Text>
        </SimpleGrid>
      </Box>
    </Box>
  );
};

export default OrdersReport;

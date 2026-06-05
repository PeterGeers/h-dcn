/**
 * OrdersTab Component
 *
 * Displays all orders in a Chakra Table with columns for Order ID,
 * Tenant badge, Customer/Club name, Status badge, Payment status badge,
 * Total, Paid, Outstanding, Created date, and Submitted date.
 *
 * Clickable rows open the OrderDetailDrawer for full order details
 * and state transition controls.
 *
 * Validates: Requirements 4.3, 4.4, 4.5, 4.6, 4.11, 4.12
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
  Badge,
  Text,
  Spinner,
  Alert,
  AlertIcon,
  useDisclosure,
} from '@chakra-ui/react';
import { useAdminOrders } from '../hooks/useAdminOrders';
import { StatusBadge } from './StatusBadge';
import { OrderDetailDrawer } from './OrderDetailDrawer';
import { AdminOrder } from '../types/admin.types';

export interface OrdersTabProps {
  /** Active tenant filter value (empty string = all) */
  tenant: string;
}

const PAYMENT_STATUS_COLOR: Record<string, string> = {
  paid: 'green',
  partial: 'yellow',
  unpaid: 'red',
};

function formatDate(dateStr?: string): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('nl-NL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

function formatCurrency(amount: number): string {
  return `€ ${(Number(amount) || 0).toFixed(2)}`;
}

export const OrdersTab: React.FC<OrdersTabProps> = ({ tenant }) => {
  const { orders, loading, error, refetch } = useAdminOrders(tenant);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedOrder, setSelectedOrder] = useState<AdminOrder | null>(null);

  const handleRowClick = (order: AdminOrder) => {
    setSelectedOrder(order);
    onOpen();
  };

  const handleDrawerClose = () => {
    setSelectedOrder(null);
    onClose();
  };

  const handleOrderUpdated = () => {
    refetch();
  };

  if (loading) {
    return (
      <Box p={8} textAlign="center">
        <Spinner size="lg" color="orange.400" />
        <Text mt={2} color="gray.400">Bestellingen laden...</Text>
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

  if (orders.length === 0) {
    return (
      <Box p={8} textAlign="center">
        <Text color="gray.400">Geen bestellingen gevonden.</Text>
      </Box>
    );
  }

  return (
    <Box>
      <Box overflowX="auto">
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              <Th>Order ID</Th>
              <Th>Tenant</Th>
              <Th>Klant / Club</Th>
              <Th>Status</Th>
              <Th>Betaling</Th>
              <Th isNumeric>Totaal</Th>
              <Th isNumeric>Betaald</Th>
              <Th isNumeric>Openstaand</Th>
              <Th>Aangemaakt</Th>
              <Th>Ingediend</Th>
            </Tr>
          </Thead>
          <Tbody>
            {orders.map((order) => (
              <Tr
                key={order.order_id}
                cursor="pointer"
                _hover={{ bg: 'gray.700' }}
                onClick={() => handleRowClick(order)}
              >
                <Td>
                  <Text fontSize="xs" fontFamily="mono">
                    {order.order_id.slice(0, 12)}…
                  </Text>
                </Td>
                <Td>
                  <Badge
                    colorScheme={order.tenant === 'presmeet' ? 'purple' : 'blue'}
                    fontSize="xs"
                  >
                    {order.tenant}
                  </Badge>
                </Td>
                <Td>
                  <Text fontSize="sm">{order.customer_name}</Text>
                  {order.club_name && (
                    <Text fontSize="xs" color="gray.400">
                      {order.club_name}
                    </Text>
                  )}
                </Td>
                <Td>
                  <StatusBadge status={order.status} />
                </Td>
                <Td>
                  <Badge
                    colorScheme={PAYMENT_STATUS_COLOR[order.payment_status] || 'gray'}
                    fontSize="xs"
                  >
                    {order.payment_status}
                  </Badge>
                </Td>
                <Td isNumeric fontSize="sm">{formatCurrency(order.total_amount)}</Td>
                <Td isNumeric fontSize="sm">{formatCurrency(order.amount_paid)}</Td>
                <Td isNumeric fontSize="sm">{formatCurrency(order.outstanding)}</Td>
                <Td fontSize="xs">{formatDate(order.created_at)}</Td>
                <Td fontSize="xs">{formatDate(order.submitted_at)}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>

      {selectedOrder && (
        <OrderDetailDrawer
          order={selectedOrder}
          isOpen={isOpen}
          onClose={handleDrawerClose}
          onOrderUpdated={handleOrderUpdated}
          tenant={tenant}
        />
      )}
    </Box>
  );
};

export default OrdersTab;

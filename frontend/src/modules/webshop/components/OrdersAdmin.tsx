import React, { useState } from 'react';
import {
  Box,
  VStack,
  Text,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Select,
  HStack,
  Spinner,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { useAdminOrders } from '../../webshop-management/hooks/useAdminOrders';
import { AdminOrder } from '../../webshop-management/types/admin.types';

const PAYMENT_STATUS_COLOR: Record<string, string> = {
  paid: 'green',
  partial: 'yellow',
  unpaid: 'red',
  pending: 'orange',
  awaiting_payment: 'blue',
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

const OrdersAdmin: React.FC = () => {
  const { t } = useTranslation('webshop');
  const [paymentStatusFilter, setPaymentStatusFilter] = useState<string>('');

  const { orders, loading, error } = useAdminOrders(
    undefined,
    undefined,
    paymentStatusFilter || undefined
  );

  if (loading) {
    return (
      <Box p={6} bg="white" borderRadius="md" textAlign="center">
        <Spinner size="lg" color="orange.400" />
        <Text mt={2} color="gray.600">{t('orders_admin.loading')}</Text>
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
    <Box p={6} bg="white" borderRadius="md" color="black">
      <VStack spacing={4} align="stretch">
        <HStack justify="space-between" align="center">
          <Text fontSize="xl" fontWeight="bold">
            {t('orders_admin.title')}
          </Text>
          <Select
            placeholder={t('orders_admin.filter_all')}
            value={paymentStatusFilter}
            onChange={(e) => setPaymentStatusFilter(e.target.value)}
            maxW="220px"
            size="sm"
          >
            <option value="unpaid">{t('orders_admin.status_unpaid')}</option>
            <option value="pending">{t('orders_admin.status_pending')}</option>
            <option value="awaiting_payment">{t('orders_admin.status_awaiting_payment')}</option>
            <option value="paid">{t('orders_admin.status_paid')}</option>
          </Select>
        </HStack>

        {orders.length === 0 ? (
          <Text color="gray.500">{t('orders_admin.no_orders')}</Text>
        ) : (
          <Box overflowX="auto">
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>{t('orders_admin.col_order_number')}</Th>
                  <Th>{t('orders_admin.col_customer')}</Th>
                  <Th>{t('orders_admin.col_status')}</Th>
                  <Th>{t('orders_admin.col_payment_status')}</Th>
                  <Th>{t('orders_admin.col_invoice')}</Th>
                  <Th isNumeric>{t('orders_admin.col_total')}</Th>
                  <Th>{t('orders_admin.col_date')}</Th>
                </Tr>
              </Thead>
              <Tbody>
                {orders.map((order: AdminOrder) => (
                  <Tr
                    key={order.order_id}
                    bg={order.invoice_number ? 'green.50' : undefined}
                  >
                    <Td>
                      <Text fontSize="sm" fontWeight="medium">
                        {order.order_number || order.order_id.slice(0, 12) + '…'}
                      </Text>
                    </Td>
                    <Td>
                      <Text fontSize="sm">{order.customer_name}</Text>
                      {order.club_name && (
                        <Text fontSize="xs" color="gray.500">
                          {order.club_name}
                        </Text>
                      )}
                    </Td>
                    <Td>
                      <Badge fontSize="xs" colorScheme="blue">
                        {order.status}
                      </Badge>
                    </Td>
                    <Td>
                      <Badge
                        fontSize="xs"
                        colorScheme={PAYMENT_STATUS_COLOR[order.payment_status] || 'gray'}
                      >
                        {t(`orders_admin.status_${order.payment_status}`, order.payment_status)}
                      </Badge>
                    </Td>
                    <Td>
                      {order.invoice_number ? (
                        <Badge colorScheme="purple" fontSize="xs">
                          {order.invoice_number}
                        </Badge>
                      ) : (
                        <Text fontSize="xs" color="gray.400">—</Text>
                      )}
                    </Td>
                    <Td isNumeric fontSize="sm">
                      {formatCurrency(order.total_amount)}
                    </Td>
                    <Td fontSize="xs">{formatDate(order.created_at)}</Td>
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

export default OrdersAdmin;

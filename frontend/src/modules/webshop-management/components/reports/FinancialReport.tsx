/**
 * FinancialReport — Displays financial summary: order list with payments,
 * totals overview, and cost breakdown from StockMovements.
 *
 * Validates: Requirements 11.4
 */

import React from 'react';
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
} from '@chakra-ui/react';
import { ReportResponse } from '../../types/admin.types';
import { formatCurrency, formatDate } from '../ReportsTab';

interface FinancialReportProps {
  report: ReportResponse;
}

const PAYMENT_STATUS_COLOR: Record<string, string> = {
  paid: 'green',
  partial: 'yellow',
  unpaid: 'red',
};

export const FinancialReport: React.FC<FinancialReportProps> = ({ report }) => {
  const { summary, orders = [] } = report;

  return (
    <Box>
      {/* Totals Overview */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4} mb={6}>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal Bestellingen</StatLabel>
          <StatNumber color="white">{summary.total_orders}</StatNumber>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totale Omzet</StatLabel>
          <StatNumber color="white">{formatCurrency(summary.total_revenue)}</StatNumber>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal Betaald</StatLabel>
          <StatNumber color="green.300">{formatCurrency(summary.total_paid)}</StatNumber>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal Openstaand</StatLabel>
          <StatNumber color="red.300">{formatCurrency(summary.total_outstanding)}</StatNumber>
        </Stat>
      </SimpleGrid>

      {/* Cost Breakdown from StockMovements */}
      {summary.purchase_cost && (
        <Box bg="gray.800" borderRadius="md" p={4} mb={6}>
          <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
            Kostenanalyse (Inkoopkosten)
          </Text>
          <Text color="gray.300" mb={2}>
            Totale inkoopkosten: {formatCurrency(summary.purchase_cost.total_inbound_cost)}
          </Text>
          {summary.purchase_cost.by_variant && summary.purchase_cost.by_variant.length > 0 && (
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th color="gray.400">Product / Variant</Th>
                  <Th color="gray.400" isNumeric>Gem. inkoopprijs</Th>
                  <Th color="gray.400" isNumeric>Verkoopprijs</Th>
                  <Th color="gray.400" isNumeric>Bruto marge</Th>
                </Tr>
              </Thead>
              <Tbody>
                {summary.purchase_cost.by_variant.map((v) => (
                  <Tr key={v.variant_id}>
                    <Td color="white">{v.product_name}</Td>
                    <Td color="white" isNumeric>{formatCurrency(v.weighted_avg_cost)}</Td>
                    <Td color="white" isNumeric>{formatCurrency(v.selling_price)}</Td>
                    <Td color={v.gross_margin >= 0 ? 'green.300' : 'red.300'} isNumeric>
                      {formatCurrency(v.gross_margin)}
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </Box>
      )}

      {/* Order List with Payment Status */}
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
                  <Th color="gray.400" isNumeric>Totaal</Th>
                  <Th color="gray.400" isNumeric>Betaald</Th>
                  <Th color="gray.400" isNumeric>Openstaand</Th>
                  <Th color="gray.400">Datum</Th>
                </Tr>
              </Thead>
              <Tbody>
                {orders.map((order) => (
                  <Tr key={order.order_id}>
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
                    <Td color="white" isNumeric fontSize="sm">
                      {formatCurrency(order.total_amount)}
                    </Td>
                    <Td color="white" isNumeric fontSize="sm">
                      {formatCurrency(order.amount_paid)}
                    </Td>
                    <Td color="white" isNumeric fontSize="sm">
                      {formatCurrency(order.outstanding)}
                    </Td>
                    <Td color="white" fontSize="xs">{formatDate(order.created_at)}</Td>
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

export default FinancialReport;

/**
 * StockMovementsReport — Inbound/sale movements, totals with weighted average cost.
 *
 * Validates: Requirements 11.11, 11.12
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
import { ReportResponse, StockMovement } from '../../types/admin.types';
import { formatCurrency, formatDate } from '../ReportsTab';

interface StockMovementsReportProps {
  report: ReportResponse;
}

export const StockMovementsReport: React.FC<StockMovementsReportProps> = ({ report }) => {
  const movements: StockMovement[] = report.movements || [];

  const inboundMovements = movements.filter((m) => m.type === 'inbound');
  const saleMovements = movements.filter((m) => m.type === 'sale');

  const totalInboundQty = inboundMovements.reduce((sum, m) => sum + m.quantity, 0);
  const totalInboundCost = inboundMovements.reduce(
    (sum, m) => sum + (m.total_cost ?? (m.purchase_price_per_unit ?? 0) * m.quantity),
    0
  );
  const totalSoldQty = saleMovements.reduce((sum, m) => sum + Math.abs(m.quantity), 0);

  // Calculate weighted average cost per variant
  const variantCosts: Record<string, { totalCost: number; totalQty: number; name: string }> = {};
  for (const m of inboundMovements) {
    if (!variantCosts[m.variant_id]) {
      variantCosts[m.variant_id] = { totalCost: 0, totalQty: 0, name: m.variant_id };
    }
    const cost = m.total_cost ?? (m.purchase_price_per_unit ?? 0) * m.quantity;
    variantCosts[m.variant_id].totalCost += cost;
    variantCosts[m.variant_id].totalQty += m.quantity;
  }

  const weightedAverages = Object.entries(variantCosts).map(([variantId, data]) => ({
    variant_id: variantId,
    weighted_avg_cost: data.totalQty > 0 ? data.totalCost / data.totalQty : 0,
    total_inbound: data.totalQty,
    total_cost: data.totalCost,
  }));

  return (
    <Box>
      {/* Totals Overview */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4} mb={6}>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal inbound</StatLabel>
          <StatNumber color="white">{totalInboundQty}</StatNumber>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totale inkoopkosten</StatLabel>
          <StatNumber color="white">{formatCurrency(totalInboundCost)}</StatNumber>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal verkocht</StatLabel>
          <StatNumber color="white">{totalSoldQty}</StatNumber>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Gemiddelde inkoopprijs</StatLabel>
          <StatNumber color="white">
            {totalInboundQty > 0 ? formatCurrency(totalInboundCost / totalInboundQty) : '—'}
          </StatNumber>
        </Stat>
      </SimpleGrid>

      {/* Weighted Average per Variant */}
      {weightedAverages.length > 0 && (
        <Box bg="gray.800" borderRadius="md" p={4} mb={6}>
          <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
            Gewogen gemiddelde kosten per variant
          </Text>
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th color="gray.400">Variant ID</Th>
                <Th color="gray.400" isNumeric>Totaal inbound</Th>
                <Th color="gray.400" isNumeric>Totale kosten</Th>
                <Th color="gray.400" isNumeric>Gem. inkoopprijs</Th>
              </Tr>
            </Thead>
            <Tbody>
              {weightedAverages.map((wa) => (
                <Tr key={wa.variant_id}>
                  <Td>
                    <Text fontSize="xs" fontFamily="mono" color="white">
                      {wa.variant_id.slice(0, 12)}…
                    </Text>
                  </Td>
                  <Td color="white" isNumeric>{wa.total_inbound}</Td>
                  <Td color="white" isNumeric>{formatCurrency(wa.total_cost)}</Td>
                  <Td color="white" isNumeric>{formatCurrency(wa.weighted_avg_cost)}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}

      {/* Movements List */}
      <Box bg="gray.800" borderRadius="md" p={4}>
        <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
          Voorraadmutaties ({movements.length})
        </Text>
        {movements.length === 0 ? (
          <Text color="gray.400">Geen voorraadmutaties gevonden.</Text>
        ) : (
          <Box overflowX="auto">
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th color="gray.400">Variant</Th>
                  <Th color="gray.400">Type</Th>
                  <Th color="gray.400" isNumeric>Aantal</Th>
                  <Th color="gray.400" isNumeric>Stuksprijs</Th>
                  <Th color="gray.400" isNumeric>Totale kosten</Th>
                  <Th color="gray.400">Leverancier</Th>
                  <Th color="gray.400">Referentie</Th>
                  <Th color="gray.400">Datum</Th>
                </Tr>
              </Thead>
              <Tbody>
                {movements.map((movement) => (
                  <Tr key={movement.movement_id}>
                    <Td>
                      <Text fontSize="xs" fontFamily="mono" color="white">
                        {movement.variant_id.slice(0, 12)}…
                      </Text>
                    </Td>
                    <Td>
                      <Badge
                        colorScheme={movement.type === 'inbound' ? 'green' : 'orange'}
                        fontSize="xs"
                      >
                        {movement.type === 'inbound' ? 'Inbound' : 'Verkoop'}
                      </Badge>
                    </Td>
                    <Td color="white" isNumeric>{movement.quantity}</Td>
                    <Td color="white" isNumeric>
                      {movement.purchase_price_per_unit != null
                        ? formatCurrency(movement.purchase_price_per_unit)
                        : '—'}
                    </Td>
                    <Td color="white" isNumeric>
                      {movement.total_cost != null
                        ? formatCurrency(movement.total_cost)
                        : '—'}
                    </Td>
                    <Td color="white" fontSize="sm">{movement.supplier_name || '—'}</Td>
                    <Td color="white" fontSize="sm">{movement.reference || '—'}</Td>
                    <Td color="white" fontSize="xs">{formatDate(movement.created_at)}</Td>
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

export default StockMovementsReport;

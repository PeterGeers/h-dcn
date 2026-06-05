/**
 * ReportsTab — Displays report summary, export controls, and tenant-specific metrics.
 *
 * - Summary stats: Total Orders, Total Revenue, Total Paid, Total Outstanding
 * - Generation timestamp display
 * - Refresh button to regenerate report
 * - Export controls (CSV / JSON) respecting tenant filter
 * - PresMeet-specific: counts per product_type by order status
 * - H-DCN-specific: orders, items sold, revenue by product
 *
 * Validates: Requirements 6.1, 6.2, 6.3
 */

import React, { useState } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
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
  Spinner,
  Alert,
  AlertIcon,
  Text,
  HStack,
  Radio,
  RadioGroup,
  Stack,
  Divider,
  Tooltip,
} from '@chakra-ui/react';
import { useAdminReports } from '../hooks/useAdminReports';
import { useAdminPermissions } from '../hooks/useAdminPermissions';
import { OrderStatus } from '../types/admin.types';

interface ReportsTabProps {
  tenant: string;
}

function formatCurrency(amount: number): string {
  return `€ ${amount.toFixed(2)}`;
}

function formatTimestamp(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleString('nl-NL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

export const ReportsTab: React.FC<ReportsTabProps> = ({ tenant }) => {
  const { report, loading, refreshing, error, refresh, exportData } =
    useAdminReports(tenant);
  const { canMutate, canExport } = useAdminPermissions();
  const [exportFormat, setExportFormat] = useState<'csv' | 'json'>('csv');

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

  if (!report) {
    return (
      <Box p={4} bg="gray.800" borderRadius="md" textAlign="center">
        <Text color="gray.400" mb={4}>
          Nog geen rapport gegenereerd.
        </Text>
        <Tooltip label="Products_CRUD vereist" isDisabled={canMutate} hasArrow>
          <Button
            colorScheme="orange"
            onClick={refresh}
            isLoading={refreshing}
            isDisabled={!canMutate}
            loadingText="Genereren..."
          >
            Rapport genereren
          </Button>
        </Tooltip>
      </Box>
    );
  }

  const { summary, generated_at } = report;

  return (
    <Box>
      {/* Summary Stats */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4} mb={4}>
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

      {/* Timestamp + Refresh */}
      <HStack justify="space-between" mb={4}>
        <Text color="gray.400" fontSize="sm">
          Rapport gegenereerd op: {formatTimestamp(generated_at)}
        </Text>
        <Tooltip label="Products_CRUD vereist" isDisabled={canMutate} hasArrow>
          <Button
            colorScheme="orange"
            variant="outline"
            size="sm"
            onClick={refresh}
            isLoading={refreshing}
            isDisabled={!canMutate}
            loadingText="Vernieuwen..."
          >
            Vernieuw Data
          </Button>
        </Tooltip>
      </HStack>

      {/* Export Controls */}
      <Box bg="gray.700" p={4} borderRadius="md" mb={6}>
        <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
          Exporteer rapport
        </Text>
        <HStack spacing={4}>
          <RadioGroup
            value={exportFormat}
            onChange={(val) => setExportFormat(val as 'csv' | 'json')}
          >
            <Stack direction="row" spacing={4}>
              <Radio value="csv" colorScheme="orange">
                <Text color="white">CSV</Text>
              </Radio>
              <Radio value="json" colorScheme="orange">
                <Text color="white">JSON</Text>
              </Radio>
            </Stack>
          </RadioGroup>
          <Tooltip
            label="Products_Export vereist"
            isDisabled={canExport}
            hasArrow
          >
            <Button
              colorScheme="orange"
              size="sm"
              onClick={() => exportData(exportFormat)}
              isDisabled={!canExport}
            >
              Download
            </Button>
          </Tooltip>
        </HStack>
      </Box>

      {/* Tenant-specific metrics */}
      {tenant === 'presmeet' && summary.by_product_type && (
        <PresMeetMetrics byProductType={summary.by_product_type} />
      )}

      {tenant === 'h-dcn' && summary.by_product && (
        <HdcnMetrics byProduct={summary.by_product} />
      )}
    </Box>
  );
};

// --- PresMeet Metrics (Task 18.4) ---

interface PresMeetMetricsProps {
  byProductType: Record<string, Record<OrderStatus, number>>;
}

const PRESMEET_STATUS_COLUMNS: OrderStatus[] = ['draft', 'submitted', 'locked'];

const PresMeetMetrics: React.FC<PresMeetMetricsProps> = ({ byProductType }) => {
  const productTypes = Object.keys(byProductType);

  if (productTypes.length === 0) return null;

  return (
    <Box bg="gray.800" borderRadius="md" p={4} mb={4}>
      <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
        PresMeet — Aantallen per producttype
      </Text>
      <Table variant="simple" size="sm">
        <Thead>
          <Tr>
            <Th color="gray.400">Producttype</Th>
            {PRESMEET_STATUS_COLUMNS.map((status) => (
              <Th key={status} color="gray.400" isNumeric>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </Th>
            ))}
          </Tr>
        </Thead>
        <Tbody>
          {productTypes.map((type) => (
            <Tr key={type}>
              <Td color="white">{type}</Td>
              {PRESMEET_STATUS_COLUMNS.map((status) => (
                <Td key={status} color="white" isNumeric>
                  {byProductType[type]?.[status] ?? 0}
                </Td>
              ))}
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
};

// --- H-DCN Metrics (Task 18.5) ---

interface HdcnMetricsProps {
  byProduct: {
    product_name: string;
    items_sold: number;
    revenue: number;
  }[];
}

const HdcnMetrics: React.FC<HdcnMetricsProps> = ({ byProduct }) => {
  if (byProduct.length === 0) return null;

  const totalOrders = byProduct.reduce((sum, p) => sum + p.items_sold, 0);

  return (
    <Box bg="gray.800" borderRadius="md" p={4} mb={4}>
      <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
        H-DCN Webshop — Verkoop per product
      </Text>
      <Table variant="simple" size="sm">
        <Thead>
          <Tr>
            <Th color="gray.400">Product</Th>
            <Th color="gray.400" isNumeric>Items verkocht</Th>
            <Th color="gray.400" isNumeric>Omzet</Th>
          </Tr>
        </Thead>
        <Tbody>
          {byProduct.map((product, idx) => (
            <Tr key={idx}>
              <Td color="white">{product.product_name}</Td>
              <Td color="white" isNumeric>{product.items_sold}</Td>
              <Td color="white" isNumeric>{formatCurrency(product.revenue)}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
};

export default ReportsTab;

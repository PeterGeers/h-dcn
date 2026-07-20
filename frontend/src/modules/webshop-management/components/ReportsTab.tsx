/**
 * ReportsTab — Unified reporting interface for Webshop Management.
 *
 * Features:
 * - Report type selector: Financial, Products, Orders, Stock Movements
 * - Additional filters: order status, payment status
 * - Export controls (CSV / JSON)
 *
 * Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7,
 * 11.8, 11.9, 11.10, 11.11, 11.12, 11.13, 11.14
 */

import React, { useState } from 'react';
import {
  Box,
  Button,
  Spinner,
  Alert,
  AlertIcon,
  Text,
  HStack,
  Radio,
  RadioGroup,
  Stack,
  Tooltip,
} from '@chakra-ui/react';
import { FilterPanel } from '../../../components/filters';
import type { FilterConfig } from '../../../components/filters/types';
import { useAdminReports } from '../hooks/useAdminReports';
import { useAdminPermissions } from '../hooks/useAdminPermissions';
import {
  ReportType,
  OrderStatusFilter,
  PaymentStatusFilter,
} from '../types/admin.types';
import { FinancialReport } from './reports/FinancialReport';
import { ProductsReport } from './reports/ProductsReport';
import { OrdersReport } from './reports/OrdersReport';
import { StockMovementsReport } from './reports/StockMovementsReport';

interface ReportsTabProps {
  eventFilter?: string;
}

// Exported utility functions for sub-components
export function formatCurrency(amount: number): string {
  return `€ ${(Number(amount) || 0).toFixed(2)}`;
}

export function formatDate(dateStr?: string): string {
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

const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  financial: 'Financieel',
  products: 'Producten',
  orders: 'Bestellingen',
  stock_movements: 'Voorraadmutaties',
};

const REPORT_TYPE_OPTIONS = Object.entries(REPORT_TYPE_LABELS).map(
  ([value, label]) => ({ value, label })
);

const ORDER_STATUS_OPTIONS = [
  { value: 'all', label: 'Alle' },
  { value: 'draft', label: 'Draft' },
  { value: 'submitted', label: 'Ingediend' },
  { value: 'locked', label: 'Vergrendeld' },
  { value: 'paid', label: 'Betaald' },
];

const PAYMENT_STATUS_OPTIONS = [
  { value: 'all', label: 'Alle' },
  { value: 'unpaid', label: 'Onbetaald' },
  { value: 'partial', label: 'Deels betaald' },
  { value: 'paid', label: 'Betaald' },
];

export const ReportsTab: React.FC<ReportsTabProps> = ({ eventFilter = '' }) => {
  const [reportType, setReportType] = useState<ReportType>('financial');
  const [orderStatus, setOrderStatus] = useState<OrderStatusFilter>('all');
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatusFilter>('all');
  const [exportFormat, setExportFormat] = useState<'csv' | 'json'>('csv');

  const { report, loading, refreshing, error, refresh, exportData } =
    useAdminReports(eventFilter, reportType, orderStatus, paymentStatus);
  const { canMutate, canExport } = useAdminPermissions();

  return (
    <Box>
      {/* Report Filters */}
      <Box mb={4}>
        <FilterPanel
          layout="horizontal"
          filters={[
            {
              type: 'single' as const,
              label: 'Rapporttype',
              options: REPORT_TYPE_OPTIONS,
              value: reportType,
              onChange: (v: string | string[]) => setReportType(v as ReportType),
            },
            {
              type: 'single' as const,
              label: 'Order status',
              options: ORDER_STATUS_OPTIONS,
              value: orderStatus,
              onChange: (v: string | string[]) => setOrderStatus(v as OrderStatusFilter),
            },
            {
              type: 'single' as const,
              label: 'Betaalstatus',
              options: PAYMENT_STATUS_OPTIONS,
              value: paymentStatus,
              onChange: (v: string | string[]) => setPaymentStatus(v as PaymentStatusFilter),
            },
          ] as FilterConfig<any>[]}
        />
      </Box>

      {/* Actions bar: Refresh + Export */}
      <HStack justify="space-between" mb={4} flexWrap="wrap" spacing={4}>
        <HStack spacing={2}>
          <Tooltip label="Products_CRUD vereist" isDisabled={canMutate} hasArrow>
            <Button
              colorScheme="orange"
              size="sm"
              onClick={refresh}
              isLoading={refreshing}
              isDisabled={!canMutate}
              loadingText="Genereren..."
            >
              Rapport genereren
            </Button>
          </Tooltip>
          {report && (
            <Text color="gray.400" fontSize="xs">
              Gegenereerd: {formatTimestamp(report.generated_at)}
            </Text>
          )}
        </HStack>

        <HStack spacing={3}>
          <RadioGroup
            value={exportFormat}
            onChange={(val) => setExportFormat(val as 'csv' | 'json')}
          >
            <Stack direction="row" spacing={3}>
              <Radio value="csv" colorScheme="orange" size="sm">
                <Text color="white" fontSize="sm">CSV</Text>
              </Radio>
              <Radio value="json" colorScheme="orange" size="sm">
                <Text color="white" fontSize="sm">JSON</Text>
              </Radio>
            </Stack>
          </RadioGroup>
          <Tooltip label="Products_Export vereist" isDisabled={canExport} hasArrow>
            <Button
              colorScheme="orange"
              variant="outline"
              size="sm"
              onClick={() => exportData(exportFormat)}
              isDisabled={!canExport || !report}
            >
              Download
            </Button>
          </Tooltip>
        </HStack>
      </HStack>

      {/* Loading State */}
      {loading && (
        <Box p={8} textAlign="center">
          <Spinner size="lg" color="orange.400" />
          <Text mt={2} color="gray.400">Rapport laden...</Text>
        </Box>
      )}

      {/* Error State */}
      {error && !loading && (
        <Alert status="error" borderRadius="md" mb={4}>
          <AlertIcon />
          {error}
        </Alert>
      )}

      {/* No Report Yet */}
      {!loading && !error && !report && (
        <Box p={8} bg="gray.800" borderRadius="md" textAlign="center">
          <Text color="gray.400">
            Nog geen rapport gegenereerd. Klik op "Rapport genereren" om te starten.
          </Text>
        </Box>
      )}

      {/* Report Content */}
      {!loading && report && (
        <Box>
          {reportType === 'financial' && <FinancialReport report={report} />}
          {reportType === 'products' && <ProductsReport report={report} />}
          {reportType === 'orders' && <OrdersReport report={report} />}
          {reportType === 'stock_movements' && <StockMovementsReport report={report} />}
        </Box>
      )}
    </Box>
  );
};

export default ReportsTab;

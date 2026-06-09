/**
 * ReportsTab — Unified reporting interface for Webshop Management.
 *
 * Features:
 * - Report type selector: Financial, Products, Orders, Stock Movements
 * - Respects primary event filter from parent (All, Webshop, specific event)
 * - Additional filters: order status, payment status
 * - Export controls (CSV / JSON)
 * - Event context display when event filter is active
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
  Select,
  Badge,
} from '@chakra-ui/react';
import { useAdminReports } from '../hooks/useAdminReports';
import { useAdminPermissions } from '../hooks/useAdminPermissions';
import { useEventFilter, EventOption } from '../hooks/useEventFilter';
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
  eventFilter: string;
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

const ORDER_STATUS_OPTIONS: { value: OrderStatusFilter; label: string }[] = [
  { value: 'all', label: 'Alle' },
  { value: 'draft', label: 'Draft' },
  { value: 'submitted', label: 'Ingediend' },
  { value: 'locked', label: 'Vergrendeld' },
  { value: 'paid', label: 'Betaald' },
];

const PAYMENT_STATUS_OPTIONS: { value: PaymentStatusFilter; label: string }[] = [
  { value: 'all', label: 'Alle' },
  { value: 'unpaid', label: 'Onbetaald' },
  { value: 'partial', label: 'Deels betaald' },
  { value: 'paid', label: 'Betaald' },
];

export const ReportsTab: React.FC<ReportsTabProps> = ({ eventFilter }) => {
  const [reportType, setReportType] = useState<ReportType>('financial');
  const [orderStatus, setOrderStatus] = useState<OrderStatusFilter>('all');
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatusFilter>('all');
  const [exportFormat, setExportFormat] = useState<'csv' | 'json'>('csv');

  const { report, loading, refreshing, error, refresh, exportData } =
    useAdminReports(eventFilter, reportType, orderStatus, paymentStatus);
  const { canMutate, canExport } = useAdminPermissions();
  const { events } = useEventFilter();

  // Resolve event context for display
  const activeEvent: EventOption | undefined = eventFilter && eventFilter !== 'webshop'
    ? events.find((e) => e.event_id === eventFilter)
    : undefined;

  return (
    <Box>
      {/* Report Type Selector */}
      <HStack spacing={4} mb={4} flexWrap="wrap">
        <Box>
          <Text fontSize="xs" color="gray.400" mb={1}>Rapporttype</Text>
          <Select
            value={reportType}
            onChange={(e) => setReportType(e.target.value as ReportType)}
            size="sm"
            maxW="200px"
          >
            {Object.entries(REPORT_TYPE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </Select>
        </Box>
        <Box>
          <Text fontSize="xs" color="gray.400" mb={1}>Order status</Text>
          <Select
            value={orderStatus}
            onChange={(e) => setOrderStatus(e.target.value as OrderStatusFilter)}
            size="sm"
            maxW="160px"
          >
            {ORDER_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </Select>
        </Box>
        <Box>
          <Text fontSize="xs" color="gray.400" mb={1}>Betaalstatus</Text>
          <Select
            value={paymentStatus}
            onChange={(e) => setPaymentStatus(e.target.value as PaymentStatusFilter)}
            size="sm"
            maxW="160px"
          >
            {PAYMENT_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </Select>
        </Box>
      </HStack>

      {/* Event Context */}
      {activeEvent && (
        <Box bg="purple.900" borderRadius="md" p={3} mb={4}>
          <HStack spacing={3}>
            <Badge colorScheme="purple" fontSize="xs">Evenement</Badge>
            <Text color="white" fontSize="sm" fontWeight="medium">
              {activeEvent.name}
            </Text>
          </HStack>
          {report?.event_context && (
            <HStack spacing={4} mt={2}>
              {report.event_context.location && (
                <Text color="gray.300" fontSize="xs">
                  Locatie: {report.event_context.location}
                </Text>
              )}
              {report.event_context.start_date && (
                <Text color="gray.300" fontSize="xs">
                  Van: {formatDate(report.event_context.start_date)}
                </Text>
              )}
              {report.event_context.end_date && (
                <Text color="gray.300" fontSize="xs">
                  Tot: {formatDate(report.event_context.end_date)}
                </Text>
              )}
            </HStack>
          )}
        </Box>
      )}

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

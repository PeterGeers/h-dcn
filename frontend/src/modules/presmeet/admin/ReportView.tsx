import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Select,
  Button,
  VStack,
  HStack,
  Text,
  Heading,
  Spinner,
  Alert,
  AlertIcon,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  IconButton,
  useToast,
} from '@chakra-ui/react';
import { ArrowBackIcon, DownloadIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { presmeetApi } from '../services/presmeetApi';
import {
  ReportType,
  ReportResponse,
  OrderStatus,
  PaymentStatus,
} from '../types/presmeet.types';
import { formatCurrency } from '../utils/priceCalculator';

// --- Column Definitions per Report Type ---

interface ColumnDef {
  key: string;
  label: string;
  /** Optional formatter for cell values */
  format?: (value: any, row: Record<string, any>) => React.ReactNode;
}

const REPORT_COLUMNS: Record<ReportType, ColumnDef[]> = {
  attendees: [
    { key: 'name', label: 'Name' },
    { key: 'role', label: 'Role' },
    { key: 'club', label: 'Club' },
    { key: 'status', label: 'Status', format: (v) => <StatusBadge status={v} /> },
  ],
  party: [
    { key: 'name', label: 'Name' },
    { key: 'person_type', label: 'Type' },
    { key: 'club', label: 'Club' },
    { key: 'status', label: 'Status', format: (v) => <StatusBadge status={v} /> },
  ],
  tshirts: [
    { key: 'person_name', label: 'Person' },
    { key: 'variant', label: 'Variant' },
    { key: 'club', label: 'Club' },
    { key: 'status', label: 'Status', format: (v) => <StatusBadge status={v} /> },
  ],
  pickups: [
    { key: 'flight', label: 'Flight' },
    { key: 'date', label: 'Date' },
    { key: 'time', label: 'Time' },
    { key: 'persons', label: 'Persons' },
    { key: 'club', label: 'Club' },
    { key: 'status', label: 'Status', format: (v) => <StatusBadge status={v} /> },
  ],
  dropoffs: [
    { key: 'flight', label: 'Flight' },
    { key: 'date', label: 'Date' },
    { key: 'time', label: 'Time' },
    { key: 'persons', label: 'Persons' },
    { key: 'club', label: 'Club' },
    { key: 'status', label: 'Status', format: (v) => <StatusBadge status={v} /> },
  ],
  financial: [
    { key: 'club', label: 'Club' },
    {
      key: 'total_charged',
      label: 'Total Charged',
      format: (v) => formatCurrency(v ?? 0),
    },
    {
      key: 'total_paid',
      label: 'Total Paid',
      format: (v) => formatCurrency(v ?? 0),
    },
    {
      key: 'total_outstanding',
      label: 'Outstanding',
      format: (v) => (
        <Text color={(v ?? 0) > 0 ? 'red.600' : 'green.600'} fontWeight="medium">
          {formatCurrency(v ?? 0)}
        </Text>
      ),
    },
  ],
  overview: [
    { key: 'metric', label: 'Metric' },
    { key: 'value', label: 'Value' },
  ],
};

const REPORT_LABELS: Record<ReportType, string> = {
  attendees: 'Attendees',
  party: 'Party Guests',
  tshirts: 'T-Shirts',
  pickups: 'Pickups',
  dropoffs: 'Dropoffs',
  financial: 'Financial',
  overview: 'Overview',
};

/** Translation key map for report labels */
const REPORT_LABEL_KEYS: Record<ReportType, string> = {
  attendees: 'reports.type_attendees',
  party: 'reports.type_party',
  tshirts: 'reports.type_tshirts',
  pickups: 'reports.type_pickups',
  dropoffs: 'reports.type_dropoffs',
  financial: 'reports.type_financial',
  overview: 'reports.type_overview',
};

const ORDER_STATUS_OPTIONS: Array<{ value: string; labelKey: string }> = [
  { value: 'all', labelKey: 'reports.filter_all_statuses' },
  { value: 'draft', labelKey: 'reports.filter_draft' },
  { value: 'submitted', labelKey: 'reports.filter_submitted' },
  { value: 'locked', labelKey: 'reports.filter_locked' },
];

const PAYMENT_STATUS_OPTIONS: Array<{ value: string; labelKey: string }> = [
  { value: 'all', labelKey: 'reports.filter_all_payment' },
  { value: 'unpaid', labelKey: 'reports.filter_unpaid' },
  { value: 'partial', labelKey: 'reports.filter_partial' },
  { value: 'paid', labelKey: 'reports.filter_paid' },
];

// --- Status Badge Component ---

function StatusBadge({ status }: { status: string }) {
  const colorScheme =
    status === 'locked'
      ? 'green'
      : status === 'submitted'
      ? 'blue'
      : status === 'draft'
      ? 'orange'
      : 'gray';
  return <Badge colorScheme={colorScheme}>{status}</Badge>;
}

// --- Financial Totals Row ---

function FinancialTotalsRow({ data, totalLabel }: { data: Record<string, any>[]; totalLabel: string }) {
  const totals = useMemo(() => {
    return data.reduce(
      (acc, row) => ({
        total_charged: acc.total_charged + (row.total_charged ?? 0),
        total_paid: acc.total_paid + (row.total_paid ?? 0),
        total_outstanding: acc.total_outstanding + (row.total_outstanding ?? 0),
      }),
      { total_charged: 0, total_paid: 0, total_outstanding: 0 }
    );
  }, [data]);

  return (
    <Tr fontWeight="bold" bg="gray.50">
      <Td>{totalLabel}</Td>
      <Td>{formatCurrency(totals.total_charged)}</Td>
      <Td>{formatCurrency(totals.total_paid)}</Td>
      <Td>
        <Text color={totals.total_outstanding > 0 ? 'red.600' : 'green.600'}>
          {formatCurrency(totals.total_outstanding)}
        </Text>
      </Td>
    </Tr>
  );
}

// --- Main Component ---

/**
 * Admin Report View — displays report data in tables with filters
 * and CSV download. Reads type and event_id from URL query params (hash routing).
 *
 * Requirements: 10, 13.3
 */
const ReportView: React.FC = () => {
  const { t } = useTranslation('presmeet');

  // Parse query params from hash routing
  const params = useMemo(() => {
    const hash = window.location.hash;
    const queryString = hash.includes('?') ? hash.split('?')[1] : '';
    return new URLSearchParams(queryString);
  }, []);

  const eventId = params.get('event_id') || '';
  const initialType = (params.get('type') as ReportType) || 'attendees';
  const initialStatus = params.get('status') || 'all';
  const initialPaymentStatus = params.get('payment_status') || 'all';

  const [reportType, setReportType] = useState<ReportType>(initialType);
  const [statusFilter, setStatusFilter] = useState<string>(initialStatus);
  const [paymentStatusFilter, setPaymentStatusFilter] = useState<string>(initialPaymentStatus);
  const [reportData, setReportData] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  // Fetch report data
  const loadReport = useCallback(async () => {
    if (!eventId) {
      setError(t('reports.no_event_selected'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await presmeetApi.getReport({
        type: reportType,
        event_id: eventId,
        status: statusFilter === 'all' ? undefined : (statusFilter as OrderStatus),
        payment_status:
          paymentStatusFilter === 'all' ? undefined : (paymentStatusFilter as PaymentStatus),
      });
      setReportData(result);
    } catch (err) {
      setError(t('reports.error'));
      setReportData(null);
    } finally {
      setLoading(false);
    }
  }, [eventId, reportType, statusFilter, paymentStatusFilter]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  // CSV download handler
  const handleCsvDownload = async () => {
    if (!eventId) return;

    setDownloading(true);
    try {
      const result = await presmeetApi.getReport({
        type: reportType,
        event_id: eventId,
        status: statusFilter === 'all' ? undefined : (statusFilter as OrderStatus),
        payment_status:
          paymentStatusFilter === 'all' ? undefined : (paymentStatusFilter as PaymentStatus),
        format: 'csv',
      });

      // The CSV response data may come as a string or need conversion
      const csvContent =
        typeof result === 'string'
          ? result
          : convertToCsv(result.data || [], REPORT_COLUMNS[reportType]);

      triggerCsvDownload(csvContent, `${reportType}-report.csv`);

      toast({
        title: t('reports.csv_downloaded'),
        status: 'success',
        duration: 2000,
      });
    } catch (err) {
      toast({
        title: t('reports.csv_download_failed'),
        description: t('reports.csv_download_failed_desc'),
        status: 'error',
        duration: 4000,
      });
    } finally {
      setDownloading(false);
    }
  };

  // Navigate back to Event Dashboard
  const handleBack = () => {
    window.location.hash = '#/admin/presmeet';
  };

  const columns = REPORT_COLUMNS[reportType];
  const data = reportData?.data || [];

  return (
    <VStack spacing={5} align="stretch">
      {/* Header with back button */}
      <HStack spacing={3}>
        <IconButton
          icon={<ArrowBackIcon />}
          aria-label={t('reports.back_to_dashboard')}
          variant="ghost"
          onClick={handleBack}
        />
        <Heading size="lg">{t('reports.title', { type: t(REPORT_LABEL_KEYS[reportType]) })}</Heading>
      </HStack>

      {/* Report metadata */}
      {reportData?.metadata && (
        <Box bg="gray.50" px={4} py={2} borderRadius="md">
          <Text fontSize="sm" color="gray.600">
            {reportData.metadata.event_name} — {reportData.metadata.event_location}
            {reportData.metadata.event_dates &&
              ` (${reportData.metadata.event_dates.start} – ${reportData.metadata.event_dates.end})`}
          </Text>
        </Box>
      )}

      {/* Filters and Actions */}
      <Box bg="white" p={4} borderRadius="md" borderWidth={1}>
        <HStack spacing={4} flexWrap="wrap">
          <Box>
            <Text fontSize="sm" fontWeight="medium" mb={1}>
              {t('reports.report_type')}
            </Text>
            <Select
              value={reportType}
              onChange={(e) => setReportType(e.target.value as ReportType)}
              size="sm"
              maxW="180px"
            >
              {Object.entries(REPORT_LABEL_KEYS).map(([value, labelKey]) => (
                <option key={value} value={value}>
                  {t(labelKey)}
                </option>
              ))}
            </Select>
          </Box>

          <Box>
            <Text fontSize="sm" fontWeight="medium" mb={1}>
              {t('reports.order_status')}
            </Text>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              size="sm"
              maxW="180px"
            >
              {ORDER_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {t(opt.labelKey)}
                </option>
              ))}
            </Select>
          </Box>

          <Box>
            <Text fontSize="sm" fontWeight="medium" mb={1}>
              {t('reports.payment_status')}
            </Text>
            <Select
              value={paymentStatusFilter}
              onChange={(e) => setPaymentStatusFilter(e.target.value)}
              size="sm"
              maxW="180px"
            >
              {PAYMENT_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {t(opt.labelKey)}
                </option>
              ))}
            </Select>
          </Box>

          <Box alignSelf="flex-end">
            <Button
              leftIcon={<DownloadIcon />}
              size="sm"
              colorScheme="green"
              onClick={handleCsvDownload}
              isLoading={downloading}
              loadingText={t('reports.downloading')}
              isDisabled={!eventId || loading}
            >
              {t('reports.download_csv')}
            </Button>
          </Box>
        </HStack>
      </Box>

      {/* Error state */}
      {error && (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          {error}
        </Alert>
      )}

      {/* Loading state */}
      {loading && (
        <Box textAlign="center" py={8}>
          <Spinner size="lg" />
          <Text mt={2}>{t('reports.loading')}</Text>
        </Box>
      )}

      {/* Report Table */}
      {!loading && !error && reportData && (
        <Box bg="white" p={4} borderRadius="md" borderWidth={1} overflowX="auto">
          {data.length === 0 ? (
            <Text color="gray.500" textAlign="center" py={6}>
              {t('reports.no_data')}
            </Text>
          ) : (
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  {columns.map((col) => (
                    <Th key={col.key}>{col.label}</Th>
                  ))}
                </Tr>
              </Thead>
              <Tbody>
                {data.map((row, idx) => (
                  <Tr key={idx}>
                    {columns.map((col) => (
                      <Td key={col.key}>
                        {col.format ? col.format(row[col.key], row) : (row[col.key] ?? '—')}
                      </Td>
                    ))}
                  </Tr>
                ))}
                {reportType === 'financial' && data.length > 0 && (
                  <FinancialTotalsRow data={data} totalLabel={t('reports.total')} />
                )}
              </Tbody>
            </Table>
          )}

          <Text fontSize="xs" color="gray.500" mt={3}>
            {data.length} {data.length === 1 ? 'row' : 'rows'}
            {reportData.metadata?.generated_at &&
              ` — Generated at ${new Date(reportData.metadata.generated_at).toLocaleString('nl-NL')}`}
          </Text>
        </Box>
      )}
    </VStack>
  );
};

// --- Utility Functions ---

/**
 * Convert report data array to CSV string.
 */
function convertToCsv(data: Record<string, any>[], columns: ColumnDef[]): string {
  if (data.length === 0) return '';

  const header = columns.map((col) => escapeCsvField(col.label)).join(',');
  const rows = data.map((row) =>
    columns.map((col) => escapeCsvField(String(row[col.key] ?? ''))).join(',')
  );

  return [header, ...rows].join('\n');
}

/**
 * Escape a single CSV field value (wrap in quotes if it contains commas, quotes, or newlines).
 */
function escapeCsvField(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

/**
 * Trigger a browser download of CSV content.
 */
function triggerCsvDownload(csvContent: string, filename: string): void {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default ReportView;

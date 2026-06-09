/**
 * useAdminReports Hook
 *
 * Loads the latest report snapshot from the API, provides
 * refresh (regenerate) and export (CSV/JSON download) functions.
 * Supports report type, event filter, order status, and payment status filters.
 *
 * Validates: Requirements 11.1, 11.2, 11.3, 11.13
 */

import { useState, useEffect, useCallback } from 'react';
import {
  getReport,
  generateReport,
  exportReport,
  GenerateReportParams,
} from '../services/adminApi';
import { ReportResponse, ReportType, OrderStatusFilter, PaymentStatusFilter } from '../types/admin.types';

export interface UseAdminReportsReturn {
  report: ReportResponse | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  exportData: (format: 'csv' | 'json') => Promise<void>;
}

/**
 * Hook for managing report data in the admin Reports tab.
 * Loads snapshot, triggers regeneration, and handles export downloads.
 */
export function useAdminReports(
  eventFilter: string,
  reportType: ReportType,
  orderStatus: OrderStatusFilter,
  paymentStatus: PaymentStatusFilter
): UseAdminReportsReturn {
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const buildParams = useCallback((): GenerateReportParams => {
    const params: GenerateReportParams = {
      report_type: reportType,
    };
    if (eventFilter && eventFilter !== '') {
      params.event_id = eventFilter;
    }
    if (orderStatus !== 'all') {
      params.order_status = orderStatus;
    }
    if (paymentStatus !== 'all') {
      params.payment_status = paymentStatus;
    }
    return params;
  }, [eventFilter, reportType, orderStatus, paymentStatus]);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = buildParams();
      const data = await getReport(params);
      setReport(data);
    } catch (err: any) {
      if (err?.response?.status === 404) {
        // No report generated yet
        setReport(null);
      } else {
        setError(err?.response?.data?.message || err?.message || 'Fout bij laden rapport');
      }
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const params = buildParams();
      await generateReport(params);
      await loadReport();
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || 'Fout bij vernieuwen rapport');
    } finally {
      setRefreshing(false);
    }
  }, [buildParams, loadReport]);

  const exportData = useCallback(async (format: 'csv' | 'json') => {
    try {
      const params = buildParams();
      const blob = await exportReport(format, params);
      // Trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const extension = format === 'csv' ? 'csv' : 'json';
      const filterLabel = eventFilter || 'alle';
      link.download = `rapport-${reportType}-${filterLabel}-${new Date().toISOString().split('T')[0]}.${extension}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || 'Fout bij exporteren rapport');
    }
  }, [buildParams, eventFilter, reportType]);

  return {
    report,
    loading,
    refreshing,
    error,
    refresh,
    exportData,
  };
}

export default useAdminReports;

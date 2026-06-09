/**
 * useAdminReports Hook
 *
 * Loads the latest report snapshot from S3 via the API, provides
 * refresh (regenerate) and export (CSV/JSON download) functions.
 *
 * Validates: Requirements 6.1, 6.2, 6.3
 */

import { useState, useEffect, useCallback } from 'react';
import {
  getReport,
  generateReport,
  exportReport,
} from '../services/adminApi';
import { ReportResponse } from '../types/admin.types';

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
export function useAdminReports(channel: string): UseAdminReportsReturn {
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getReport(channel || undefined);
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
  }, [channel]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      await generateReport(channel || undefined);
      await loadReport();
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || 'Fout bij vernieuwen rapport');
    } finally {
      setRefreshing(false);
    }
  }, [channel, loadReport]);

  const exportData = useCallback(async (format: 'csv' | 'json') => {
    try {
      const blob = await exportReport(channel || undefined, format);
      // Trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const extension = format === 'csv' ? 'csv' : 'json';
      const channelLabel = channel || 'all';
      link.download = `rapport-${channelLabel}-${new Date().toISOString().split('T')[0]}.${extension}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || 'Fout bij exporteren rapport');
    }
  }, [channel]);

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

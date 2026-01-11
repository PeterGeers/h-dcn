/**
 * Hook for Member Export Service
 * 
 * Simple hook to export member data as JSON.
 * Much simpler than parquet files!
 */

import { useState, useCallback } from 'react';
import { Member } from '../types/index';
import { MemberExportService, MemberExportResponse, MemberExportError } from '../services/MemberExportService';

interface UseMemberExportResult {
  members: Member[] | null;
  loading: boolean;
  error: string | null;
  metadata: MemberExportResponse['metadata'] | null;
  exportMembers: () => Promise<void>;
  hasPermission: boolean | null;
  checkPermission: () => Promise<void>;
}

export const useMemberExport = (): UseMemberExportResult => {
  const [members, setMembers] = useState<Member[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<MemberExportResponse['metadata'] | null>(null);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);

  const exportMembers = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      console.log('[useMemberExport] Starting member export');
      
      const result = await MemberExportService.exportMembers();
      
      if (result.success) {
        setMembers(result.data);
        setMetadata(result.metadata);
        console.log(`[useMemberExport] Successfully loaded ${result.data.length} members`);
      } else {
        setError((result as MemberExportError).error);
        setMembers(null);
        setMetadata(null);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to export members';
      setError(errorMessage);
      setMembers(null);
      setMetadata(null);
      console.error('[useMemberExport] Export failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const checkPermission = useCallback(async () => {
    try {
      const result = await MemberExportService.checkExportPermission();
      setHasPermission(result.hasPermission);
      if (!result.hasPermission && result.error) {
        setError(result.error);
      }
    } catch (err) {
      setHasPermission(false);
      setError(err instanceof Error ? err.message : 'Permission check failed');
    }
  }, []);

  return {
    members,
    loading,
    error,
    metadata,
    exportMembers,
    hasPermission,
    checkPermission
  };
};

export default useMemberExport;
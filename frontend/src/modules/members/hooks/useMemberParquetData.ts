/**
 * React Hook for Member Reporting Parquet Data
 * 
 * This hook loads parquet data for the member administration module.
 * Used for:
 * - Member table display and selection
 * - Reporting and analytics functions
 * - Read-only operations with calculated fields
 * 
 * NOT used for:
 * - CRUD operations (use regular API calls)
 * - Real-time data updates
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { memberParquetDataService, ParquetLoadResult, ParquetFileStatus } from '../services/parquetDataService';
import { Member } from '../../../types/index';
import { HDCNGroup } from '../../../config/memberFields';

// ============================================================================
// HOOK TYPES
// ============================================================================

export interface UseMemberParquetDataOptions {
  /** Whether to automatically load data when hook mounts (true for member tables and reporting) */
  autoLoad?: boolean;
  
  /** Whether to apply calculated fields */
  applyCalculatedFields?: boolean;
  
  /** Whether to apply regional filtering */
  applyRegionalFiltering?: boolean;
  
  /** Whether to enable caching */
  enableCaching?: boolean;
}

export interface UseMemberParquetDataReturn {
  // Data state
  data: Member[] | null;
  loading: boolean;
  error: string | null;
  
  // Metadata
  recordCount: number;
  fromCache: boolean;
  lastLoadTime: number | null;
  
  // File status
  fileStatus: ParquetFileStatus | null;
  isDataAvailable: boolean;
  
  // Actions
  loadData: () => Promise<void>;
  refreshData: () => Promise<void>;
  clearCache: () => void;
  checkAvailability: () => Promise<void>;
}

// ============================================================================
// MAIN HOOK
// ============================================================================

export function useMemberParquetData(
  userRole: HDCNGroup,
  userRegion?: string,
  options: UseMemberParquetDataOptions = {}
): UseMemberParquetDataReturn {
  const {
    autoLoad = true, // Auto-load for member tables and reporting
    applyCalculatedFields = true,
    applyRegionalFiltering = true,
    enableCaching = true
  } = options;

  // State management
  const [data, setData] = useState<Member[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [recordCount, setRecordCount] = useState<number>(0);
  const [fromCache, setFromCache] = useState<boolean>(false);
  const [lastLoadTime, setLastLoadTime] = useState<number | null>(null);
  const [fileStatus, setFileStatus] = useState<ParquetFileStatus | null>(null);

  // Refs for cleanup
  const mountedRef = useRef<boolean>(true);

  // ============================================================================
  // UTILITY FUNCTIONS
  // ============================================================================

  const log = useCallback((message: string, data?: any) => {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[useMemberParquetData] ${message}`, data || '');
    }
  }, []);

  // ============================================================================
  // DATA LOADING FUNCTIONS
  // ============================================================================

  const loadData = useCallback(async (): Promise<void> => {
    if (loading) {
      log('Already loading data, skipping request');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      log(`Loading parquet data for role: ${userRole}, region: ${userRegion}`);
      
      const result: ParquetLoadResult = await memberParquetDataService.loadLatestMemberData(
        userRole,
        userRegion,
        {
          applyCalculatedFields,
          applyRegionalFiltering,
          enableCaching
        }
      );
      
      if (!mountedRef.current) {
        log('Component unmounted during load, ignoring result');
        return;
      }
      
      if (result.success && result.data) {
        setData(result.data);
        setRecordCount(result.metadata?.recordCount || 0);
        setFromCache(result.metadata?.fromCache || false);
        setLastLoadTime(Date.now());
        
        log(`Successfully loaded ${result.data.length} members`, {
          fromCache: result.metadata?.fromCache,
          loadTime: result.metadata?.loadTime
        });
      } else {
        throw new Error(result.error || 'Failed to load parquet data');
      }
      
    } catch (err) {
      if (!mountedRef.current) return;
      
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      log('Error loading parquet data:', err);
      
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [userRole, userRegion, applyCalculatedFields, applyRegionalFiltering, enableCaching, loading, log]);

  const refreshData = useCallback(async (): Promise<void> => {
    log('Refreshing parquet data');
    memberParquetDataService.clearCache(); // Clear cache to force fresh load
    await loadData();
  }, [loadData, log]);

  const clearCache = useCallback((): void => {
    log('Clearing parquet data cache');
    memberParquetDataService.clearCache();
    setFromCache(false);
  }, [log]);

  const checkAvailability = useCallback(async (): Promise<void> => {
    try {
      log('Checking parquet data availability');
      const status = await memberParquetDataService.checkDataAvailability();
      
      if (mountedRef.current) {
        setFileStatus(status);
        log('File status updated', status);
      }
      
    } catch (err) {
      if (mountedRef.current) {
        log('Error checking availability:', err);
      }
    }
  }, [log]);

  // ============================================================================
  // EFFECTS
  // ============================================================================

  // Check availability on mount
  useEffect(() => {
    checkAvailability();
  }, []); // Only run once on mount

  // Auto-load data for member tables and reporting
  useEffect(() => {
    if (autoLoad) {
      log('Auto-loading parquet data for member tables and reporting');
      loadData();
    }
  }, []); // Only run once on mount

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      log('useMemberParquetData cleanup completed');
    };
  }, [log]);

  // ============================================================================
  // COMPUTED VALUES
  // ============================================================================

  const isDataAvailable = fileStatus?.available || false;

  // ============================================================================
  // RETURN HOOK INTERFACE
  // ============================================================================

  return {
    // Data state
    data,
    loading,
    error,
    
    // Metadata
    recordCount,
    fromCache,
    lastLoadTime,
    
    // File status
    fileStatus,
    isDataAvailable,
    
    // Actions
    loadData,
    refreshData,
    clearCache,
    checkAvailability
  };
}

export default useMemberParquetData;
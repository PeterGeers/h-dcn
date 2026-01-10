/**
 * React Hook for Parquet Data Management
 * 
 * This hook provides a React-friendly interface to the ParquetDataService,
 * managing loading states, error handling, and automatic data refresh.
 * 
 * Features:
 * - Automatic data loading with loading states
 * - Error handling and retry logic
 * - Data caching and refresh capabilities
 * - Regional filtering based on user permissions
 * - TypeScript support with proper typing
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { parquetDataService } from '../services/ParquetDataService';
import { Member } from '../types/index';
import {
  ParquetLoadOptions,
  ParquetLoadResult,
  ParquetFileStatus,
  ParquetError,
  ParquetProcessingStats
} from '../types/ParquetTypes';

// ============================================================================
// HOOK TYPES
// ============================================================================

export interface UseParquetDataOptions extends Partial<ParquetLoadOptions> {
  /** Whether to automatically load data on mount */
  autoLoad?: boolean;
  
  /** Filename to load (defaults to 'latest') */
  filename?: string;
  
  /** Interval for automatic refresh in milliseconds */
  refreshInterval?: number;
  
  /** Whether to retry on error */
  retryOnError?: boolean;
  
  /** Maximum number of retry attempts */
  maxRetries?: number;
  
  /** Delay between retry attempts in milliseconds */
  retryDelay?: number;
}

export interface UseParquetDataReturn {
  // Data state
  data: Member[] | null;
  loading: boolean;
  error: string | null;
  
  // Metadata
  metadata: ParquetLoadResult['metadata'] | null;
  fileStatus: ParquetFileStatus | null;
  
  // Actions
  loadData: (filename?: string) => Promise<void>;
  refreshData: () => Promise<void>;
  clearCache: () => void;
  retry: () => Promise<void>;
  
  // Status
  isDataAvailable: boolean;
  lastLoadTime: number | null;
  retryCount: number;
  hasPermission: boolean;
}

// ============================================================================
// MAIN HOOK
// ============================================================================

export function useParquetData(options: UseParquetDataOptions = {}): UseParquetDataReturn {
  const {
    autoLoad = true,
    filename = 'latest',
    refreshInterval,
    retryOnError = true,
    maxRetries = 3,
    retryDelay = 1000,
    ...loadOptions
  } = options;

  // State management
  const [data, setData] = useState<Member[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<ParquetLoadResult['metadata'] | null>(null);
  const [fileStatus, setFileStatus] = useState<ParquetFileStatus | null>(null);
  const [lastLoadTime, setLastLoadTime] = useState<number | null>(null);
  const [retryCount, setRetryCount] = useState<number>(0);
  const [hasPermission, setHasPermission] = useState<boolean>(false);

  // Refs for cleanup and state management
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef<boolean>(true);

  // ============================================================================
  // UTILITY FUNCTIONS
  // ============================================================================

  const log = useCallback((message: string, data?: any) => {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[useParquetData] ${message}`, data || '');
    }
  }, []);

  const logError = useCallback((message: string, error?: any) => {
    console.error(`[useParquetData] ${message}`, error || '');
  }, []);

  // ============================================================================
  // DATA LOADING FUNCTIONS
  // ============================================================================

  const loadData = useCallback(async (targetFilename?: string): Promise<void> => {
    const fileToLoad = targetFilename || filename;
    
    if (loading) {
      log(`Already loading data, skipping request for ${fileToLoad}`);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      log(`Loading parquet data from ${fileToLoad}`, loadOptions);
      
      const result = await parquetDataService.loadMemberData(fileToLoad, loadOptions);
      
      if (!mountedRef.current) {
        log('Component unmounted during load, ignoring result');
        return;
      }
      
      if (result.success && result.data) {
        setData(result.data);
        setMetadata(result.metadata || null);
        setLastLoadTime(Date.now());
        setRetryCount(0);
        setHasPermission(true);
        
        log(`Successfully loaded ${result.data.length} members`, result.metadata);
      } else {
        // Check if error is permission-related
        if (result.error && (result.error.includes('permission') || result.error.includes('Authentication required'))) {
          setHasPermission(false);
        }
        throw new Error(result.error || 'Failed to load parquet data');
      }
      
    } catch (err) {
      if (!mountedRef.current) return;
      
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      
      // Check if error is permission-related
      if (errorMessage.includes('permission') || errorMessage.includes('Authentication required')) {
        setHasPermission(false);
      }
      
      logError('Error loading parquet data', err);
      
      // Retry logic
      if (retryOnError && retryCount < maxRetries) {
        const nextRetryCount = retryCount + 1;
        setRetryCount(nextRetryCount);
        
        log(`Scheduling retry ${nextRetryCount}/${maxRetries} in ${retryDelay}ms`);
        
        retryTimeoutRef.current = setTimeout(() => {
          if (mountedRef.current) {
            loadData(targetFilename);
          }
        }, retryDelay);
      }
      
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [filename, loadOptions, loading, retryOnError, retryCount, maxRetries, retryDelay, log, logError]);

  const refreshData = useCallback(async (): Promise<void> => {
    log('Refreshing parquet data');
    setRetryCount(0); // Reset retry count on manual refresh
    await loadData();
  }, [loadData, log]);

  const retry = useCallback(async (): Promise<void> => {
    log('Manual retry requested');
    setRetryCount(0); // Reset retry count on manual retry
    setError(null);
    await loadData();
  }, [loadData, log]);

  // ============================================================================
  // FILE STATUS MANAGEMENT
  // ============================================================================

  const loadFileStatus = useCallback(async (): Promise<void> => {
    try {
      log('Loading file status');
      const status = await parquetDataService.getParquetStatus();
      
      if (mountedRef.current) {
        setFileStatus(status);
        
        // Check if error is permission-related
        if (status.error && (status.error.includes('permission') || status.error.includes('Authentication required'))) {
          setHasPermission(false);
        } else {
          setHasPermission(true);
        }
        
        log('File status loaded', status);
      }
      
    } catch (err) {
      if (mountedRef.current) {
        logError('Error loading file status', err);
      }
    }
  }, [log, logError]);

  // ============================================================================
  // CACHE MANAGEMENT
  // ============================================================================

  const clearCache = useCallback((): void => {
    log('Clearing parquet data cache');
    parquetDataService.clearCache();
  }, [log]);

  // ============================================================================
  // EFFECTS
  // ============================================================================

  // Initial load and file status check
  useEffect(() => {
    if (autoLoad) {
      log('Auto-loading parquet data on mount');
      loadData();
    }
    
    // Always load file status
    loadFileStatus();
  }, []); // Empty dependency array for mount-only effect

  // Refresh interval setup
  useEffect(() => {
    if (refreshInterval && refreshInterval > 0) {
      log(`Setting up refresh interval: ${refreshInterval}ms`);
      
      refreshIntervalRef.current = setInterval(() => {
        if (!loading) {
          log('Auto-refreshing data');
          refreshData();
        }
      }, refreshInterval);
      
      return () => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current);
          refreshIntervalRef.current = null;
        }
      };
    }
  }, [refreshInterval, loading, refreshData, log]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
      
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      
      log('useParquetData cleanup completed');
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
    metadata,
    fileStatus,
    
    // Actions
    loadData,
    refreshData,
    clearCache,
    retry,
    
    // Status
    isDataAvailable,
    lastLoadTime,
    retryCount,
    hasPermission
  };
}

// ============================================================================
// SPECIALIZED HOOKS
// ============================================================================

/**
 * Hook for loading latest parquet data with default settings
 */
export function useLatestParquetData(options: Omit<UseParquetDataOptions, 'filename'> = {}): UseParquetDataReturn {
  return useParquetData({
    ...options,
    filename: 'latest'
  });
}

/**
 * Hook for loading parquet data with calculated fields disabled (raw data only)
 */
export function useRawParquetData(options: UseParquetDataOptions = {}): UseParquetDataReturn {
  return useParquetData({
    ...options,
    applyCalculatedFields: false
  });
}

/**
 * Hook for loading parquet data with regional filtering disabled (all data)
 */
export function useUnfilteredParquetData(options: UseParquetDataOptions = {}): UseParquetDataReturn {
  return useParquetData({
    ...options,
    applyRegionalFiltering: false
  });
}

/**
 * Hook for loading parquet data with caching disabled (always fresh)
 */
export function useFreshParquetData(options: UseParquetDataOptions = {}): UseParquetDataReturn {
  return useParquetData({
    ...options,
    enableCaching: false
  });
}

// ============================================================================
// UTILITY HOOKS
// ============================================================================

/**
 * Hook for checking parquet data availability without loading data
 */
export function useParquetDataStatus(): {
  fileStatus: ParquetFileStatus | null;
  isAvailable: boolean;
  loading: boolean;
  error: string | null;
  hasPermission: boolean;
  refresh: () => Promise<void>;
} {
  const [fileStatus, setFileStatus] = useState<ParquetFileStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasPermission, setHasPermission] = useState<boolean>(false);
  const mountedRef = useRef<boolean>(true);

  const refresh = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      
      const status = await parquetDataService.getParquetStatus();
      
      if (mountedRef.current) {
        setFileStatus(status);
        
        // Check if error is permission-related
        if (status.error && status.error.includes('permission')) {
          setHasPermission(false);
          setError(status.error);
        } else if (status.error && status.error.includes('Authentication required')) {
          setHasPermission(false);
          setError(status.error);
        } else {
          setHasPermission(true);
          if (status.error) {
            setError(status.error);
          }
        }
      }
      
    } catch (err) {
      if (mountedRef.current) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMessage);
        setHasPermission(false);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    refresh();
    
    return () => {
      mountedRef.current = false;
    };
  }, [refresh]);

  return {
    fileStatus,
    isAvailable: fileStatus?.available || false,
    loading,
    error,
    hasPermission,
    refresh
  };
}

export default useParquetData;
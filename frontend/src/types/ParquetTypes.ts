/**
 * Types for Parquet Data Service
 * 
 * This module defines types for the parquet data loading and processing system.
 * It extends the existing Member type and adds parquet-specific interfaces.
 */

import { Member } from './index';

// ============================================================================
// PARQUET FILE METADATA
// ============================================================================

export interface ParquetFileInfo {
  filename: string;
  size: number;
  lastModified: string;
  recordCount?: number;
  contentType: string;
  metadata?: Record<string, any>;
}

export interface ParquetFileStatus {
  available: boolean;
  files: ParquetFileInfo[];
  latestFile?: ParquetFileInfo;
  lastGenerated?: string;
  error?: string;
}

// ============================================================================
// PARQUET DATA LOADING
// ============================================================================

export interface ParquetLoadOptions {
  /** Whether to apply calculated fields after loading raw data */
  applyCalculatedFields?: boolean;
  
  /** Whether to apply regional filtering based on user permissions */
  applyRegionalFiltering?: boolean;
  
  /** Whether to cache the loaded data in memory */
  enableCaching?: boolean;
  
  /** Maximum age of cached data in milliseconds */
  cacheMaxAge?: number;
  
  /** Whether to use web workers for processing */
  useWebWorkers?: boolean;
}

export interface ParquetLoadResult {
  success: boolean;
  data?: Member[];
  error?: string;
  metadata?: {
    recordCount: number;
    loadTime: number;
    fromCache: boolean;
    calculatedFieldsApplied: boolean;
    regionalFilteringApplied: boolean;
  };
}

// ============================================================================
// PARQUET DOWNLOAD RESPONSE
// ============================================================================

export interface ParquetDownloadResponse {
  success: boolean;
  download_method: 'direct_content' | 'presigned_url';
  data?: {
    content?: string; // Base64 encoded content for direct downloads
    download_url?: string; // Pre-signed URL for large files
    expires_in?: number;
    filename: string;
    size: number;
  };
  metadata?: ParquetFileInfo;
  message?: string;
  error?: string;
}

// ============================================================================
// CACHING
// ============================================================================

export interface ParquetCacheEntry {
  data: Member[];
  timestamp: number;
  filename: string;
  recordCount: number;
  calculatedFieldsApplied: boolean;
}

export interface ParquetCacheOptions {
  maxAge: number; // Maximum age in milliseconds
  maxEntries: number; // Maximum number of cached entries
  enableIndexedDB: boolean; // Whether to persist cache to IndexedDB
}

// ============================================================================
// REGIONAL FILTERING
// ============================================================================

export interface RegionalFilterOptions {
  userRoles: string[];
  userEmail: string;
  allowedRegions?: string[];
}

// ============================================================================
// ERROR TYPES
// ============================================================================

export enum ParquetErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  PERMISSION_ERROR = 'PERMISSION_ERROR',
  FILE_NOT_FOUND = 'FILE_NOT_FOUND',
  PARSE_ERROR = 'PARSE_ERROR',
  CACHE_ERROR = 'CACHE_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

export interface ParquetError {
  type: ParquetErrorType;
  message: string;
  details?: any;
  timestamp: number;
}

// ============================================================================
// SERVICE CONFIGURATION
// ============================================================================

export interface ParquetServiceConfig {
  /** Base URL for the API */
  apiBaseUrl: string;
  
  /** Default load options */
  defaultLoadOptions: ParquetLoadOptions;
  
  /** Cache configuration */
  cacheOptions: ParquetCacheOptions;
  
  /** Whether to enable debug logging */
  enableDebugLogging: boolean;
  
  /** Timeout for API requests in milliseconds */
  requestTimeout: number;
}

// ============================================================================
// PROCESSING STATISTICS
// ============================================================================

export interface ParquetProcessingStats {
  totalRecords: number;
  processedRecords: number;
  calculatedFieldsComputed: number;
  regionallyFiltered: number;
  processingTime: number;
  memoryUsage?: number;
}

// ============================================================================
// WEB WORKER MESSAGES
// ============================================================================

export interface ParquetWorkerMessage {
  type: 'PROCESS_DATA' | 'APPLY_CALCULATED_FIELDS' | 'APPLY_REGIONAL_FILTER';
  payload: {
    data: any[];
    options?: any;
  };
  requestId: string;
}

export interface ParquetWorkerResponse {
  type: 'SUCCESS' | 'ERROR' | 'PROGRESS';
  payload: {
    data?: Member[];
    error?: string;
    progress?: number;
    stats?: ParquetProcessingStats;
  };
  requestId: string;
}
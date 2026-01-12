/**
 * Parquet Data Service for H-DCN Member Reporting
 * 
 * This service handles loading raw parquet data from the backend API,
 * applying calculated fields using the existing calculatedFields.ts system,
 * and providing caching and regional filtering capabilities.
 * 
 * Key Features:
 * - Load raw parquet data from backend API
 * - Apply calculated fields using existing frontend logic
 * - Regional filtering based on user permissions
 * - Memory caching with optional IndexedDB persistence
 * - Web worker support for background processing
 * - Comprehensive error handling and logging
 */

import { ApiService } from './apiService';
import { computeCalculatedFieldsForArray } from '../utils/calculatedFields';
import { Member } from '../types/index';
import { webWorkerManager, WebWorkerManager } from './WebWorkerManager';
import {
  ParquetFileInfo,
  ParquetFileStatus,
  ParquetLoadOptions,
  ParquetLoadResult,
  ParquetDownloadResponse,
  ParquetCacheEntry,
  ParquetCacheOptions,
  ParquetError,
  ParquetErrorType,
  ParquetServiceConfig,
  ParquetProcessingStats,
  RegionalFilterOptions
} from '../types/ParquetTypes';

// ============================================================================
// SERVICE CONFIGURATION
// ============================================================================

const DEFAULT_CONFIG: ParquetServiceConfig = {
  apiBaseUrl: process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod',
  defaultLoadOptions: {
    applyCalculatedFields: true,
    applyRegionalFiltering: true,
    enableCaching: true,
    cacheMaxAge: 5 * 60 * 1000, // 5 minutes
    useWebWorkers: true // Re-enabled Web Workers after resolving CloudFront MIME type issue
  },
  cacheOptions: {
    maxAge: 5 * 60 * 1000, // 5 minutes
    maxEntries: 5,
    enableIndexedDB: false // Disabled by default for simplicity
  },
  enableDebugLogging: process.env.NODE_ENV === 'development',
  requestTimeout: 30000 // 30 seconds
};

// ============================================================================
// PARQUET DATA SERVICE CLASS
// ============================================================================

export class ParquetDataService {
  private static instance: ParquetDataService;
  private config: ParquetServiceConfig;
  private cache: Map<string, ParquetCacheEntry> = new Map();
  private loadingPromises: Map<string, Promise<ParquetLoadResult>> = new Map();

  private constructor(config: Partial<ParquetServiceConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.log('ParquetDataService initialized', this.config);
  }

  /**
   * Get singleton instance of ParquetDataService
   */
  public static getInstance(config?: Partial<ParquetServiceConfig>): ParquetDataService {
    if (!ParquetDataService.instance) {
      ParquetDataService.instance = new ParquetDataService(config);
    }
    return ParquetDataService.instance;
  }

  // ============================================================================
  // LOGGING UTILITIES
  // ============================================================================

  private log(message: string, data?: any): void {
    if (this.config.enableDebugLogging) {
      console.log(`[ParquetDataService] ${message}`, data || '');
    }
  }

  private logError(message: string, error?: any): void {
    console.error(`[ParquetDataService] ${message}`, error || '');
  }

  // ============================================================================
  // ERROR HANDLING
  // ============================================================================

  private createError(type: ParquetErrorType, message: string, details?: any): ParquetError {
    return {
      type,
      message,
      details,
      timestamp: Date.now()
    };
  }

  private handleApiError(error: any): ParquetError {
    if (error.message?.includes('401') || error.message?.includes('Unauthorized')) {
      return this.createError(ParquetErrorType.AUTHENTICATION_ERROR, 'Authentication failed', error);
    }
    if (error.message?.includes('403') || error.message?.includes('Forbidden')) {
      return this.createError(ParquetErrorType.PERMISSION_ERROR, 'Permission denied', error);
    }
    if (error.message?.includes('404') || error.message?.includes('Not Found')) {
      return this.createError(ParquetErrorType.FILE_NOT_FOUND, 'Parquet file not found', error);
    }
    if (error.message?.includes('Network') || error.message?.includes('fetch')) {
      return this.createError(ParquetErrorType.NETWORK_ERROR, 'Network error', error);
    }
    return this.createError(ParquetErrorType.UNKNOWN_ERROR, error.message || 'Unknown error', error);
  }

  // ============================================================================
  // CACHE MANAGEMENT
  // ============================================================================

  private getCacheKey(filename: string, options: ParquetLoadOptions): string {
    const baseOptions = {
      applyCalculatedFields: options.applyCalculatedFields,
      applyRegionalFiltering: options.applyRegionalFiltering
    };
    
    // Include user roles in cache key when regional filtering is enabled
    // This ensures different users with different regional access get separate cache entries
    if (options.applyRegionalFiltering) {
      const userRoles = ApiService.getCurrentUserRoles();
      const userEmail = ApiService.getCurrentUserEmail();
      
      if (userRoles && userEmail) {
        // Sort roles to ensure consistent cache keys
        const sortedRoles = [...userRoles].sort();
        (baseOptions as any).userRoles = sortedRoles;
        (baseOptions as any).userEmail = userEmail;
      }
    }
    
    const optionsHash = JSON.stringify(baseOptions);
    return `${filename}:${btoa(optionsHash)}`;
  }

  private getCachedData(cacheKey: string): ParquetCacheEntry | null {
    const entry = this.cache.get(cacheKey);
    if (!entry) return null;

    const age = Date.now() - entry.timestamp;
    if (age > this.config.cacheOptions.maxAge) {
      this.cache.delete(cacheKey);
      this.log(`Cache entry expired for ${cacheKey}`);
      return null;
    }

    this.log(`Cache hit for ${cacheKey}`);
    return entry;
  }

  private setCachedData(cacheKey: string, data: Member[], filename: string, calculatedFieldsApplied: boolean): void {
    // Implement LRU cache by removing oldest entries if we exceed maxEntries
    if (this.cache.size >= this.config.cacheOptions.maxEntries) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
      this.log(`Removed oldest cache entry: ${oldestKey}`);
    }

    const entry: ParquetCacheEntry = {
      data: [...data], // Create a copy to avoid mutations
      timestamp: Date.now(),
      filename,
      recordCount: data.length,
      calculatedFieldsApplied
    };

    this.cache.set(cacheKey, entry);
    this.log(`Cached data for ${cacheKey} (${data.length} records)`);
  }

  public clearCache(): void {
    this.cache.clear();
    this.log('Cache cleared');
  }

  // ============================================================================
  // PERMISSION CHECKING
  // ============================================================================

  /**
   * Check if current user has permission to access parquet data
   */
  private checkParquetPermissions(): { hasPermission: boolean; error?: string } {
    try {
      // Get current user roles from ApiService
      const userRoles = ApiService.getCurrentUserRoles();
      const userEmail = ApiService.getCurrentUserEmail();
      
      if (!userRoles || !userEmail) {
        return {
          hasPermission: false,
          error: 'Authentication required to access parquet data'
        };
      }
      
      // New role structure permissions - NO BACKWARD COMPATIBILITY
      const requiredPermissions = [
        'Members_CRUD',
        'Members_Read', 
        'Members_Export',
        'System_User_Management'
      ];
      
      // Check if user has any of the required permissions
      const hasRequiredPermission = userRoles.some(role => requiredPermissions.includes(role));
      
      if (!hasRequiredPermission) {
        const permissionRoles = userRoles.filter(r => !r.startsWith('Regio_'));
        const regionRoles = userRoles.filter(r => r.startsWith('Regio_'));
        this.log(`Permission denied for user ${userEmail} with permission roles: ${permissionRoles.join(', ')}, region roles: ${regionRoles.join(', ')}`);
        return {
          hasPermission: false,
          error: 'Insufficient permissions. Parquet data access requires Members_CRUD, Members_Read, Members_Export, or System_User_Management role with appropriate regional assignment.'
        };
      }
      
      const permissionRoles = userRoles.filter(r => !r.startsWith('Regio_'));
      const regionRoles = userRoles.filter(r => r.startsWith('Regio_'));
      this.log(`Permission granted for user ${userEmail} with permission roles: ${permissionRoles.join(', ')}, region roles: ${regionRoles.join(', ')}`);
      return { hasPermission: true };
      
    } catch (error) {
      this.logError('Error checking parquet permissions', error);
      return {
        hasPermission: false,
        error: 'Failed to verify permissions'
      };
    }
  }

  // ============================================================================
  // PARQUET FILE STATUS AND METADATA
  // ============================================================================

  /**
   * Get status of available parquet files
   */
  public async getParquetStatus(): Promise<ParquetFileStatus> {
    try {
      this.log('Fetching parquet file status');
      
      // Check user permissions first
      const permissionCheck = this.checkParquetPermissions();
      if (!permissionCheck.hasPermission) {
        return {
          available: false,
          files: [],
          error: permissionCheck.error
        };
      }
      
      // Note: This endpoint doesn't exist yet according to the plan
      // For now, we'll try to get the latest file to check availability
      const response = await ApiService.get<ParquetDownloadResponse>('/analytics/download-parquet/latest');
      
      if (!response.success) {
        return {
          available: false,
          files: [],
          error: response.error || 'Failed to get parquet status'
        };
      }

      // Extract file info from the download response
      const fileInfo: ParquetFileInfo = {
        filename: response.data?.data?.filename || 'latest.parquet',
        size: response.data?.data?.size || 0,
        lastModified: new Date().toISOString(), // We don't have this info yet
        contentType: 'application/octet-stream',
        metadata: response.data?.metadata || {}
      };

      return {
        available: true,
        files: [fileInfo],
        latestFile: fileInfo,
        lastGenerated: fileInfo.lastModified
      };

    } catch (error) {
      this.logError('Error getting parquet status', error);
      return {
        available: false,
        files: [],
        error: 'Failed to check parquet file status'
      };
    }
  }

  // ============================================================================
  // RAW PARQUET DATA LOADING
  // ============================================================================

  /**
   * Download raw parquet file from backend API
   * 
   * ARCHITECTURE NOTE: Any user with member access permissions can download the full parquet file.
   * Regional filtering is handled in the frontend after download, not during download.
   * This allows for better performance and more flexible filtering options.
   */
  private async downloadParquetFile(filename: string = 'latest'): Promise<{ success: boolean; data?: ArrayBuffer; error?: string }> {
    try {
      this.log(`Downloading parquet file: ${filename}`);
      
      // Make direct fetch request to handle both JSON and binary responses
      const token = localStorage.getItem('authToken');
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/analytics/download-parquet/${filename}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type') || '';
      
      if (contentType.includes('application/json')) {
        // Large file - JSON response with pre-signed URL or direct content
        const jsonData = await response.json();
        
        if (jsonData.download_method === 'presigned_url' && jsonData.data?.download_url) {
          // Handle pre-signed URL download for large files
          this.log('Using pre-signed URL for large file download');
          const fileResponse = await fetch(jsonData.data.download_url);
          if (!fileResponse.ok) {
            throw new Error(`Failed to download from pre-signed URL: ${fileResponse.statusText}`);
          }
          const arrayBuffer = await fileResponse.arrayBuffer();
          return { success: true, data: arrayBuffer };
          
        } else if (jsonData.download_method === 'direct_content' && jsonData.data?.content) {
          // Handle direct content download for small files (base64 encoded in JSON)
          this.log('Using direct content download from JSON');
          const binaryString = atob(jsonData.data.content);
          const arrayBuffer = new ArrayBuffer(binaryString.length);
          const uint8Array = new Uint8Array(arrayBuffer);
          for (let i = 0; i < binaryString.length; i++) {
            uint8Array[i] = binaryString.charCodeAt(i);
          }
          return { success: true, data: arrayBuffer };
        } else {
          throw new Error('Invalid JSON response format');
        }
      } else {
        // Small file - direct binary response (base64 encoded)
        this.log('Handling direct binary response');
        const text = await response.text();
        
        // The response body is base64 encoded binary data
        const binaryString = atob(text);
        const arrayBuffer = new ArrayBuffer(binaryString.length);
        const uint8Array = new Uint8Array(arrayBuffer);
        for (let i = 0; i < binaryString.length; i++) {
          uint8Array[i] = binaryString.charCodeAt(i);
        }
        return { success: true, data: arrayBuffer };
      }

    } catch (error) {
      this.logError('Download error', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Download failed' 
      };
    }
  }

  /**
   * Parse parquet data from ArrayBuffer to raw member objects
   */
  private async parseParquetData(arrayBuffer: ArrayBuffer): Promise<{ success: boolean; data?: any[]; error?: string }> {
    try {
      this.log('Parsing parquet data');
      
      // First try to parse as JSON (fallback for development/testing)
      try {
        // Check if we have TextDecoder available (browser environment)
        const decoder = typeof TextDecoder !== 'undefined' ? new TextDecoder() : null;
        if (decoder) {
          const text = decoder.decode(arrayBuffer);
          const jsonData = JSON.parse(text);
          if (Array.isArray(jsonData)) {
            this.log(`Successfully parsed ${jsonData.length} records as JSON`);
            return { success: true, data: jsonData };
          }
        }
      } catch (jsonError) {
        // Continue to parquet parsing if JSON fails
        this.log('JSON parsing failed, trying parquet parsing');
      }
      
      // Try Apache Arrow for parquet parsing (browser environment only)
      if (typeof window !== 'undefined') {
        try {
          const { tableFromIPC } = await import('apache-arrow');
          
          // Convert ArrayBuffer to Uint8Array for Apache Arrow
          const uint8Array = new Uint8Array(arrayBuffer);
          
          // Parse the parquet file
          const table = tableFromIPC(uint8Array);
          
          // Convert to JavaScript objects
          const records: any[] = [];
          for (let i = 0; i < table.numRows; i++) {
            const record: any = {};
            for (const field of table.schema.fields) {
              const column = table.getChild(field.name);
              if (column) {
                record[field.name] = column.get(i);
              }
            }
            records.push(record);
          }
          
          this.log(`Successfully parsed ${records.length} records from parquet file`);
          return { success: true, data: records };
          
        } catch (arrowError) {
          this.logError('Apache Arrow parsing failed', arrowError);
        }
      }
      
      // Final fallback: try manual text decoding for test environments
      try {
        // Manual text decoding for Node.js/test environments
        const text = String.fromCharCode.apply(null, Array.from(new Uint8Array(arrayBuffer)));
        const jsonData = JSON.parse(text);
        if (Array.isArray(jsonData)) {
          this.log(`Fallback: parsed ${jsonData.length} records using manual decoding`);
          return { success: true, data: jsonData };
        }
      } catch (fallbackError) {
        this.log('Manual decoding fallback also failed');
      }
      
      return { 
        success: false, 
        error: 'Failed to parse parquet data - no suitable parser available' 
      };
      
    } catch (error) {
      this.logError('Error parsing parquet data', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Failed to parse parquet data' 
      };
    }
  }

  // ============================================================================
  // DATA PROCESSING
  // ============================================================================

  /**
   * Apply calculated fields to raw member data
   */
  private async applyCalculatedFields(rawMembers: any[], useWebWorkers: boolean = false): Promise<Member[]> {
    try {
      this.log(`Applying calculated fields to ${rawMembers.length} members (Web Workers: ${useWebWorkers})`);
      
      // Use Web Workers for large datasets or when explicitly requested
      if (useWebWorkers && webWorkerManager.isAvailable() && rawMembers.length > 50) {
        this.log('Using Web Workers for calculated fields processing');
        
        const result = await webWorkerManager.applyCalculatedFields(rawMembers);
        this.log(`Web Worker processing completed: ${result.data.length} members processed`);
        return result.data;
      }
      
      // Fallback to synchronous processing
      this.log('Using synchronous processing for calculated fields');
      const processedMembers = computeCalculatedFieldsForArray(rawMembers as Member[]);
      
      this.log(`Successfully applied calculated fields to ${processedMembers.length} members`);
      return processedMembers as Member[];
      
    } catch (error) {
      this.logError('Error applying calculated fields', error);
      // Return raw data if calculated fields fail
      return rawMembers as Member[];
    }
  }

  /**
   * Apply regional filtering based on user permissions using new role structure
   * 
   * ARCHITECTURE NOTE: This function is called AFTER downloading the full parquet file.
   * The backend provides the complete dataset to any user with member access permissions.
   * Regional filtering is applied here in the frontend based on the user's regional roles.
   * This approach provides better performance and more flexible filtering capabilities.
   */
  private async applyRegionalFiltering(members: Member[], options?: RegionalFilterOptions, useWebWorkers: boolean = false): Promise<Member[]> {
    if (!options) {
      // Get current user roles from ApiService
      const userRoles = ApiService.getCurrentUserRoles();
      const userEmail = ApiService.getCurrentUserEmail();
      
      if (!userRoles || !userEmail) {
        this.log('No user authentication info available, skipping regional filtering');
        return members;
      }
      
      options = { userRoles, userEmail };
    }

    try {
      const permissionRoles = options.userRoles.filter(r => !r.startsWith('Regio_'));
      const regionRoles = options.userRoles.filter(r => r.startsWith('Regio_'));
      this.log(`Applying regional filtering for user with permission roles: ${permissionRoles.join(', ')}, region roles: ${regionRoles.join(', ')} (Web Workers: ${useWebWorkers})`);
      
      // Use Web Workers for large datasets or when explicitly requested
      if (useWebWorkers && webWorkerManager.isAvailable() && members.length > 100) {
        this.log('Using Web Workers for regional filtering');
        
        const result = await webWorkerManager.applyRegionalFilter(members, options);
        this.log(`Web Worker filtering completed: ${members.length} -> ${result.data.length} members`);
        return result.data;
      }
      
      // Fallback to synchronous processing
      this.log('Using synchronous processing for regional filtering');
      
      // NEW ROLE STRUCTURE: Check for full access roles - NO BACKWARD COMPATIBILITY
      const systemAdminRoles = ['System_CRUD', 'System_User_Management'];
      
      const hasSystemAccess = options.userRoles.some(role => systemAdminRoles.includes(role));
      
      // NEW ROLE STRUCTURE: Check for Regio_All access
      const hasRegioAll = options.userRoles.includes('Regio_All');
      
      if (hasSystemAccess || hasRegioAll) {
        this.log(`User has full access (${hasSystemAccess ? 'system-admin' : 'Regio_All'}), no regional filtering applied`);
        return members;
      }
      
      // NEW ROLE STRUCTURE: Extract regional roles (format: Regio_RegionName)
      const regionalRoles = options.userRoles.filter(role => role.startsWith('Regio_') && role !== 'Regio_All');
      
      let allowedRegions: string[] = [];
      
      // Process regional roles
      if (regionalRoles.length > 0) {
        allowedRegions = regionalRoles.map(role => role.replace('Regio_', ''));
        this.log(`Regional roles found: ${regionalRoles.join(', ')} -> allowed regions: ${allowedRegions.join(', ')}`);
      }
      
      if (allowedRegions.length === 0) {
        this.log('No regional roles found, checking if user has any member access permissions');
        
        // If user has member read permissions but no regional roles, they might be a national user
        const hasMemberAccess = options.userRoles.some(role => 
          role.includes('Members_Read') || role.includes('Members_CRUD')
        );
        
        if (hasMemberAccess) {
          this.log('User has member access but no regional restrictions, returning all members');
          return members;
        } else {
          this.log('User has no member access permissions, returning empty result');
          return [];
        }
      }
      
      this.log(`User allowed regions: ${allowedRegions.join(', ')}`);
      
      // Filter members by region
      const filteredMembers = members.filter(member => {
        const memberRegion = member.regio || member.region;
        
        if (!memberRegion) {
          // Members without region assignment - include them for full access users only
          this.log(`Member ${member.id || 'unknown'} has no region assigned`);
          return hasSystemAccess || hasRegioAll;
        }
        
        // Check if member's region is in allowed regions
        const isAllowed = allowedRegions.includes(memberRegion);
        
        if (!isAllowed) {
          this.log(`Member ${member.id || 'unknown'} from region '${memberRegion}' filtered out (not in allowed regions: ${allowedRegions.join(', ')})`);
        }
        
        return isAllowed;
      });
      
      this.log(`Regional filtering applied: ${members.length} -> ${filteredMembers.length} members`);
      
      // Security audit log for regional access
      if (filteredMembers.length < members.length) {
        const permissionRoles = options.userRoles.filter(r => !r.startsWith('Regio_'));
        const regionRoles = options.userRoles.filter(r => r.startsWith('Regio_'));
        this.log(`SECURITY_AUDIT: Regional filtering applied for user ${options.userEmail} with permission roles [${permissionRoles.join(', ')}] and region roles [${regionRoles.join(', ')}]. Filtered ${members.length - filteredMembers.length} members from unauthorized regions.`);
      }
      
      return filteredMembers;
      
    } catch (error) {
      this.logError('Error applying regional filtering', error);
      // SECURITY: In case of error, return empty array to prevent data leaks
      this.log('SECURITY_WARNING: Regional filtering failed, returning empty result to prevent data leaks');
      return [];
    }
  }

  // ============================================================================
  // MAIN LOADING METHODS
  // ============================================================================

  /**
   * Load latest member data from parquet files
   */
  public async loadLatestMemberData(options: Partial<ParquetLoadOptions> = {}): Promise<ParquetLoadResult> {
    return this.loadMemberData('latest', options);
  }

  /**
   * Load member data from a specific parquet file
   */
  public async loadMemberData(filename: string = 'latest', options: Partial<ParquetLoadOptions> = {}): Promise<ParquetLoadResult> {
    const startTime = Date.now();
    const loadOptions = { ...this.config.defaultLoadOptions, ...options };
    const cacheKey = this.getCacheKey(filename, loadOptions);
    
    try {
      this.log(`Loading member data from ${filename}`, loadOptions);
      
      // Check user permissions first
      const permissionCheck = this.checkParquetPermissions();
      if (!permissionCheck.hasPermission) {
        return {
          success: false,
          error: permissionCheck.error,
          metadata: {
            recordCount: 0,
            loadTime: Date.now() - startTime,
            fromCache: false,
            calculatedFieldsApplied: false,
            regionalFilteringApplied: false
          }
        };
      }
      
      // Check if we're already loading this data
      if (this.loadingPromises.has(cacheKey)) {
        this.log(`Already loading ${filename}, waiting for existing promise`);
        return await this.loadingPromises.get(cacheKey)!;
      }
      
      // Check cache first
      if (loadOptions.enableCaching) {
        const cachedData = this.getCachedData(cacheKey);
        if (cachedData) {
          const loadTime = Date.now() - startTime;
          return {
            success: true,
            data: [...cachedData.data], // Return a copy
            metadata: {
              recordCount: cachedData.recordCount,
              loadTime,
              fromCache: true,
              calculatedFieldsApplied: cachedData.calculatedFieldsApplied,
              regionalFilteringApplied: loadOptions.applyRegionalFiltering || false
            }
          };
        }
      }
      
      // Create loading promise
      const loadingPromise = this.performDataLoad(filename, loadOptions, startTime);
      this.loadingPromises.set(cacheKey, loadingPromise);
      
      try {
        const result = await loadingPromise;
        return result;
      } finally {
        // Clean up loading promise
        this.loadingPromises.delete(cacheKey);
      }
      
    } catch (error) {
      this.logError(`Error loading member data from ${filename}`, error);
      const parquetError = this.handleApiError(error);
      
      return {
        success: false,
        error: parquetError.message,
        metadata: {
          recordCount: 0,
          loadTime: Date.now() - startTime,
          fromCache: false,
          calculatedFieldsApplied: false,
          regionalFilteringApplied: false
        }
      };
    }
  }

  /**
   * Perform the actual data loading process
   */
  private async performDataLoad(filename: string, options: ParquetLoadOptions, startTime: number): Promise<ParquetLoadResult> {
    // Step 1: Download raw parquet data
    const downloadResult = await this.downloadParquetFile(filename);
    if (!downloadResult.success || !downloadResult.data) {
      throw new Error(downloadResult.error || 'Failed to download parquet file');
    }
    
    // Step 2: Parse parquet data
    const parseResult = await this.parseParquetData(downloadResult.data);
    if (!parseResult.success || !parseResult.data) {
      throw new Error(parseResult.error || 'Failed to parse parquet data');
    }
    
    let processedData = parseResult.data as Member[];
    
    // Step 3: Use Web Workers for combined processing if enabled and beneficial
    if (options.useWebWorkers && webWorkerManager.isAvailable() && processedData.length > 50) {
      this.log('Using Web Workers for combined data processing');
      
      try {
        // Get regional filter options
        let regionalFilterOptions;
        if (options.applyRegionalFiltering) {
          const userRoles = ApiService.getCurrentUserRoles();
          const userEmail = ApiService.getCurrentUserEmail();
          if (userRoles && userEmail) {
            regionalFilterOptions = { userRoles, userEmail };
          }
        }
        
        // Process data using Web Workers
        const result = await webWorkerManager.processData(processedData, {
          applyCalculatedFields: options.applyCalculatedFields,
          applyRegionalFiltering: options.applyRegionalFiltering,
          regionalFilterOptions
        });
        
        processedData = result.data;
        this.log(`Web Worker processing completed: ${processedData.length} members processed`);
        
      } catch (workerError) {
        this.logError('Web Worker processing failed, falling back to synchronous processing', workerError);
        
        // Fallback to synchronous processing
        if (options.applyCalculatedFields) {
          processedData = await this.applyCalculatedFields(processedData, false);
        }
        
        if (options.applyRegionalFiltering) {
          processedData = await this.applyRegionalFiltering(processedData, undefined, false);
        }
      }
    } else {
      // Use synchronous processing
      this.log('Using synchronous data processing');
      
      // Step 3: Apply calculated fields if requested
      if (options.applyCalculatedFields) {
        processedData = await this.applyCalculatedFields(processedData, false);
      }
      
      // Step 4: Apply regional filtering if requested
      if (options.applyRegionalFiltering) {
        processedData = await this.applyRegionalFiltering(processedData, undefined, false);
      }
    }
    
    // Step 5: Cache the result if caching is enabled
    if (options.enableCaching) {
      const cacheKey = this.getCacheKey(filename, options);
      this.setCachedData(cacheKey, processedData, filename, options.applyCalculatedFields || false);
    }
    
    const loadTime = Date.now() - startTime;
    this.log(`Successfully loaded ${processedData.length} members in ${loadTime}ms`);
    
    return {
      success: true,
      data: processedData,
      metadata: {
        recordCount: processedData.length,
        loadTime,
        fromCache: false,
        calculatedFieldsApplied: options.applyCalculatedFields || false,
        regionalFilteringApplied: options.applyRegionalFiltering || false
      }
    };
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /**
   * Get available parquet files
   */
  public async getAvailableFiles(): Promise<ParquetFileInfo[]> {
    const status = await this.getParquetStatus();
    return status.files;
  }

  /**
   * Check if parquet data is available
   */
  public async isDataAvailable(): Promise<boolean> {
    const status = await this.getParquetStatus();
    return status.available;
  }

  /**
   * Get cache statistics
   */
  public getCacheStats(): { entries: number; totalRecords: number; oldestEntry?: string } {
    let totalRecords = 0;
    let oldestTimestamp = Date.now();
    let oldestEntry: string | undefined;
    
    for (const [key, entry] of this.cache.entries()) {
      totalRecords += entry.recordCount;
      if (entry.timestamp < oldestTimestamp) {
        oldestTimestamp = entry.timestamp;
        oldestEntry = key;
      }
    }
    
    return {
      entries: this.cache.size,
      totalRecords,
      oldestEntry
    };
  }

  /**
   * Get Web Worker status
   */
  public getWebWorkerStatus(): {
    available: boolean;
    enabled: boolean;
    workerStats?: {
      totalWorkers: number;
      availableWorkers: number;
      activeTasks: number;
      queuedTasks: number;
    };
  } {
    const available = webWorkerManager.isAvailable();
    const enabled = this.config.defaultLoadOptions.useWebWorkers || false;
    
    return {
      available,
      enabled,
      workerStats: available ? webWorkerManager.getStatus() : undefined
    };
  }

  /**
   * Update service configuration
   */
  public updateConfig(newConfig: Partial<ParquetServiceConfig>): void {
    this.config = { ...this.config, ...newConfig };
    this.log('Configuration updated', this.config);
  }
}

// ============================================================================
// SINGLETON EXPORT
// ============================================================================

// Export singleton instance
export const parquetDataService = ParquetDataService.getInstance();

// Export class for testing and custom configurations
export default ParquetDataService;
/**
 * Parquet Data Service for Member Reporting Module
 * 
 * This service handles loading raw parquet data from the backend API specifically
 * for the member reporting functionality. It integrates with the existing member
 * module architecture and only loads data when the reporting tab is accessed.
 * 
 * Key Features:
 * - Module-scoped service (only for member reporting)
 * - Lazy loading (only when reporting tab is opened)
 * - Integration with existing calculated fields system
 * - Regional filtering based on user permissions
 * - Memory caching for session duration
 */

import { ApiService } from '../../../services/apiService';
import { computeCalculatedFieldsForArray } from '../../../utils/calculatedFields';
import { Member } from '../../../types/index';
import { HDCNGroup } from '../../../config/memberFields';

// ============================================================================
// TYPES
// ============================================================================

export interface ParquetLoadOptions {
  /** Whether to apply calculated fields after loading raw data */
  applyCalculatedFields?: boolean;
  
  /** Whether to apply regional filtering based on user permissions */
  applyRegionalFiltering?: boolean;
  
  /** Whether to cache the loaded data in memory */
  enableCaching?: boolean;
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

export interface ParquetFileStatus {
  available: boolean;
  latestFile?: {
    filename: string;
    size: number;
    lastModified: string;
  };
  error?: string;
}

// ============================================================================
// PARQUET DATA SERVICE
// ============================================================================

class MemberParquetDataService {
  private cache: Map<string, { data: Member[]; timestamp: number; calculatedFieldsApplied: boolean }> = new Map();
  private readonly CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
  private loadingPromise: Promise<ParquetLoadResult> | null = null;

  /**
   * Load latest member data from parquet files
   * Only called when user opens the reporting tab
   */
  public async loadLatestMemberData(
    userRole: HDCNGroup,
    userRegion?: string,
    options: ParquetLoadOptions = {}
  ): Promise<ParquetLoadResult> {
    const startTime = Date.now();
    const defaultOptions: ParquetLoadOptions = {
      applyCalculatedFields: true,
      applyRegionalFiltering: true,
      enableCaching: true,
      ...options
    };

    try {
      // Prevent multiple simultaneous loads
      if (this.loadingPromise) {
        console.log('[MemberParquetDataService] Already loading, waiting for existing promise');
        return await this.loadingPromise;
      }

      // Check cache first
      if (defaultOptions.enableCaching) {
        const cacheKey = this.getCacheKey(defaultOptions);
        const cachedData = this.getCachedData(cacheKey);
        if (cachedData) {
          const loadTime = Date.now() - startTime;
          return {
            success: true,
            data: [...cachedData.data], // Return a copy
            metadata: {
              recordCount: cachedData.data.length,
              loadTime,
              fromCache: true,
              calculatedFieldsApplied: cachedData.calculatedFieldsApplied,
              regionalFilteringApplied: defaultOptions.applyRegionalFiltering || false
            }
          };
        }
      }

      // Create loading promise
      this.loadingPromise = this.performDataLoad(userRole, userRegion, defaultOptions, startTime);
      
      try {
        const result = await this.loadingPromise;
        return result;
      } finally {
        this.loadingPromise = null;
      }

    } catch (error) {
      console.error('[MemberParquetDataService] Error loading member data:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to load parquet data',
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
   * Check if parquet data is available
   */
  public async checkDataAvailability(): Promise<ParquetFileStatus> {
    try {
      console.log('[MemberParquetDataService] Checking parquet data availability');
      
      const response = await ApiService.get('/analytics/download-parquet/latest');
      
      if (!response.success) {
        return {
          available: false,
          error: response.error || 'Failed to check parquet status'
        };
      }

      return {
        available: true,
        latestFile: {
          filename: response.data?.data?.filename || 'latest.parquet',
          size: response.data?.data?.size || 0,
          lastModified: new Date().toISOString()
        }
      };

    } catch (error) {
      console.error('[MemberParquetDataService] Error checking availability:', error);
      return {
        available: false,
        error: 'Failed to check parquet data availability'
      };
    }
  }

  /**
   * Clear cached data
   */
  public clearCache(): void {
    this.cache.clear();
    console.log('[MemberParquetDataService] Cache cleared');
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  private async performDataLoad(
    userRole: HDCNGroup,
    userRegion: string | undefined,
    options: ParquetLoadOptions,
    startTime: number
  ): Promise<ParquetLoadResult> {
    console.log('[MemberParquetDataService] Starting data load process');

    // Step 1: Download raw parquet data
    const downloadResult = await this.downloadParquetFile();
    if (!downloadResult.success || !downloadResult.data) {
      throw new Error(downloadResult.error || 'Failed to download parquet file');
    }

    // Step 2: Parse parquet data
    const parseResult = await this.parseParquetData(downloadResult.data);
    if (!parseResult.success || !parseResult.data) {
      throw new Error(parseResult.error || 'Failed to parse parquet data');
    }

    let processedData = parseResult.data as Member[];

    // Step 3: Apply calculated fields if requested
    if (options.applyCalculatedFields) {
      processedData = this.applyCalculatedFields(processedData);
    }

    // Step 4: Apply regional filtering if requested
    if (options.applyRegionalFiltering) {
      processedData = this.applyRegionalFiltering(processedData, userRole, userRegion);
    }

    // Step 5: Cache the result if caching is enabled
    if (options.enableCaching) {
      const cacheKey = this.getCacheKey(options);
      this.setCachedData(cacheKey, processedData, options.applyCalculatedFields || false);
    }

    const loadTime = Date.now() - startTime;
    console.log(`[MemberParquetDataService] Successfully loaded ${processedData.length} members in ${loadTime}ms`);

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

  private async downloadParquetFile(): Promise<{ success: boolean; data?: ArrayBuffer; error?: string }> {
    try {
      console.log('[MemberParquetDataService] Downloading parquet file');
      
      const response = await ApiService.getBinary('/analytics/download-parquet/latest');
      
      if (!response.success) {
        throw new Error(response.error || 'Download failed');
      }

      // The response.data should be the base64 encoded content
      const base64Content = response.data;
      if (typeof base64Content !== 'string') {
        throw new Error('Expected base64 string response');
      }

      // Decode base64 to binary
      const binaryString = atob(base64Content);
      const arrayBuffer = new ArrayBuffer(binaryString.length);
      const uint8Array = new Uint8Array(arrayBuffer);
      for (let i = 0; i < binaryString.length; i++) {
        uint8Array[i] = binaryString.charCodeAt(i);
      }
      
      return { success: true, data: arrayBuffer };

    } catch (error) {
      console.error('[MemberParquetDataService] Download error:', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Download failed' 
      };
    }
  }

  private async parseParquetData(arrayBuffer: ArrayBuffer): Promise<{ success: boolean; data?: any[]; error?: string }> {
    try {
      console.log('[MemberParquetDataService] Parsing parquet data');
      
      // First try to parse as JSON (fallback for development/testing)
      try {
        const decoder = typeof TextDecoder !== 'undefined' ? new TextDecoder() : null;
        if (decoder) {
          const text = decoder.decode(arrayBuffer);
          const jsonData = JSON.parse(text);
          if (Array.isArray(jsonData)) {
            console.log(`[MemberParquetDataService] Successfully parsed ${jsonData.length} records as JSON`);
            return { success: true, data: jsonData };
          }
        }
      } catch (jsonError) {
        console.log('[MemberParquetDataService] JSON parsing failed, trying parquet parsing');
      }
      
      // Try Apache Arrow for parquet parsing (browser environment only)
      if (typeof window !== 'undefined') {
        try {
          const { tableFromIPC } = await import('apache-arrow');
          
          const uint8Array = new Uint8Array(arrayBuffer);
          const table = tableFromIPC(uint8Array);
          
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
          
          console.log(`[MemberParquetDataService] Successfully parsed ${records.length} records from parquet file`);
          return { success: true, data: records };
          
        } catch (arrowError) {
          console.error('[MemberParquetDataService] Apache Arrow parsing failed:', arrowError);
        }
      }
      
      // Final fallback: try manual text decoding
      try {
        const text = String.fromCharCode.apply(null, Array.from(new Uint8Array(arrayBuffer)));
        const jsonData = JSON.parse(text);
        if (Array.isArray(jsonData)) {
          console.log(`[MemberParquetDataService] Fallback: parsed ${jsonData.length} records using manual decoding`);
          return { success: true, data: jsonData };
        }
      } catch (fallbackError) {
        console.log('[MemberParquetDataService] Manual decoding fallback also failed');
      }
      
      return { 
        success: false, 
        error: 'Failed to parse parquet data - no suitable parser available' 
      };
      
    } catch (error) {
      console.error('[MemberParquetDataService] Parse error:', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Failed to parse parquet data' 
      };
    }
  }

  private applyCalculatedFields(rawMembers: any[]): Member[] {
    try {
      console.log(`[MemberParquetDataService] Applying calculated fields to ${rawMembers.length} members`);
      
      const processedMembers = computeCalculatedFieldsForArray(rawMembers as Member[]);
      
      console.log(`[MemberParquetDataService] Successfully applied calculated fields to ${processedMembers.length} members`);
      return processedMembers as Member[];
      
    } catch (error) {
      console.error('[MemberParquetDataService] Error applying calculated fields:', error);
      return rawMembers as Member[];
    }
  }

  private applyRegionalFiltering(members: Member[], userRole: HDCNGroup, userRegion?: string): Member[] {
    try {
      console.log(`[MemberParquetDataService] Applying regional filtering for role: ${userRole}`);
      
      // Check if user has full access roles
      const fullAccessRoles: HDCNGroup[] = ['Members_CRUD', 'System_User_Management'];
      const hasFullAccess = fullAccessRoles.includes(userRole);
      
      if (hasFullAccess) {
        console.log('[MemberParquetDataService] User has full access, no regional filtering applied');
        return members;
      }
      
      // Apply regional filtering for regional users
      if (userRegion) {
        const filteredMembers = members.filter(member => {
          const memberRegion = member.regio || member.region;
          return memberRegion === userRegion;
        });
        
        console.log(`[MemberParquetDataService] Regional filtering applied: ${members.length} -> ${filteredMembers.length} members`);
        return filteredMembers;
      }
      
      console.log('[MemberParquetDataService] No regional filtering criteria, returning all members');
      return members;
      
    } catch (error) {
      console.error('[MemberParquetDataService] Error applying regional filtering:', error);
      return members;
    }
  }

  private getCacheKey(options: ParquetLoadOptions): string {
    const optionsHash = JSON.stringify({
      applyCalculatedFields: options.applyCalculatedFields,
      applyRegionalFiltering: options.applyRegionalFiltering
    });
    return `latest:${btoa(optionsHash)}`;
  }

  private getCachedData(cacheKey: string): { data: Member[]; calculatedFieldsApplied: boolean } | null {
    const entry = this.cache.get(cacheKey);
    if (!entry) return null;

    const age = Date.now() - entry.timestamp;
    if (age > this.CACHE_DURATION) {
      this.cache.delete(cacheKey);
      console.log(`[MemberParquetDataService] Cache entry expired for ${cacheKey}`);
      return null;
    }

    console.log(`[MemberParquetDataService] Cache hit for ${cacheKey}`);
    return { data: entry.data, calculatedFieldsApplied: entry.calculatedFieldsApplied };
  }

  private setCachedData(cacheKey: string, data: Member[], calculatedFieldsApplied: boolean): void {
    // Simple LRU: remove oldest entry if we have too many
    if (this.cache.size >= 3) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
      console.log(`[MemberParquetDataService] Removed oldest cache entry: ${oldestKey}`);
    }

    this.cache.set(cacheKey, {
      data: [...data], // Create a copy to avoid mutations
      timestamp: Date.now(),
      calculatedFieldsApplied
    });

    console.log(`[MemberParquetDataService] Cached data for ${cacheKey} (${data.length} records)`);
  }
}

// ============================================================================
// SINGLETON EXPORT
// ============================================================================

export const memberParquetDataService = new MemberParquetDataService();
export default memberParquetDataService;
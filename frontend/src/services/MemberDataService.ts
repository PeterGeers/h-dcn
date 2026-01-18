/**
 * Member Data Service for H-DCN Application
 * 
 * This service manages member data fetching with regional filtering and session storage caching.
 * It integrates with the backend regional filtering API and computes calculated fields.
 * 
 * Features:
 * - Fetches regionally-filtered member data from backend API
 * - Caches data in browser session storage for fast subsequent loads
 * - Computes calculated fields (korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar)
 * - Provides manual refresh capability for CRUD users
 * - Handles network and storage errors gracefully
 */

import { computeCalculatedFieldsForArray } from '../utils/calculatedFields';
import { getAuthHeaders } from '../utils/authHeaders';
import { Member } from '../types/index';

/**
 * Response structure from backend API
 */
export interface MemberDataResponse {
  success: boolean;
  data: Member[];
  error?: string;
  metadata: {
    total_count: number;
    region: string;
    timestamp: string;
  };
}

/**
 * Error response structure
 */
export interface MemberDataError {
  success: false;
  error: string;
  details?: string;
}

/**
 * Service class for managing member data
 */
export class MemberDataService {
  private static readonly STORAGE_KEY = 'hdcn_member_data';
  private static readonly STORAGE_TIMESTAMP_KEY = 'hdcn_member_data_timestamp';
  private static readonly API_ENDPOINT = '/api/members';
  private static readonly BASE_URL = process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

  /**
   * Fetch members from backend API
   * Automatically computes calculated fields and caches in session storage
   * 
   * @param forceRefresh - If true, bypasses cache and fetches fresh data
   * @returns Promise with array of members (with calculated fields)
   * @throws Error if fetch fails or authentication is invalid
   */
  static async fetchMembers(forceRefresh: boolean = false): Promise<Member[]> {
    // Check cache first (unless force refresh)
    if (!forceRefresh) {
      const cached = this.getCachedMembers();
      if (cached) {
        console.log('[MemberDataService] Using cached member data');
        return cached;
      }
    }

    console.log('[MemberDataService] Fetching fresh member data from backend');

    try {
      // Get authentication headers
      const authHeaders = await getAuthHeaders();

      // Construct full URL
      const url = `${this.BASE_URL}${this.API_ENDPOINT}`;

      // Make API request
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          ...authHeaders,
        },
      });

      // Handle HTTP errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        if (response.status === 401) {
          throw new Error('Authentication failed. Please log in again.');
        } else if (response.status === 403) {
          throw new Error('You do not have permission to view member data.');
        } else if (response.status === 500) {
          throw new Error('Server error. Please try again later.');
        } else {
          throw new Error(
            errorData.error || 
            errorData.message || 
            `Failed to fetch members: ${response.statusText}`
          );
        }
      }

      // Parse response
      const data: MemberDataResponse = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch member data');
      }

      // IMPORTANT: Compute calculated fields using existing calculatedFields.ts system
      // Backend sends only raw data, frontend computes: korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar
      const membersWithCalculatedFields = computeCalculatedFieldsForArray(data.data);

      console.log(`[MemberDataService] Fetched ${membersWithCalculatedFields.length} members from region: ${data.metadata.region}`);

      // Cache in session storage (with calculated fields)
      this.cacheMembers(membersWithCalculatedFields);

      return membersWithCalculatedFields;
    } catch (error) {
      console.error('[MemberDataService] Error fetching members:', error);
      
      // Re-throw with more context
      if (error instanceof Error) {
        throw error;
      } else {
        throw new Error('Failed to load member data. Please check your connection.');
      }
    }
  }

  /**
   * Get cached members from session storage
   * 
   * @returns Array of cached members or null if no cache exists
   */
  private static getCachedMembers(): Member[] | null {
    try {
      const cached = sessionStorage.getItem(this.STORAGE_KEY);
      if (!cached) {
        return null;
      }

      const members = JSON.parse(cached);
      
      // Validate cache structure
      if (!Array.isArray(members)) {
        console.warn('[MemberDataService] Invalid cache structure, clearing cache');
        this.clearCache();
        return null;
      }

      // Check cache timestamp (optional - for debugging)
      const timestamp = sessionStorage.getItem(this.STORAGE_TIMESTAMP_KEY);
      if (timestamp) {
        console.log(`[MemberDataService] Cache timestamp: ${timestamp}`);
      }

      return members;
    } catch (error) {
      console.error('[MemberDataService] Error reading from session storage:', error);
      // Clear corrupted cache
      this.clearCache();
      return null;
    }
  }

  /**
   * Cache members in session storage
   * 
   * @param members - Array of members to cache
   */
  private static cacheMembers(members: Member[]): void {
    try {
      sessionStorage.setItem(this.STORAGE_KEY, JSON.stringify(members));
      sessionStorage.setItem(this.STORAGE_TIMESTAMP_KEY, new Date().toISOString());
      console.log(`[MemberDataService] Cached ${members.length} members in session storage`);
    } catch (error) {
      console.error('[MemberDataService] Error writing to session storage:', error);
      
      // Check if quota exceeded
      if (error instanceof DOMException && error.name === 'QuotaExceededError') {
        console.warn('[MemberDataService] Session storage quota exceeded');
      }
      
      // Continue without caching - not critical for functionality
    }
  }

  /**
   * Clear cached members (for manual refresh)
   */
  static clearCache(): void {
    try {
      sessionStorage.removeItem(this.STORAGE_KEY);
      sessionStorage.removeItem(this.STORAGE_TIMESTAMP_KEY);
      console.log('[MemberDataService] Cache cleared');
    } catch (error) {
      console.error('[MemberDataService] Error clearing session storage:', error);
    }
  }

  /**
   * Refresh members (clear cache and fetch fresh)
   * 
   * @returns Promise with array of fresh members
   * @throws Error if fetch fails
   */
  static async refreshMembers(): Promise<Member[]> {
    console.log('[MemberDataService] Refreshing member data');
    this.clearCache();
    return this.fetchMembers(true);
  }

  /**
   * Check if session storage is available
   * 
   * @returns True if session storage is available and working
   */
  static isSessionStorageAvailable(): boolean {
    try {
      const testKey = '__hdcn_storage_test__';
      sessionStorage.setItem(testKey, 'test');
      sessionStorage.removeItem(testKey);
      return true;
    } catch (error) {
      console.warn('[MemberDataService] Session storage not available:', error);
      return false;
    }
  }

  /**
   * Get cache metadata (for debugging/monitoring)
   * 
   * @returns Cache metadata or null if no cache exists
   */
  static getCacheMetadata(): { timestamp: string; count: number } | null {
    try {
      const timestamp = sessionStorage.getItem(this.STORAGE_TIMESTAMP_KEY);
      const cached = sessionStorage.getItem(this.STORAGE_KEY);
      
      if (!timestamp || !cached) {
        return null;
      }

      const members = JSON.parse(cached);
      
      return {
        timestamp,
        count: Array.isArray(members) ? members.length : 0,
      };
    } catch (error) {
      console.error('[MemberDataService] Error getting cache metadata:', error);
      return null;
    }
  }
}

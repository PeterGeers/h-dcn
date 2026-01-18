/**
 * Tests for MemberDataService
 * 
 * Tests cover:
 * - Session storage caching
 * - Cache retrieval and usage
 * - Manual refresh functionality
 * - Error handling for network failures
 * - Error handling for storage failures
 * - Calculated fields integration
 */

import { MemberDataService } from '../MemberDataService';
import { computeCalculatedFieldsForArray } from '../../utils/calculatedFields';
import { getAuthHeaders } from '../../utils/authHeaders';
import { Member } from '../../types/index';

// Mock dependencies
jest.mock('../../utils/calculatedFields');
jest.mock('../../utils/authHeaders');

const mockComputeCalculatedFieldsForArray = computeCalculatedFieldsForArray as jest.MockedFunction<typeof computeCalculatedFieldsForArray>;
const mockGetAuthHeaders = getAuthHeaders as jest.MockedFunction<typeof getAuthHeaders>;

// Mock fetch globally
global.fetch = jest.fn();
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

describe('MemberDataService', () => {
  // Sample member data
  const mockRawMembers: Member[] = [
    {
      id: '1',
      name: 'Jan Jansen',
      email: 'jan@example.com',
      region: 'Utrecht',
      membershipType: 'individual',
      lidnummer: '12345',
      voornaam: 'Jan',
      achternaam: 'Jansen',
      status: 'Actief',
      regio: 'Utrecht',
      geboortedatum: '1978-09-26',
      tijdstempel: '2018-04-01',
    },
    {
      id: '2',
      name: 'Piet Pietersen',
      email: 'piet@example.com',
      region: 'Utrecht',
      membershipType: 'individual',
      lidnummer: '12346',
      voornaam: 'Piet',
      achternaam: 'Pietersen',
      status: 'Actief',
      regio: 'Utrecht',
      geboortedatum: '1985-03-15',
      tijdstempel: '2019-06-01',
    },
  ];

  const mockMembersWithCalculatedFields: Member[] = mockRawMembers.map(m => ({
    ...m,
    korte_naam: `${m.voornaam} ${m.achternaam}`,
    leeftijd: 45,
    verjaardag: 'september 26',
    jaren_lid: 6,
    aanmeldingsjaar: 2018,
  }));

  const mockApiResponse = {
    success: true,
    data: mockRawMembers,
    metadata: {
      total_count: 2,
      region: 'Utrecht',
      timestamp: '2026-01-17T10:30:00Z',
    },
  };

  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();
    
    // Clear session storage
    sessionStorage.clear();
    
    // Setup default mock implementations
    mockGetAuthHeaders.mockResolvedValue({
      'Content-Type': 'application/json',
      'Authorization': 'Bearer mock-token',
      'X-Enhanced-Groups': JSON.stringify(['Members_Read', 'Regio_Utrecht']),
    });

    mockComputeCalculatedFieldsForArray.mockReturnValue(mockMembersWithCalculatedFields);

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockApiResponse,
      status: 200,
      statusText: 'OK',
    } as Response);
  });

  describe('fetchMembers', () => {
    it('should fetch members from API and cache in session storage', async () => {
      const members = await MemberDataService.fetchMembers();

      // Verify API was called
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/members'),
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-token',
          }),
        })
      );

      // Verify calculated fields were computed
      expect(mockComputeCalculatedFieldsForArray).toHaveBeenCalledWith(mockRawMembers);

      // Verify data was cached
      const cached = sessionStorage.getItem('hdcn_member_data');
      expect(cached).toBeTruthy();
      expect(JSON.parse(cached!)).toEqual(mockMembersWithCalculatedFields);

      // Verify timestamp was cached
      const timestamp = sessionStorage.getItem('hdcn_member_data_timestamp');
      expect(timestamp).toBeTruthy();

      // Verify returned data
      expect(members).toEqual(mockMembersWithCalculatedFields);
    });

    it('should use cached data on second call', async () => {
      // First call - should fetch from API
      await MemberDataService.fetchMembers();
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Second call - should use cache
      const members = await MemberDataService.fetchMembers();
      expect(mockFetch).toHaveBeenCalledTimes(1); // Still 1, not 2
      expect(members).toEqual(mockMembersWithCalculatedFields);
    });

    it('should bypass cache when forceRefresh is true', async () => {
      // First call - should fetch from API
      await MemberDataService.fetchMembers();
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Second call with forceRefresh - should fetch again
      await MemberDataService.fetchMembers(true);
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it('should handle 401 authentication errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ error: 'Invalid token' }),
      } as Response);

      await expect(MemberDataService.fetchMembers()).rejects.toThrow(
        'Authentication failed. Please log in again.'
      );
    });

    it('should handle 403 permission errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ error: 'Insufficient permissions' }),
      } as Response);

      await expect(MemberDataService.fetchMembers()).rejects.toThrow(
        'You do not have permission to view member data.'
      );
    });

    it('should handle 500 server errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ error: 'Database error' }),
      } as Response);

      await expect(MemberDataService.fetchMembers()).rejects.toThrow(
        'Server error. Please try again later.'
      );
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(MemberDataService.fetchMembers()).rejects.toThrow('Network error');
    });

    it('should handle API response with success: false', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: false,
          error: 'Custom error message',
        }),
      } as Response);

      await expect(MemberDataService.fetchMembers()).rejects.toThrow('Custom error message');
    });
  });

  describe('refreshMembers', () => {
    it('should clear cache and fetch fresh data', async () => {
      // Set up cache
      sessionStorage.setItem('hdcn_member_data', JSON.stringify(mockMembersWithCalculatedFields));
      sessionStorage.setItem('hdcn_member_data_timestamp', '2026-01-17T09:00:00Z');

      // Refresh
      const members = await MemberDataService.refreshMembers();

      // Verify cache was cleared and API was called
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(members).toEqual(mockMembersWithCalculatedFields);
    });
  });

  describe('clearCache', () => {
    it('should remove cached data from session storage', () => {
      // Set up cache
      sessionStorage.setItem('hdcn_member_data', JSON.stringify(mockMembersWithCalculatedFields));
      sessionStorage.setItem('hdcn_member_data_timestamp', '2026-01-17T09:00:00Z');

      // Clear cache
      MemberDataService.clearCache();

      // Verify cache was cleared
      expect(sessionStorage.getItem('hdcn_member_data')).toBeNull();
      expect(sessionStorage.getItem('hdcn_member_data_timestamp')).toBeNull();
    });
  });

  describe('session storage error handling', () => {
    it('should handle session storage unavailable gracefully', async () => {
      // Mock sessionStorage to throw error
      const originalGetItem = sessionStorage.getItem;
      sessionStorage.getItem = jest.fn(() => {
        throw new Error('Storage unavailable');
      });

      // Should still fetch from API
      const members = await MemberDataService.fetchMembers();
      expect(members).toEqual(mockMembersWithCalculatedFields);

      // Restore
      sessionStorage.getItem = originalGetItem;
    });

    it('should handle corrupted cache data', async () => {
      // Set corrupted cache
      sessionStorage.setItem('hdcn_member_data', 'invalid-json');

      // Should fetch from API instead of using corrupted cache
      const members = await MemberDataService.fetchMembers();
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(members).toEqual(mockMembersWithCalculatedFields);
    });

    it('should handle cache with invalid structure', async () => {
      // Set cache with invalid structure (not an array)
      sessionStorage.setItem('hdcn_member_data', JSON.stringify({ invalid: 'structure' }));

      // Should fetch from API instead of using invalid cache
      const members = await MemberDataService.fetchMembers();
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(members).toEqual(mockMembersWithCalculatedFields);
    });

    it('should continue without caching if storage write fails', async () => {
      // Mock sessionStorage.setItem to throw error
      const originalSetItem = sessionStorage.setItem;
      sessionStorage.setItem = jest.fn(() => {
        throw new DOMException('QuotaExceededError');
      });

      // Should still return data even if caching fails
      const members = await MemberDataService.fetchMembers();
      expect(members).toEqual(mockMembersWithCalculatedFields);

      // Restore
      sessionStorage.setItem = originalSetItem;
    });
  });

  describe('isSessionStorageAvailable', () => {
    it('should return true when session storage is available', () => {
      expect(MemberDataService.isSessionStorageAvailable()).toBe(true);
    });

    it('should return false when session storage is not available', () => {
      // Save original sessionStorage
      const originalSessionStorage = global.sessionStorage;
      
      // Mock sessionStorage to throw errors
      Object.defineProperty(global, 'sessionStorage', {
        value: {
          setItem: jest.fn(() => {
            throw new Error('Storage unavailable');
          }),
          removeItem: jest.fn(() => {
            throw new Error('Storage unavailable');
          }),
          getItem: jest.fn(() => {
            throw new Error('Storage unavailable');
          }),
          clear: jest.fn(),
          length: 0,
          key: jest.fn(),
        },
        writable: true,
        configurable: true,
      });

      expect(MemberDataService.isSessionStorageAvailable()).toBe(false);

      // Restore original sessionStorage
      Object.defineProperty(global, 'sessionStorage', {
        value: originalSessionStorage,
        writable: true,
        configurable: true,
      });
    });
  });

  describe('getCacheMetadata', () => {
    it('should return cache metadata when cache exists', () => {
      // Set up cache
      const timestamp = '2026-01-17T10:30:00Z';
      sessionStorage.setItem('hdcn_member_data', JSON.stringify(mockMembersWithCalculatedFields));
      sessionStorage.setItem('hdcn_member_data_timestamp', timestamp);

      const metadata = MemberDataService.getCacheMetadata();

      expect(metadata).toEqual({
        timestamp,
        count: 2,
      });
    });

    it('should return null when cache does not exist', () => {
      const metadata = MemberDataService.getCacheMetadata();
      expect(metadata).toBeNull();
    });

    it('should handle corrupted cache gracefully', () => {
      sessionStorage.setItem('hdcn_member_data', 'invalid-json');
      sessionStorage.setItem('hdcn_member_data_timestamp', '2026-01-17T10:30:00Z');

      const metadata = MemberDataService.getCacheMetadata();
      expect(metadata).toBeNull();
    });
  });

  describe('calculated fields integration', () => {
    it('should compute calculated fields after fetching', async () => {
      await MemberDataService.fetchMembers();

      // Verify computeCalculatedFieldsForArray was called with raw data
      expect(mockComputeCalculatedFieldsForArray).toHaveBeenCalledWith(mockRawMembers);
      expect(mockComputeCalculatedFieldsForArray).toHaveBeenCalledTimes(1);
    });

    it('should cache members with calculated fields', async () => {
      await MemberDataService.fetchMembers();

      // Verify cached data includes calculated fields
      const cached = sessionStorage.getItem('hdcn_member_data');
      const cachedMembers = JSON.parse(cached!);

      expect(cachedMembers[0]).toHaveProperty('korte_naam');
      expect(cachedMembers[0]).toHaveProperty('leeftijd');
      expect(cachedMembers[0]).toHaveProperty('verjaardag');
      expect(cachedMembers[0]).toHaveProperty('jaren_lid');
      expect(cachedMembers[0]).toHaveProperty('aanmeldingsjaar');
    });
  });
});

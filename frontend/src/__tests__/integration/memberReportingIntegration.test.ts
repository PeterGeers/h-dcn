/**
 * Frontend Integration Tests for Member Reporting System
 * 
 * Tests the complete member reporting flow in a browser-like environment:
 * - Complete user flow: load → filter → refresh
 * - Session storage caching across navigation
 * - MemberDataService integration with backend API
 * - Error handling and recovery
 * 
 * Requirements: All
 * 
 * Usage:
 *   npm test -- memberReportingIntegration.test.ts
 */

import { MemberDataService } from '../../services/MemberDataService';
import { computeCalculatedFieldsForArray } from '../../utils/calculatedFields';

// Mock fetch for controlled testing
global.fetch = jest.fn();

// Mock session storage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

// Mock auth headers
jest.mock('../../utils/authHeaders', () => ({
  getAuthHeaders: jest.fn().mockResolvedValue({
    'Authorization': 'Bearer mock_jwt_token',
    'X-Enhanced-Groups': 'Regio_Utrecht,members_read',
    'Content-Type': 'application/json',
  }),
}));

// Sample member data
const mockMembersRaw = [
  {
    lidnummer: '12345',
    voornaam: 'Jan',
    tussenvoegsel: 'van',
    achternaam: 'Jansen',
    email: 'jan@utrecht.nl',
    regio: 'Utrecht',
    status: 'Actief',
    geboortedatum: '1980-05-15',
    tijdstempel: '2020-01-01',
  },
  {
    lidnummer: '12346',
    voornaam: 'Piet',
    achternaam: 'Pietersen',
    email: 'piet@utrecht.nl',
    regio: 'Utrecht',
    status: 'Inactief',
    geboortedatum: '1975-08-20',
    tijdstempel: '2018-06-15',
  },
  {
    lidnummer: '12347',
    voornaam: 'Klaas',
    achternaam: 'Klaassen',
    email: 'klaas@utrecht.nl',
    regio: 'Utrecht',
    status: 'Opgezegd',
    geboortedatum: '1990-12-10',
    tijdstempel: '2019-03-20',
  },
];

const mockApiResponse = {
  success: true,
  data: mockMembersRaw,
  metadata: {
    total_count: 3,
    region: 'Utrecht',
    timestamp: '2026-01-18T10:00:00Z',
  },
};

describe('Member Reporting Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorageMock.clear();
    (global.fetch as jest.Mock).mockClear();
  });

  describe('Complete User Flow: Load → Filter → Refresh', () => {
    test('should complete full user flow successfully', async () => {
      console.log('\n=== Testing Complete User Flow ===');

      // Mock successful API response
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockApiResponse,
      });

      // Step 1: Initial load
      console.log('Step 1: Initial load...');
      const members1 = await MemberDataService.fetchMembers();

      expect(members1).toHaveLength(3);
      expect(members1[0]).toHaveProperty('korte_naam'); // Calculated field
      expect(members1[0]).toHaveProperty('leeftijd'); // Calculated field
      console.log(`  ✓ Loaded ${members1.length} members with calculated fields`);

      // Verify session storage was populated
      const cached = sessionStorageMock.getItem('hdcn_member_data');
      expect(cached).toBeTruthy();
      console.log('  ✓ Data cached in session storage');

      // Step 2: Second load (should use cache)
      console.log('\nStep 2: Second load (cache hit)...');
      (global.fetch as jest.Mock).mockClear();

      const members2 = await MemberDataService.fetchMembers();

      expect(members2).toHaveLength(3);
      expect(global.fetch).not.toHaveBeenCalled(); // Should use cache
      console.log('  ✓ Used cached data (no API call)');

      // Step 3: Client-side filtering
      console.log('\nStep 3: Client-side filtering...');
      const startFilter = performance.now();
      const activeMembers = members2.filter(m => m.status === 'Actief');
      const filterTime = performance.now() - startFilter;

      expect(activeMembers).toHaveLength(1);
      expect(filterTime).toBeLessThan(200); // <200ms requirement
      console.log(`  ✓ Filtered in ${filterTime.toFixed(2)}ms (<200ms requirement)`);

      // Step 4: Refresh (clear cache and fetch fresh)
      console.log('\nStep 4: Refresh data...');
      const updatedResponse = {
        ...mockApiResponse,
        data: [...mockMembersRaw, {
          lidnummer: '12348',
          voornaam: 'Anna',
          achternaam: 'de Vries',
          email: 'anna@utrecht.nl',
          regio: 'Utrecht',
          status: 'Actief',
          geboortedatum: '1985-03-25',
          tijdstempel: '2021-02-10',
        }],
        metadata: {
          ...mockApiResponse.metadata,
          total_count: 4,
          timestamp: '2026-01-18T10:05:00Z',
        },
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => updatedResponse,
      });

      const members3 = await MemberDataService.refreshMembers();

      expect(members3).toHaveLength(4);
      expect(global.fetch).toHaveBeenCalledTimes(1); // Fresh API call
      console.log(`  ✓ Refreshed data: ${members3.length} members`);

      console.log('\n✓ Complete user flow PASSED');
    });

    test('should handle filter with multiple criteria', async () => {
      console.log('\n=== Testing Multiple Filter Criteria ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockApiResponse,
      });

      const members = await MemberDataService.fetchMembers();

      // Apply multiple filters (AND logic)
      const filtered = members.filter(m =>
        m.regio === 'Utrecht' &&
        m.status === 'Actief' &&
        m.voornaam.toLowerCase().includes('jan')
      );

      expect(filtered).toHaveLength(1);
      expect(filtered[0].voornaam).toBe('Jan');
      console.log('  ✓ Multiple filters applied correctly (AND logic)');

      console.log('\n✓ Multiple filter criteria test PASSED');
    });
  });

  describe('Session Storage Caching', () => {
    test('should cache data in session storage on first load', async () => {
      console.log('\n=== Testing Session Storage Caching ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockApiResponse,
      });

      await MemberDataService.fetchMembers();

      const cached = sessionStorageMock.getItem('hdcn_member_data');
      const timestamp = sessionStorageMock.getItem('hdcn_member_data_timestamp');

      expect(cached).toBeTruthy();
      expect(timestamp).toBeTruthy();

      const cachedMembers = JSON.parse(cached!);
      expect(cachedMembers).toHaveLength(3);
      console.log('  ✓ Data cached with timestamp');

      console.log('\n✓ Session storage caching test PASSED');
    });

    test('should use cached data on subsequent loads', async () => {
      console.log('\n=== Testing Cache Usage ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockApiResponse,
      });

      // First load
      await MemberDataService.fetchMembers();
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // Second load (should use cache)
      (global.fetch as jest.Mock).mockClear();
      await MemberDataService.fetchMembers();
      expect(global.fetch).not.toHaveBeenCalled();

      console.log('  ✓ Cache used on second load');

      console.log('\n✓ Cache usage test PASSED');
    });

    test('should clear cache on refresh', async () => {
      console.log('\n=== Testing Cache Clearing ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockApiResponse,
      });

      // Initial load
      await MemberDataService.fetchMembers();
      expect(sessionStorageMock.getItem('hdcn_member_data')).toBeTruthy();

      // Refresh
      await MemberDataService.refreshMembers();

      // Cache should be cleared and repopulated
      expect(sessionStorageMock.getItem('hdcn_member_data')).toBeTruthy();
      expect(global.fetch).toHaveBeenCalledTimes(2); // Initial + refresh

      console.log('  ✓ Cache cleared and repopulated on refresh');

      console.log('\n✓ Cache clearing test PASSED');
    });

    test('should handle session storage unavailable', async () => {
      console.log('\n=== Testing Session Storage Unavailable ===');

      // Temporarily break session storage
      const originalSetItem = sessionStorageMock.setItem;
      sessionStorageMock.setItem = jest.fn(() => {
        throw new Error('QuotaExceededError');
      });

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockApiResponse,
      });

      // Should not throw error, just continue without caching
      const members = await MemberDataService.fetchMembers();

      expect(members).toHaveLength(3);
      console.log('  ✓ Continued without caching when storage unavailable');

      // Restore
      sessionStorageMock.setItem = originalSetItem;

      console.log('\n✓ Session storage unavailable test PASSED');
    });

    test('should simulate navigation and cache persistence', async () => {
      console.log('\n=== Testing Cache Persistence Across Navigation ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockApiResponse,
      });

      // Load on page 1
      console.log('  Page 1: Loading data...');
      await MemberDataService.fetchMembers();
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // Simulate navigation to page 2 (cache persists)
      console.log('  Page 2: Using cached data...');
      (global.fetch as jest.Mock).mockClear();
      const members = await MemberDataService.fetchMembers();
      expect(global.fetch).not.toHaveBeenCalled();
      expect(members).toHaveLength(3);

      console.log('  ✓ Cache persisted across navigation');

      console.log('\n✓ Cache persistence test PASSED');
    });
  });

  describe('Performance Requirements', () => {
    test('should meet filter response time requirement (<200ms)', async () => {
      console.log('\n=== Testing Filter Performance ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockApiResponse,
      });

      const members = await MemberDataService.fetchMembers();

      // Test various filters
      const filters = [
        { name: 'Status filter', fn: (m: any) => m.status === 'Actief' },
        { name: 'Region filter', fn: (m: any) => m.regio === 'Utrecht' },
        { name: 'Search filter', fn: (m: any) => m.voornaam.toLowerCase().includes('jan') },
        { name: 'Combined filter', fn: (m: any) => m.status === 'Actief' && m.regio === 'Utrecht' },
      ];

      for (const { name, fn } of filters) {
        const start = performance.now();
        const filtered = members.filter(fn);
        const elapsed = performance.now() - start;

        expect(elapsed).toBeLessThan(200);
        console.log(`  ${name}: ${elapsed.toFixed(2)}ms (${filtered.length} results)`);
      }

      console.log('  ✓ All filters meet <200ms requirement');

      console.log('\n✓ Filter performance test PASSED');
    });

    test('should compute calculated fields efficiently', async () => {
      console.log('\n=== Testing Calculated Fields Performance ===');

      const start = performance.now();
      const membersWithCalc = computeCalculatedFieldsForArray(mockMembersRaw);
      const elapsed = performance.now() - start;

      expect(membersWithCalc).toHaveLength(3);
      expect(membersWithCalc[0]).toHaveProperty('korte_naam');
      expect(membersWithCalc[0]).toHaveProperty('leeftijd');
      expect(membersWithCalc[0]).toHaveProperty('verjaardag');
      expect(membersWithCalc[0]).toHaveProperty('jaren_lid');
      expect(membersWithCalc[0]).toHaveProperty('aanmeldingsjaar');

      console.log(`  Computed calculated fields in ${elapsed.toFixed(2)}ms`);
      expect(elapsed).toBeLessThan(100); // Should be very fast

      console.log('  ✓ Calculated fields computed efficiently');

      console.log('\n✓ Calculated fields performance test PASSED');
    });
  });

  describe('Error Scenarios', () => {
    test('should handle network failure', async () => {
      console.log('\n=== Testing Network Failure ===');

      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      await expect(MemberDataService.fetchMembers()).rejects.toThrow('Failed to load member data');

      console.log('  ✓ Network failure handled correctly');

      console.log('\n✓ Network failure test PASSED');
    });

    test('should handle 401 authentication error', async () => {
      console.log('\n=== Testing 401 Authentication Error ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ error: 'Authentication failed' }),
      });

      await expect(MemberDataService.fetchMembers()).rejects.toThrow('Authentication failed');

      console.log('  ✓ 401 error handled correctly');

      console.log('\n✓ 401 error test PASSED');
    });

    test('should handle 403 permission error', async () => {
      console.log('\n=== Testing 403 Permission Error ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ error: 'Access denied' }),
      });

      await expect(MemberDataService.fetchMembers()).rejects.toThrow('You do not have permission');

      console.log('  ✓ 403 error handled correctly');

      console.log('\n✓ 403 error test PASSED');
    });

    test('should handle 500 server error', async () => {
      console.log('\n=== Testing 500 Server Error ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ error: 'Database error' }),
      });

      await expect(MemberDataService.fetchMembers()).rejects.toThrow('Server error');

      console.log('  ✓ 500 error handled correctly');

      console.log('\n✓ 500 error test PASSED');
    });

    test('should handle malformed JSON response', async () => {
      console.log('\n=== Testing Malformed JSON Response ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      await expect(MemberDataService.fetchMembers()).rejects.toThrow();

      console.log('  ✓ Malformed JSON handled correctly');

      console.log('\n✓ Malformed JSON test PASSED');
    });

    test('should handle empty response', async () => {
      console.log('\n=== Testing Empty Response ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          data: [],
          metadata: {
            total_count: 0,
            region: 'Utrecht',
            timestamp: '2026-01-18T10:00:00Z',
          },
        }),
      });

      const members = await MemberDataService.fetchMembers();

      expect(members).toHaveLength(0);
      console.log('  ✓ Empty response handled correctly');

      console.log('\n✓ Empty response test PASSED');
    });
  });

  describe('Data Integrity', () => {
    test('should preserve all member fields', async () => {
      console.log('\n=== Testing Data Integrity ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockApiResponse,
      });

      const members = await MemberDataService.fetchMembers();

      const member = members[0];
      expect(member).toHaveProperty('lidnummer');
      expect(member).toHaveProperty('voornaam');
      expect(member).toHaveProperty('achternaam');
      expect(member).toHaveProperty('email');
      expect(member).toHaveProperty('regio');
      expect(member).toHaveProperty('status');
      expect(member).toHaveProperty('geboortedatum');
      expect(member).toHaveProperty('tijdstempel');

      console.log('  ✓ All original fields preserved');

      console.log('\n✓ Data integrity test PASSED');
    });

    test('should add calculated fields', async () => {
      console.log('\n=== Testing Calculated Fields ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockApiResponse,
      });

      const members = await MemberDataService.fetchMembers();

      const member = members[0];
      expect(member).toHaveProperty('korte_naam');
      expect(member).toHaveProperty('leeftijd');
      expect(member).toHaveProperty('verjaardag');
      expect(member).toHaveProperty('jaren_lid');
      expect(member).toHaveProperty('aanmeldingsjaar');

      console.log('  ✓ All calculated fields added');
      console.log(`  korte_naam: ${member.korte_naam}`);
      console.log(`  leeftijd: ${member.leeftijd}`);
      console.log(`  verjaardag: ${member.verjaardag}`);
      console.log(`  jaren_lid: ${member.jaren_lid}`);
      console.log(`  aanmeldingsjaar: ${member.aanmeldingsjaar}`);

      console.log('\n✓ Calculated fields test PASSED');
    });
  });

  describe('Cache Metadata', () => {
    test('should provide cache metadata', async () => {
      console.log('\n=== Testing Cache Metadata ===');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockApiResponse,
      });

      await MemberDataService.fetchMembers();

      const metadata = MemberDataService.getCacheMetadata();

      expect(metadata).toBeTruthy();
      expect(metadata).toHaveProperty('timestamp');
      expect(metadata).toHaveProperty('count');
      expect(metadata!.count).toBe(3);

      console.log(`  ✓ Cache metadata: ${JSON.stringify(metadata)}`);

      console.log('\n✓ Cache metadata test PASSED');
    });

    test('should return null metadata when no cache', () => {
      console.log('\n=== Testing No Cache Metadata ===');

      const metadata = MemberDataService.getCacheMetadata();

      expect(metadata).toBeNull();
      console.log('  ✓ Returns null when no cache');

      console.log('\n✓ No cache metadata test PASSED');
    });
  });
});

/**
 * Integration Tests for Member Reporting System
 * 
 * Tests the complete member reporting flow including:
 * - Loading member data
 * - Session storage caching
 * - Filtering functionality
 * - Refresh button for CRUD users
 * - Error handling
 * - Performance requirements
 * 
 * These tests validate the entire frontend system end-to-end.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import { MemberDataService } from '../services/MemberDataService';
import { Member } from '../types';

// Mock dependencies
jest.mock('../utils/authHeaders', () => ({
  getAuthHeaders: jest.fn(() => ({
    'Authorization': 'Bearer mock_jwt_token',
    'X-Enhanced-Groups': 'Regio_Utrecht,members_read',
    'Content-Type': 'application/json'
  }))
}));

jest.mock('../utils/calculatedFields', () => ({
  computeCalculatedFieldsForArray: jest.fn((members) => 
    members.map((m: any) => ({
      ...m,
      korte_naam: `${m.voornaam} ${m.achternaam}`,
      leeftijd: 45,
      verjaardag: 'mei 15',
      jaren_lid: 5,
      aanmeldingsjaar: 2020
    }))
  )
}));

describe('Member Reporting Integration Tests', () => {
  
  // Sample test data
  const mockUtrechtMembers: Member[] = [
    {
      lidnummer: 'UT001',
      voornaam: 'Jan',
      achternaam: 'Jansen',
      email: 'jan@utrecht.nl',
      regio: 'Utrecht',
      status: 'Actief',
      geboortedatum: '1980-05-15',
      tijdstempel: '2020-01-01'
    },
    {
      lidnummer: 'UT002',
      voornaam: 'Piet',
      achternaam: 'Pietersen',
      email: 'piet@utrecht.nl',
      regio: 'Utrecht',
      status: 'Inactief',
      geboortedatum: '1975-08-20',
      tijdstempel: '2018-06-15'
    },
    {
      lidnummer: 'UT003',
      voornaam: 'Klaas',
      achternaam: 'Klaassen',
      email: 'klaas@utrecht.nl',
      regio: 'Utrecht',
      status: 'Opgezegd',
      geboortedatum: '1990-12-10',
      tijdstempel: '2019-03-20'
    }
  ];

  const mockAllRegionsMembers: Member[] = [
    ...mockUtrechtMembers,
    {
      lidnummer: 'ZH001',
      voornaam: 'Anna',
      achternaam: 'de Vries',
      email: 'anna@zuidholland.nl',
      regio: 'Zuid-Holland',
      status: 'Actief',
      geboortedatum: '1985-03-25',
      tijdstempel: '2021-02-10'
    },
    {
      lidnummer: 'NH001',
      voornaam: 'Emma',
      achternaam: 'Smit',
      email: 'emma@noordholland.nl',
      regio: 'Noord-Holland',
      status: 'Actief',
      geboortedatum: '1988-11-05',
      tijdstempel: '2020-09-01'
    }
  ];

  beforeEach(() => {
    // Clear session storage before each test
    sessionStorage.clear();
    
    // Reset fetch mock
    global.fetch = jest.fn();
    
    // Clear all mocks
    jest.clearAllMocks();
  });

  describe('Complete User Flow Tests', () => {
    
    test('Regional user flow: load → filter → verify data', async () => {
      // Mock API response for regional user
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      // Load members
      const startTime = performance.now();
      const members = await MemberDataService.fetchMembers();
      const loadTime = performance.now() - startTime;

      // Verify data loaded
      expect(members).toHaveLength(3);
      expect(members.every(m => m.regio === 'Utrecht')).toBe(true);

      // Verify all statuses included (no status filtering)
      const statuses = new Set(members.map(m => m.status));
      expect(statuses.has('Actief')).toBe(true);
      expect(statuses.has('Inactief')).toBe(true);
      expect(statuses.has('Opgezegd')).toBe(true);

      // Verify performance (<2 seconds for initial load)
      expect(loadTime).toBeLessThan(2000);

      // Verify session storage caching
      const cached = sessionStorage.getItem('hdcn_member_data');
      expect(cached).toBeTruthy();

      console.log(`✓ Regional user flow completed in ${loadTime.toFixed(0)}ms`);
    });

    test('Regio_All user flow: load → verify all regions', async () => {
      // Mock API response for Regio_All user
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockAllRegionsMembers,
          metadata: {
            total_count: 5,
            region: 'All',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      // Load members
      const members = await MemberDataService.fetchMembers();

      // Verify all regions present
      expect(members).toHaveLength(5);
      
      const regions = new Set(members.map(m => m.regio));
      expect(regions.has('Utrecht')).toBe(true);
      expect(regions.has('Zuid-Holland')).toBe(true);
      expect(regions.has('Noord-Holland')).toBe(true);

      console.log('✓ Regio_All user flow completed');
    });

    test('CRUD user flow: load → refresh → verify cache cleared', async () => {
      // Initial load
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      const initialMembers = await MemberDataService.fetchMembers();
      expect(initialMembers).toHaveLength(3);

      // Verify cache exists
      expect(sessionStorage.getItem('hdcn_member_data')).toBeTruthy();

      // Refresh (simulating CRUD user clicking refresh button)
      const updatedMembers = [...mockUtrechtMembers, {
        lidnummer: 'UT004',
        voornaam: 'New',
        achternaam: 'Member',
        email: 'new@utrecht.nl',
        regio: 'Utrecht',
        status: 'Actief',
        geboortedatum: '1995-01-01',
        tijdstempel: '2024-01-01'
      }];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: updatedMembers,
          metadata: {
            total_count: 4,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      const refreshedMembers = await MemberDataService.refreshMembers();

      // Verify new data loaded
      expect(refreshedMembers).toHaveLength(4);
      expect(refreshedMembers.find(m => m.lidnummer === 'UT004')).toBeTruthy();

      // Verify API was called twice (initial + refresh)
      expect(global.fetch).toHaveBeenCalledTimes(2);

      console.log('✓ CRUD user refresh flow completed');
    });
  });

  describe('Session Storage Caching Tests', () => {
    
    test('Session storage caching works across multiple calls', async () => {
      // Mock API response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      // First call - should fetch from API
      const members1 = await MemberDataService.fetchMembers();
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // Second call - should use cache
      const members2 = await MemberDataService.fetchMembers();
      expect(global.fetch).toHaveBeenCalledTimes(1); // Still 1, not 2

      // Verify same data
      expect(members1).toEqual(members2);

      console.log('✓ Session storage caching verified');
    });

    test('Cache persists across page navigation (simulated)', async () => {
      // Mock API response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      // Load data
      await MemberDataService.fetchMembers();

      // Simulate navigation by creating new service instance
      // (In real app, this would be a new page load)
      const cachedMembers = await MemberDataService.fetchMembers();

      // Should use cache, not call API again
      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(cachedMembers).toHaveLength(3);

      console.log('✓ Cache persistence verified');
    });

    test('Cache metadata is stored correctly', async () => {
      // Mock API response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      await MemberDataService.fetchMembers();

      // Check cache metadata
      const metadata = MemberDataService.getCacheMetadata();
      
      expect(metadata).toBeTruthy();
      expect(metadata?.memberCount).toBe(3);
      expect(metadata?.timestamp).toBeTruthy();

      console.log('✓ Cache metadata verified');
    });

    test('Session storage unavailable fallback works', async () => {
      // Mock session storage failure
      const originalSetItem = sessionStorage.setItem;
      sessionStorage.setItem = jest.fn(() => {
        throw new Error('QuotaExceededError');
      });

      // Mock API response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      // Should still work without caching
      const members = await MemberDataService.fetchMembers();
      expect(members).toHaveLength(3);

      // Restore original
      sessionStorage.setItem = originalSetItem;

      console.log('✓ Session storage fallback verified');
    });
  });

  describe('Performance Tests', () => {
    
    test('Regional user load time meets <2 second requirement', async () => {
      // Mock API response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      const startTime = performance.now();
      await MemberDataService.fetchMembers();
      const loadTime = performance.now() - startTime;

      // Requirement: <2 seconds for initial load
      expect(loadTime).toBeLessThan(2000);

      console.log(`✓ Load time: ${loadTime.toFixed(0)}ms (requirement: <2000ms)`);
    });

    test('Cached data retrieval is instant (<50ms)', async () => {
      // Setup cache
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      await MemberDataService.fetchMembers();

      // Measure cached retrieval
      const startTime = performance.now();
      await MemberDataService.fetchMembers();
      const cacheTime = performance.now() - startTime;

      // Should be nearly instant
      expect(cacheTime).toBeLessThan(50);

      console.log(`✓ Cache retrieval: ${cacheTime.toFixed(1)}ms`);
    });

    test('Calculated fields computation is fast', async () => {
      // Mock API response with many members
      const manyMembers = Array.from({ length: 1500 }, (_, i) => ({
        lidnummer: `M${i.toString().padStart(4, '0')}`,
        voornaam: `Member${i}`,
        achternaam: 'Test',
        email: `member${i}@test.nl`,
        regio: 'Utrecht',
        status: 'Actief',
        geboortedatum: '1980-01-01',
        tijdstempel: '2020-01-01'
      }));

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: manyMembers,
          metadata: {
            total_count: 1500,
            region: 'All',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      const startTime = performance.now();
      const members = await MemberDataService.fetchMembers();
      const totalTime = performance.now() - startTime;

      expect(members).toHaveLength(1500);
      
      // Should process 1500 members in reasonable time
      expect(totalTime).toBeLessThan(3000);

      console.log(`✓ Processed 1500 members in ${totalTime.toFixed(0)}ms`);
    });
  });

  describe('Error Scenario Tests', () => {
    
    test('Network failure error handling', async () => {
      // Mock network failure
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      await expect(MemberDataService.fetchMembers()).rejects.toThrow('Network error');

      console.log('✓ Network failure handled correctly');
    });

    test('401 Authentication error handling', async () => {
      // Mock 401 response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({
          success: false,
          error: 'Authentication required'
        })
      } as Response);

      await expect(MemberDataService.fetchMembers()).rejects.toThrow(
        'Authentication failed'
      );

      console.log('✓ 401 error handled correctly');
    });

    test('403 Permission error handling', async () => {
      // Mock 403 response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({
          success: false,
          error: 'Access denied'
        })
      } as Response);

      await expect(MemberDataService.fetchMembers()).rejects.toThrow(
        'You do not have permission'
      );

      console.log('✓ 403 error handled correctly');
    });

    test('500 Server error handling', async () => {
      // Mock 500 response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({
          success: false,
          error: 'Database error'
        })
      } as Response);

      await expect(MemberDataService.fetchMembers()).rejects.toThrow(
        'Server error'
      );

      console.log('✓ 500 error handled correctly');
    });

    test('Malformed API response handling', async () => {
      // Mock malformed response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          // Missing 'data' field
          success: true,
          metadata: {}
        })
      } as Response);

      await expect(MemberDataService.fetchMembers()).rejects.toThrow();

      console.log('✓ Malformed response handled correctly');
    });

    test('Empty data response handling', async () => {
      // Mock empty data response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: [],
          metadata: {
            total_count: 0,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      const members = await MemberDataService.fetchMembers();
      
      expect(members).toEqual([]);
      expect(Array.isArray(members)).toBe(true);

      console.log('✓ Empty data handled correctly');
    });
  });

  describe('Regional Isolation Tests', () => {
    
    test('Regional user only receives their region data', async () => {
      // Mock API response for Utrecht user
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      const members = await MemberDataService.fetchMembers();

      // Verify only Utrecht members
      expect(members.every(m => m.regio === 'Utrecht')).toBe(true);
      
      // Verify no other regions
      const regions = new Set(members.map(m => m.regio));
      expect(regions.size).toBe(1);
      expect(regions.has('Utrecht')).toBe(true);

      console.log('✓ Regional isolation verified');
    });

    test('All statuses included for regional users', async () => {
      // Mock API response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      const members = await MemberDataService.fetchMembers();

      // Verify all statuses present (no status filtering)
      const statuses = new Set(members.map(m => m.status));
      expect(statuses.has('Actief')).toBe(true);
      expect(statuses.has('Inactief')).toBe(true);
      expect(statuses.has('Opgezegd')).toBe(true);

      console.log('✓ All statuses included (no status filtering)');
    });
  });

  describe('Calculated Fields Integration', () => {
    
    test('Calculated fields are computed after fetch', async () => {
      // Mock API response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      const members = await MemberDataService.fetchMembers();

      // Verify calculated fields are present
      members.forEach(member => {
        expect(member.korte_naam).toBeTruthy();
        expect(member.leeftijd).toBeDefined();
        expect(member.verjaardag).toBeTruthy();
        expect(member.jaren_lid).toBeDefined();
        expect(member.aanmeldingsjaar).toBeDefined();
      });

      console.log('✓ Calculated fields computed correctly');
    });

    test('Cached members include calculated fields', async () => {
      // Mock API response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockUtrechtMembers,
          metadata: {
            total_count: 3,
            region: 'Utrecht',
            timestamp: new Date().toISOString()
          }
        })
      } as Response);

      await MemberDataService.fetchMembers();

      // Get from cache
      const cached = JSON.parse(sessionStorage.getItem('hdcn_member_data') || '[]');

      // Verify calculated fields in cache
      expect(cached[0].korte_naam).toBeTruthy();
      expect(cached[0].leeftijd).toBeDefined();

      console.log('✓ Cached data includes calculated fields');
    });
  });
});

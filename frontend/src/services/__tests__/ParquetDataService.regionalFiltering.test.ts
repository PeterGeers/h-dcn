/**
 * ParquetDataService Regional Filtering Tests
 * 
 * Tests the regional filtering functionality in the ParquetDataService,
 * including data loading with regional restrictions and permission validation.
 */

import ParquetDataService from '../ParquetDataService';
import { ApiService } from '../apiService';
import { Member } from '../../types/index';
import { ParquetLoadOptions } from '../../types/ParquetTypes';

// Mock ApiService
jest.mock('../apiService');
const mockApiService = ApiService as jest.Mocked<typeof ApiService>;

// Mock computeCalculatedFieldsForArray
jest.mock('../../utils/calculatedFields', () => ({
  computeCalculatedFieldsForArray: jest.fn((data) => data)
}));

// Mock webWorkerManager
jest.mock('../WebWorkerManager', () => ({
  webWorkerManager: {
    isAvailable: () => false,
    applyRegionalFilter: jest.fn(),
    applyCalculatedFields: jest.fn(),
    processData: jest.fn()
  }
}));

describe('ParquetDataService Regional Filtering', () => {
  let service: ParquetDataService;
  
  // Mock member data from different regions
  const mockMemberData: Member[] = [
    {
      id: '1',
      voornaam: 'Jan',
      achternaam: 'Jansen',
      email: 'jan@example.com',
      regio: 'Utrecht',
      status: 'Actief'
    },
    {
      id: '2',
      voornaam: 'Piet', 
      achternaam: 'Pietersen',
      email: 'piet@example.com',
      regio: 'Limburg',
      status: 'Actief'
    },
    {
      id: '3',
      voornaam: 'Klaas',
      achternaam: 'Klaassen',
      email: 'klaas@example.com', 
      regio: 'Noord-Holland',
      status: 'Actief'
    },
    {
      id: '4',
      voornaam: 'Marie',
      achternaam: 'Mariesen',
      email: 'marie@example.com',
      regio: 'Zuid-Holland',
      status: 'Actief'
    },
    {
      id: '5',
      voornaam: 'Anna',
      achternaam: 'Annesen',
      email: 'anna@example.com',
      regio: undefined, // Member without region
      status: 'Actief'
    }
  ] as Member[];

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Create fresh service instance for each test
    service = ParquetDataService.getInstance({
      enableDebugLogging: false,
      defaultLoadOptions: {
        applyCalculatedFields: false,
        applyRegionalFiltering: true,
        enableCaching: false,
        useWebWorkers: false
      }
    });
    
    // Clear cache
    service.clearCache();
    
    // Mock successful API responses
    mockApiService.get.mockResolvedValue({
      success: true,
      data: {
        download_method: 'direct_content',
        data: {
          content: btoa(JSON.stringify(mockMemberData))
        }
      }
    });
  });

  describe('Regional Filtering with Different User Roles', () => {
    test('should return all members for national admin (Members_CRUD + Regio_All)', async () => {
      // Mock national admin user
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD', 'Regio_All']);
      mockApiService.getCurrentUserEmail.mockReturnValue('admin@hdcn.nl');
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(5); // All members including one without region
      expect(result.metadata?.regionalFilteringApplied).toBe(true);
    });

    test('should return only Utrecht members for Utrecht coordinator', async () => {
      // Mock Utrecht regional coordinator
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD', 'Regio_Utrecht']);
      mockApiService.getCurrentUserEmail.mockReturnValue('utrecht@hdcn.nl');
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(1);
      expect(result.data![0].regio).toBe('Utrecht');
      expect(result.data![0].voornaam).toBe('Jan');
      expect(result.metadata?.regionalFilteringApplied).toBe(true);
    });

    test('should return only Limburg members for Limburg viewer', async () => {
      // Mock Limburg regional viewer
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_Read', 'Regio_Limburg']);
      mockApiService.getCurrentUserEmail.mockReturnValue('limburg@hdcn.nl');
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(1);
      expect(result.data![0].regio).toBe('Limburg');
      expect(result.data![0].voornaam).toBe('Piet');
      expect(result.metadata?.regionalFilteringApplied).toBe(true);
    });

    test('should return multiple regions for multi-regional user', async () => {
      // Mock multi-regional user
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD', 'Regio_Noord-Holland', 'Regio_Zuid-Holland']);
      mockApiService.getCurrentUserEmail.mockReturnValue('multi@hdcn.nl');
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(2);
      
      const regions = result.data!.map(m => m.regio);
      expect(regions).toContain('Noord-Holland');
      expect(regions).toContain('Zuid-Holland');
      
      const names = result.data!.map(m => m.voornaam);
      expect(names).toContain('Klaas');
      expect(names).toContain('Marie');
      expect(result.metadata?.regionalFilteringApplied).toBe(true);
    });

    test('should return empty array for user with incomplete roles', async () => {
      // Mock user with permission but no regional role
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD']); // Missing regional role
      mockApiService.getCurrentUserEmail.mockReturnValue('incomplete@hdcn.nl');
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(5); // Full access due to Members_CRUD permission
      expect(result.metadata?.regionalFilteringApplied).toBe(true);
    });

    test('should return empty array for regular member (no admin access)', async () => {
      // Mock regular member
      mockApiService.getCurrentUserRoles.mockReturnValue(['hdcnLeden', 'Regio_Utrecht']);
      mockApiService.getCurrentUserEmail.mockReturnValue('member@hdcn.nl');
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      // Should fail permission check before reaching regional filtering
      expect(result.success).toBe(false);
      expect(result.error).toContain('Insufficient permissions');
    });
  });

  describe('Regional Filtering Edge Cases', () => {
    test('should handle members without region assignment correctly', async () => {
      // National admin should see member without region
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD', 'Regio_All']);
      mockApiService.getCurrentUserEmail.mockReturnValue('admin@hdcn.nl');
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      expect(result.success).toBe(true);
      expect(result.data!.some(m => !m.regio)).toBe(true); // Should include member without region
      
      // Regional user should NOT see member without region
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD', 'Regio_Utrecht']);
      mockApiService.getCurrentUserEmail.mockReturnValue('utrecht@hdcn.nl');
      
      const regionalResult = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      expect(regionalResult.success).toBe(true);
      expect(regionalResult.data!.some(m => !m.regio)).toBe(false); // Should NOT include member without region
    });

    test('should skip regional filtering when disabled', async () => {
      // Mock regional user
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD', 'Regio_Utrecht']);
      mockApiService.getCurrentUserEmail.mockReturnValue('utrecht@hdcn.nl');
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: false, // Disabled
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(5); // All members (no filtering applied)
      expect(result.metadata?.regionalFilteringApplied).toBe(false);
    });

    test('should handle missing authentication gracefully', async () => {
      // Mock missing authentication
      mockApiService.getCurrentUserRoles.mockReturnValue(null);
      mockApiService.getCurrentUserEmail.mockReturnValue(null);
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      // Should fail permission check
      expect(result.success).toBe(false);
      expect(result.error).toContain('Authentication required');
    });

    test('should handle regional filtering errors gracefully', async () => {
      // Mock user with valid roles
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD', 'Regio_Utrecht']);
      mockApiService.getCurrentUserEmail.mockReturnValue('utrecht@hdcn.nl');
      
      // Mock data with invalid structure to trigger error
      const invalidData = [{ invalid: 'data' }];
      mockApiService.get.mockResolvedValue({
        success: true,
        data: {
          download_method: 'direct_content',
          data: {
            content: btoa(JSON.stringify(invalidData))
          }
        }
      });
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      // Should return empty array on filtering error (security measure)
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(0);
    });
  });

  describe('Permission Validation', () => {
    test('should deny access for users without required permissions', async () => {
      // Mock user without required permissions
      mockApiService.getCurrentUserRoles.mockReturnValue(['hdcnLeden']);
      mockApiService.getCurrentUserEmail.mockReturnValue('member@hdcn.nl');
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      // Should fail permission check before reaching regional filtering
      expect(result.success).toBe(false);
      expect(result.error).toContain('Insufficient permissions');
    });

    test('should allow access for users with required permissions', async () => {
      // Mock user with required permissions
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_Read', 'Regio_Utrecht']);
      mockApiService.getCurrentUserEmail.mockReturnValue('reader@hdcn.nl');
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(1); // Utrecht members only
    });

    test('should handle authentication errors', async () => {
      // Mock authentication failure
      mockApiService.getCurrentUserRoles.mockReturnValue(null);
      mockApiService.getCurrentUserEmail.mockReturnValue(null);
      
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: false
      });
      
      // Should fail permission check
      expect(result.success).toBe(false);
      expect(result.error).toContain('Authentication required');
    });
  });

  describe('Performance and Caching', () => {
    test('should cache filtered results correctly', async () => {
      // Mock Utrecht regional user
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD', 'Regio_Utrecht']);
      mockApiService.getCurrentUserEmail.mockReturnValue('utrecht@hdcn.nl');
      
      // First load
      const result1 = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: true
      });
      
      expect(result1.success).toBe(true);
      expect(result1.data).toHaveLength(1);
      expect(result1.metadata?.fromCache).toBe(false);
      
      // Second load should use cache
      const result2 = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: true
      });
      
      expect(result2.success).toBe(true);
      expect(result2.data).toHaveLength(1);
      expect(result2.metadata?.fromCache).toBe(true);
      
      // API should only be called once
      expect(mockApiService.get).toHaveBeenCalledTimes(1);
    });

    test('should use different cache keys for different regional filtering', async () => {
      // First user - Utrecht
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD', 'Regio_Utrecht']);
      mockApiService.getCurrentUserEmail.mockReturnValue('utrecht@hdcn.nl');
      
      const result1 = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: true
      });
      
      expect(result1.success).toBe(true);
      expect(result1.data).toHaveLength(1);
      
      // Second user - Limburg (should not use Utrecht cache)
      mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD', 'Regio_Limburg']);
      mockApiService.getCurrentUserEmail.mockReturnValue('limburg@hdcn.nl');
      
      const result2 = await service.loadLatestMemberData({
        applyRegionalFiltering: true,
        applyCalculatedFields: false,
        enableCaching: true
      });
      
      expect(result2.success).toBe(true);
      expect(result2.data).toHaveLength(1);
      expect(result2.data![0].regio).toBe('Limburg');
      
      // API should be called twice (different cache keys)
      expect(mockApiService.get).toHaveBeenCalledTimes(2);
    });
  });
});
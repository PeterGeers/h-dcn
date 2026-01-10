/**
 * Tests for ParquetDataService
 * 
 * These tests verify the core functionality of loading raw parquet files
 * from the backend API and applying calculated fields.
 */

import { ParquetDataService } from '../ParquetDataService';
import { ApiService } from '../apiService';
import { computeCalculatedFieldsForArray } from '../../utils/calculatedFields';

// Mock dependencies
jest.mock('../apiService');
jest.mock('../../utils/calculatedFields');

const mockApiService = ApiService as jest.Mocked<typeof ApiService>;
const mockComputeCalculatedFieldsForArray = computeCalculatedFieldsForArray as jest.MockedFunction<typeof computeCalculatedFieldsForArray>;

describe('ParquetDataService', () => {
  let service: ParquetDataService;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Create a fresh service instance for each test
    service = new (ParquetDataService as any)();
    
    // Mock ApiService methods with proper permissions by default
    mockApiService.getCurrentUserRoles.mockReturnValue(['Members_CRUD']);
    mockApiService.getCurrentUserEmail.mockReturnValue('test@example.com');
  });

  describe('loadLatestMemberData', () => {
    it('should successfully load and process parquet data', async () => {
      // Mock API response for parquet download
      const mockParquetResponse = {
        success: true,
        data: {
          download_method: 'direct_content' as const,
          data: {
            content: btoa(JSON.stringify([
              {
                voornaam: 'Jan',
                achternaam: 'Doe',
                geboortedatum: '1980-01-01',
                tijdstempel: '2020-01-01'
              },
              {
                voornaam: 'Jane',
                achternaam: 'Smith',
                geboortedatum: '1985-05-15',
                tijdstempel: '2021-03-15'
              }
            ])),
            filename: 'members.parquet',
            size: 1024
          }
        }
      };

      mockApiService.get.mockResolvedValue(mockParquetResponse);

      // Mock calculated fields processing
      const mockProcessedData = [
        {
          voornaam: 'Jan',
          achternaam: 'Doe',
          geboortedatum: '1980-01-01',
          tijdstempel: '2020-01-01',
          korte_naam: 'Jan Doe',
          leeftijd: 44
        },
        {
          voornaam: 'Jane',
          achternaam: 'Smith',
          geboortedatum: '1985-05-15',
          tijdstempel: '2021-03-15',
          korte_naam: 'Jane Smith',
          leeftijd: 39
        }
      ];

      mockComputeCalculatedFieldsForArray.mockReturnValue(mockProcessedData as any);

      // Test the load function
      const result = await service.loadLatestMemberData({
        applyCalculatedFields: true,
        applyRegionalFiltering: false,
        enableCaching: false
      });

      // Verify the result
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(2);
      expect(result.data![0].korte_naam).toBe('Jan Doe');
      expect(result.data![1].korte_naam).toBe('Jane Smith');
      expect(result.metadata?.recordCount).toBe(2);
      expect(result.metadata?.calculatedFieldsApplied).toBe(true);

      // Verify API was called correctly
      expect(mockApiService.get).toHaveBeenCalledWith('/analytics/download-parquet/latest');
      
      // Verify calculated fields were applied
      expect(mockComputeCalculatedFieldsForArray).toHaveBeenCalledWith([
        {
          voornaam: 'Jan',
          achternaam: 'Doe',
          geboortedatum: '1980-01-01',
          tijdstempel: '2020-01-01'
        },
        {
          voornaam: 'Jane',
          achternaam: 'Smith',
          geboortedatum: '1985-05-15',
          tijdstempel: '2021-03-15'
        }
      ]);
    });

    it('should handle API errors gracefully', async () => {
      // Mock API error
      mockApiService.get.mockResolvedValue({
        success: false,
        error: 'Authentication failed'
      });

      // Test the load function
      const result = await service.loadLatestMemberData();

      // Verify error handling
      expect(result.success).toBe(false);
      expect(result.error).toContain('Authentication failed');
      expect(result.data).toBeUndefined();
    });

    it('should handle permission errors', async () => {
      // Mock user without required permissions
      mockApiService.getCurrentUserRoles.mockReturnValue(['SomeOtherRole']);
      mockApiService.getCurrentUserEmail.mockReturnValue('unauthorized@example.com');

      // Test the load function
      const result = await service.loadLatestMemberData();

      // Verify permission error handling
      expect(result.success).toBe(false);
      expect(result.error).toContain('Insufficient permissions');
      expect(result.data).toBeUndefined();
      
      // API should not be called if permissions fail
      expect(mockApiService.get).not.toHaveBeenCalled();
    });

    it('should handle missing authentication', async () => {
      // Mock missing authentication
      mockApiService.getCurrentUserRoles.mockReturnValue([]);
      mockApiService.getCurrentUserEmail.mockReturnValue(null);

      // Test the load function
      const result = await service.loadLatestMemberData();

      // Verify authentication error handling
      expect(result.success).toBe(false);
      expect(result.error).toContain('Authentication required');
      expect(result.data).toBeUndefined();
    });

    it('should handle parquet parsing errors', async () => {
      // Mock API response with invalid content
      const mockParquetResponse = {
        success: true,
        data: {
          download_method: 'direct_content' as const,
          data: {
            content: 'invalid-base64-content',
            filename: 'members.parquet',
            size: 1024
          }
        }
      };

      mockApiService.get.mockResolvedValue(mockParquetResponse);

      // Test the load function
      const result = await service.loadLatestMemberData();

      // Verify error handling
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('should load data without regional filtering (comes in next step)', async () => {
      // Mock API response
      const mockParquetResponse = {
        success: true,
        data: {
          download_method: 'direct_content' as const,
          data: {
            content: btoa(JSON.stringify([
              { voornaam: 'Jan', regio: 'Noord' },
              { voornaam: 'Jane', regio: 'Zuid' },
              { voornaam: 'Bob', regio: 'Noord' }
            ])),
            filename: 'members.parquet',
            size: 1024
          }
        }
      };

      mockApiService.get.mockResolvedValue(mockParquetResponse);
      mockComputeCalculatedFieldsForArray.mockImplementation((data) => data as any);

      // Test the load function without regional filtering (basic loading only)
      const result = await service.loadLatestMemberData({
        applyRegionalFiltering: false
      });

      // Verify basic loading works (regional filtering comes in next step)
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(3); // All members loaded
      expect(result.metadata?.regionalFilteringApplied).toBe(false);
    });

    it('should skip calculated fields when disabled', async () => {
      // Mock API response
      const mockParquetResponse = {
        success: true,
        data: {
          download_method: 'direct_content' as const,
          data: {
            content: btoa(JSON.stringify([
              { voornaam: 'Jan', achternaam: 'Doe' }
            ])),
            filename: 'members.parquet',
            size: 1024
          }
        }
      };

      mockApiService.get.mockResolvedValue(mockParquetResponse);

      // Test the load function without calculated fields
      const result = await service.loadLatestMemberData({
        applyCalculatedFields: false
      });

      // Verify calculated fields were not applied
      expect(result.success).toBe(true);
      expect(result.metadata?.calculatedFieldsApplied).toBe(false);
      expect(mockComputeCalculatedFieldsForArray).not.toHaveBeenCalled();
    });
  });

  describe('getParquetStatus', () => {
    it('should return file status information', async () => {
      // Mock API response
      const mockStatusResponse = {
        success: true,
        data: {
          data: {
            filename: 'members-2024-01-08.parquet',
            size: 150000
          }
        }
      };

      mockApiService.get.mockResolvedValue(mockStatusResponse);

      // Test the status function
      const status = await service.getParquetStatus();

      // Verify the result
      expect(status.available).toBe(true);
      expect(status.files).toHaveLength(1);
      expect(status.files[0].filename).toBe('members-2024-01-08.parquet');
      expect(status.files[0].size).toBe(150000);
    });

    it('should handle status check errors', async () => {
      // Mock API error
      mockApiService.get.mockResolvedValue({
        success: false,
        error: 'File not found'
      });

      // Test the status function
      const status = await service.getParquetStatus();

      // Verify error handling
      expect(status.available).toBe(false);
      expect(status.error).toContain('File not found');
    });
  });

  describe('caching', () => {
    it('should cache loaded data', async () => {
      // Mock API response
      const mockParquetResponse = {
        success: true,
        data: {
          download_method: 'direct_content' as const,
          data: {
            content: btoa(JSON.stringify([{ voornaam: 'Jan' }])),
            filename: 'members.parquet',
            size: 1024
          }
        }
      };

      mockApiService.get.mockResolvedValue(mockParquetResponse);
      mockComputeCalculatedFieldsForArray.mockImplementation((data) => data as any);

      // First load
      const result1 = await service.loadLatestMemberData({ enableCaching: true });
      expect(result1.success).toBe(true);
      expect(result1.metadata?.fromCache).toBe(false);

      // Second load should use cache
      const result2 = await service.loadLatestMemberData({ enableCaching: true });
      expect(result2.success).toBe(true);
      expect(result2.metadata?.fromCache).toBe(true);

      // API should only be called once
      expect(mockApiService.get).toHaveBeenCalledTimes(1);
    });

    it('should clear cache when requested', async () => {
      // Load data first
      const mockParquetResponse = {
        success: true,
        data: {
          download_method: 'direct_content' as const,
          data: {
            content: btoa(JSON.stringify([{ voornaam: 'Jan' }])),
            filename: 'members.parquet',
            size: 1024
          }
        }
      };

      mockApiService.get.mockResolvedValue(mockParquetResponse);
      mockComputeCalculatedFieldsForArray.mockImplementation((data) => data as any);

      await service.loadLatestMemberData({ enableCaching: true });

      // Clear cache
      service.clearCache();

      // Next load should not use cache
      const result = await service.loadLatestMemberData({ enableCaching: true });
      expect(result.metadata?.fromCache).toBe(false);
      expect(mockApiService.get).toHaveBeenCalledTimes(2);
    });
  });
});
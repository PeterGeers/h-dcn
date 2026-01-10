/**
 * Performance tests for DataProcessingService
 * These tests ensure the service performs well with larger datasets
 */

import { DataProcessingService, FilterCriteria, SortCriteria } from '../DataProcessingService';
import { Member } from '../../types/index';

// Generate large test dataset
const generateLargeDataset = (size: number): Member[] => {
  const regions = ['Noord-Holland', 'Zuid-Holland', 'Gelderland', 'Utrecht', 'Noord-Brabant', 'Limburg'];
  const statuses = ['Actief', 'Inactief', 'Geschorst'];
  const memberships = ['Gewoon', 'Ere', 'Donateur', 'Jeugd'];
  
  return Array.from({ length: size }, (_, i) => ({
    id: `member-${i}`,
    voornaam: `Voornaam${i}`,
    achternaam: `Achternaam${i}`,
    korte_naam: `Voornaam${i} Achternaam${i}`,
    email: `member${i}@example.com`,
    regio: regions[i % regions.length],
    status: statuses[i % statuses.length],
    leeftijd: 20 + (i % 60), // Ages 20-79
    jaren_lid: 1 + (i % 50), // 1-50 years membership
    lidmaatschap: memberships[i % memberships.length],
    tijdstempel: new Date(2000 + (i % 24), (i % 12), (i % 28) + 1).toISOString(),
    postcode: `${1000 + (i % 9000)}AB`,
    woonplaats: `Stad${i % 100}`,
    straat: `Straat${i} ${i + 1}`,
    telefoon: `06${String(i).padStart(8, '0')}`,
    geboortedatum: new Date(1950 + (i % 50), (i % 12), (i % 28) + 1).toISOString()
  } as Member));
};

describe('DataProcessingService Performance Tests', () => {
  let service: DataProcessingService;
  let smallDataset: Member[];
  let mediumDataset: Member[];
  let largeDataset: Member[];

  beforeAll(() => {
    service = DataProcessingService.getInstance();
    smallDataset = generateLargeDataset(100);
    mediumDataset = generateLargeDataset(1000);
    largeDataset = generateLargeDataset(5000);
  });

  beforeEach(() => {
    service.clearCache();
  });

  describe('Filtering Performance', () => {
    test('should filter small dataset quickly (<10ms)', () => {
      const filters: FilterCriteria[] = [
        { field: 'status', operator: 'equals', value: 'Actief' },
        { field: 'leeftijd', operator: 'greaterThan', value: 30 }
      ];

      const startTime = performance.now();
      const result = service.processData(smallDataset, { filters });
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(10);
      expect(result.data.length).toBeGreaterThan(0);
      expect(result.processingTime).toBeLessThan(10);
    });

    test('should filter medium dataset efficiently (<50ms)', () => {
      const filters: FilterCriteria[] = [
        { field: 'status', operator: 'equals', value: 'Actief' },
        { field: 'regio', operator: 'in', value: ['Noord-Holland', 'Zuid-Holland'] },
        { field: 'jaren_lid', operator: 'greaterThan', value: 10 }
      ];

      const startTime = performance.now();
      const result = service.processData(mediumDataset, { filters });
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(50);
      expect(result.data.length).toBeGreaterThan(0);
      expect(result.processingTime).toBeLessThan(50);
    });

    test('should handle large dataset with reasonable performance (<200ms)', () => {
      const filters: FilterCriteria[] = [
        { field: 'status', operator: 'equals', value: 'Actief' },
        { field: 'leeftijd', operator: 'between', value: 25, secondValue: 65 }
      ];

      const startTime = performance.now();
      const result = service.processData(largeDataset, { filters });
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(200);
      expect(result.data.length).toBeGreaterThan(0);
      expect(result.processingTime).toBeLessThan(200);
    });
  });

  describe('Sorting Performance', () => {
    test('should sort medium dataset quickly (<30ms)', () => {
      const sorts: SortCriteria[] = [
        { field: 'achternaam', direction: 'asc' },
        { field: 'voornaam', direction: 'asc' }
      ];

      const startTime = performance.now();
      const result = service.processData(mediumDataset, { sorts });
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(30);
      expect(result.data).toHaveLength(mediumDataset.length);
      expect(result.processingTime).toBeLessThan(30);
    });

    test('should sort large dataset with acceptable performance (<100ms)', () => {
      const sorts: SortCriteria[] = [
        { field: 'regio', direction: 'asc' },
        { field: 'leeftijd', direction: 'desc' }
      ];

      const startTime = performance.now();
      const result = service.processData(largeDataset, { sorts });
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(100);
      expect(result.data).toHaveLength(largeDataset.length);
      expect(result.processingTime).toBeLessThan(100);
    });
  });

  describe('Search Performance', () => {
    test('should search medium dataset efficiently (<40ms)', () => {
      const search = {
        query: 'Voornaam1',
        options: {
          fields: ['voornaam', 'achternaam', 'korte_naam'],
          caseSensitive: false
        }
      };

      const startTime = performance.now();
      const result = service.processData(mediumDataset, { search });
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(40);
      expect(result.data.length).toBeGreaterThan(0);
      expect(result.processingTime).toBeLessThan(40);
    });

    test('should handle fuzzy search on large dataset (<150ms)', () => {
      const search = {
        query: 'Voornaam1',
        options: {
          fields: ['voornaam', 'achternaam'],
          fuzzy: true,
          threshold: 0.8
        }
      };

      const startTime = performance.now();
      const result = service.processData(largeDataset, { search });
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(150);
      expect(result.data.length).toBeGreaterThan(0);
      expect(result.processingTime).toBeLessThan(150);
    });
  });

  describe('Combined Operations Performance', () => {
    test('should handle complex operations on medium dataset (<80ms)', () => {
      const filters: FilterCriteria[] = [
        { field: 'status', operator: 'equals', value: 'Actief' },
        { field: 'leeftijd', operator: 'between', value: 25, secondValue: 55 }
      ];

      const sorts: SortCriteria[] = [
        { field: 'regio', direction: 'asc' },
        { field: 'jaren_lid', direction: 'desc' }
      ];

      const search = {
        query: 'Voornaam',
        options: {
          fields: ['voornaam', 'korte_naam'],
          caseSensitive: false
        }
      };

      const pagination = { page: 1, pageSize: 50 };

      const startTime = performance.now();
      const result = service.processData(mediumDataset, {
        filters,
        sorts,
        search,
        pagination
      });
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(80);
      expect(result.data.length).toBeLessThanOrEqual(50);
      expect(result.processingTime).toBeLessThan(80);
    });
  });

  describe('Aggregation Performance', () => {
    test('should calculate aggregations on large dataset efficiently (<100ms)', () => {
      const aggregations = [
        {
          field: 'leeftijd',
          operations: ['count', 'sum', 'average', 'min', 'max'] as ('count' | 'sum' | 'average' | 'min' | 'max')[]
        },
        {
          field: 'jaren_lid',
          operations: ['average', 'max'] as ('average' | 'max')[],
          groupByField: 'regio'
        }
      ];

      const startTime = performance.now();
      const result = service.processData(largeDataset, { aggregations });
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(100);
      expect(result.aggregations).toBeDefined();
      expect(result.aggregations!.leeftijd).toBeDefined();
      expect(result.aggregations!.jaren_lid).toBeDefined();
      expect(result.processingTime).toBeLessThan(100);
    });
  });

  describe('Caching Performance', () => {
    test('should significantly improve performance with caching', () => {
      const filters: FilterCriteria[] = [
        { field: 'status', operator: 'equals', value: 'Actief' }
      ];

      // First run (no cache)
      const result1 = service.processData(mediumDataset, { filters });
      const firstRunTime = result1.processingTime;

      // Second run (with cache)
      const result2 = service.processData(mediumDataset, { filters });
      const secondRunTime = result2.processingTime;

      // Cache should make it significantly faster
      expect(secondRunTime).toBeLessThan(firstRunTime * 0.5);
      expect(result1.data).toEqual(result2.data);
    });

    test('should handle cache eviction properly', () => {
      // Fill cache beyond limit
      for (let i = 0; i < 60; i++) {
        const filters: FilterCriteria[] = [
          { field: 'leeftijd', operator: 'equals', value: 20 + i }
        ];
        service.processData(smallDataset, { filters });
      }

      // Should still work after cache eviction
      const filters: FilterCriteria[] = [
        { field: 'status', operator: 'equals', value: 'Actief' }
      ];

      const result = service.processData(smallDataset, { filters });
      expect(result.data.length).toBeGreaterThan(0);
    });
  });

  describe('Memory Usage', () => {
    test('should not cause memory leaks with repeated operations', () => {
      const initialMemory = process.memoryUsage().heapUsed;

      // Perform many operations
      for (let i = 0; i < 100; i++) {
        const filters: FilterCriteria[] = [
          { field: 'leeftijd', operator: 'greaterThan', value: i % 50 }
        ];
        service.processData(mediumDataset, { filters });
      }

      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }

      const finalMemory = process.memoryUsage().heapUsed;
      const memoryIncrease = finalMemory - initialMemory;

      // Memory increase should be reasonable (less than 50MB)
      expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
    });
  });

  describe('Batch Processing', () => {
    test('should use batch processing for very large datasets', async () => {
      const veryLargeDataset = generateLargeDataset(10000);
      
      const filters: FilterCriteria[] = [
        { field: 'status', operator: 'equals', value: 'Actief' }
      ];

      const startTime = performance.now();
      const result = await service.processBatch(veryLargeDataset, { filters }, 1000);
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(500); // Should complete within 500ms
      expect(result.data.length).toBeGreaterThan(0);
      expect(result.totalCount).toBe(10000);
    });
  });
});
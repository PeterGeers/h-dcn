/**
 * Tests for DataProcessingService
 */

import { DataProcessingService, FilterCriteria, SortCriteria } from '../DataProcessingService';
import { Member } from '../../types/index';

// Mock member data for testing
const mockMembers: Member[] = [
  {
    id: '1',
    voornaam: 'Jan',
    achternaam: 'Jansen',
    korte_naam: 'Jan Jansen',
    email: 'jan@example.com',
    regio: 'Noord-Holland',
    status: 'Actief',
    leeftijd: 45,
    jaren_lid: 10,
    lidmaatschap: 'Gewoon',
    tijdstempel: '2014-01-15T00:00:00Z'
  } as Member,
  {
    id: '2',
    voornaam: 'Piet',
    achternaam: 'Pietersen',
    korte_naam: 'Piet Pietersen',
    email: 'piet@example.com',
    regio: 'Zuid-Holland',
    status: 'Actief',
    leeftijd: 52,
    jaren_lid: 25,
    lidmaatschap: 'Ere',
    tijdstempel: '1999-03-20T00:00:00Z'
  } as Member,
  {
    id: '3',
    voornaam: 'Marie',
    achternaam: 'de Vries',
    korte_naam: 'Marie de Vries',
    email: 'marie@example.com',
    regio: 'Noord-Holland',
    status: 'Inactief',
    leeftijd: 38,
    jaren_lid: 5,
    lidmaatschap: 'Gewoon',
    tijdstempel: '2019-06-10T00:00:00Z'
  } as Member,
  {
    id: '4',
    voornaam: 'Klaas',
    achternaam: 'Klaasen',
    korte_naam: 'Klaas Klaasen',
    email: 'klaas@example.com',
    regio: 'Gelderland',
    status: 'Actief',
    leeftijd: 29,
    jaren_lid: 3,
    lidmaatschap: 'Gewoon',
    tijdstempel: '2021-09-05T00:00:00Z'
  } as Member
];

describe('DataProcessingService', () => {
  let service: DataProcessingService;

  beforeEach(() => {
    service = DataProcessingService.getInstance();
    service.clearCache();
  });

  describe('Basic Filtering', () => {
    test('should filter by exact match', () => {
      const filters: FilterCriteria[] = [
        { field: 'status', operator: 'equals', value: 'Actief' }
      ];

      const result = service.processData(mockMembers, { filters });
      
      expect(result.data).toHaveLength(3);
      expect(result.filteredCount).toBe(3);
      expect(result.totalCount).toBe(4);
      expect(result.data.every(m => m.status === 'Actief')).toBe(true);
    });

    test('should filter by contains', () => {
      const filters: FilterCriteria[] = [
        { field: 'korte_naam', operator: 'contains', value: 'Jan' }
      ];

      const result = service.processData(mockMembers, { filters });
      
      expect(result.data).toHaveLength(1);
      expect(result.data[0].korte_naam).toBe('Jan Jansen');
    });

    test('should filter by numeric comparison', () => {
      const filters: FilterCriteria[] = [
        { field: 'leeftijd', operator: 'greaterThan', value: 40 }
      ];

      const result = service.processData(mockMembers, { filters });
      
      expect(result.data).toHaveLength(2);
      expect(result.data.every(m => m.leeftijd > 40)).toBe(true);
    });

    test('should filter by range (between)', () => {
      const filters: FilterCriteria[] = [
        { field: 'jaren_lid', operator: 'between', value: 5, secondValue: 15 }
      ];

      const result = service.processData(mockMembers, { filters });
      
      expect(result.data).toHaveLength(2);
      expect(result.data.every(m => m.jaren_lid >= 5 && m.jaren_lid <= 15)).toBe(true);
    });

    test('should filter by array inclusion', () => {
      const filters: FilterCriteria[] = [
        { field: 'regio', operator: 'in', value: ['Noord-Holland', 'Zuid-Holland'] }
      ];

      const result = service.processData(mockMembers, { filters });
      
      expect(result.data).toHaveLength(3);
      expect(result.data.every(m => ['Noord-Holland', 'Zuid-Holland'].includes(m.regio))).toBe(true);
    });
  });

  describe('Multiple Filters (AND logic)', () => {
    test('should apply multiple filters with AND logic', () => {
      const filters: FilterCriteria[] = [
        { field: 'status', operator: 'equals', value: 'Actief' },
        { field: 'regio', operator: 'equals', value: 'Noord-Holland' }
      ];

      const result = service.processData(mockMembers, { filters });
      
      expect(result.data).toHaveLength(1);
      expect(result.data[0].korte_naam).toBe('Jan Jansen');
    });
  });

  describe('Sorting', () => {
    test('should sort by single field ascending', () => {
      const sorts: SortCriteria[] = [
        { field: 'leeftijd', direction: 'asc' }
      ];

      const result = service.processData(mockMembers, { sorts });
      
      expect(result.data[0].leeftijd).toBe(29);
      expect(result.data[1].leeftijd).toBe(38);
      expect(result.data[2].leeftijd).toBe(45);
      expect(result.data[3].leeftijd).toBe(52);
    });

    test('should sort by single field descending', () => {
      const sorts: SortCriteria[] = [
        { field: 'jaren_lid', direction: 'desc' }
      ];

      const result = service.processData(mockMembers, { sorts });
      
      expect(result.data[0].jaren_lid).toBe(25);
      expect(result.data[1].jaren_lid).toBe(10);
      expect(result.data[2].jaren_lid).toBe(5);
      expect(result.data[3].jaren_lid).toBe(3);
    });

    test('should sort by multiple fields', () => {
      const sorts: SortCriteria[] = [
        { field: 'regio', direction: 'asc' },
        { field: 'leeftijd', direction: 'desc' }
      ];

      const result = service.processData(mockMembers, { sorts });
      
      // First by region, then by age descending within region
      expect(result.data[0].regio).toBe('Gelderland');
      expect(result.data[1].regio).toBe('Noord-Holland');
      expect(result.data[1].leeftijd).toBe(45); // Jan (45) before Marie (38)
      expect(result.data[2].leeftijd).toBe(38);
      expect(result.data[3].regio).toBe('Zuid-Holland');
    });
  });

  describe('Search Functionality', () => {
    test('should search across multiple fields', () => {
      const search = {
        query: 'Jan',
        options: {
          fields: ['voornaam', 'achternaam', 'korte_naam'],
          caseSensitive: false
        }
      };

      const result = service.processData(mockMembers, { search });
      
      expect(result.data).toHaveLength(1);
      expect(result.data[0].korte_naam).toBe('Jan Jansen');
    });

    test('should perform case-sensitive search', () => {
      const search = {
        query: 'jan',
        options: {
          fields: ['voornaam'],
          caseSensitive: true
        }
      };

      const result = service.processData(mockMembers, { search });
      
      expect(result.data).toHaveLength(0);
    });

    test('should perform fuzzy search', () => {
      const search = {
        query: 'Jansn', // Typo in "Jansen"
        options: {
          fields: ['achternaam'],
          fuzzy: true,
          threshold: 0.7
        }
      };

      const result = service.processData(mockMembers, { search });
      
      expect(result.data).toHaveLength(1);
      expect(result.data[0].achternaam).toBe('Jansen');
    });
  });

  describe('Pagination', () => {
    test('should paginate results', () => {
      const pagination = { page: 1, pageSize: 2 };

      const result = service.processData(mockMembers, { pagination });
      
      expect(result.data).toHaveLength(2);
      expect(result.totalCount).toBe(4);
      expect(result.filteredCount).toBe(4);
    });

    test('should paginate filtered results', () => {
      const filters: FilterCriteria[] = [
        { field: 'status', operator: 'equals', value: 'Actief' }
      ];
      const pagination = { page: 2, pageSize: 2 };

      const result = service.processData(mockMembers, { filters, pagination });
      
      expect(result.data).toHaveLength(1); // Only 1 item on page 2
      expect(result.totalCount).toBe(4);
      expect(result.filteredCount).toBe(3);
    });
  });

  describe('Aggregations', () => {
    test('should calculate basic aggregations', () => {
      const aggregations = [{
        field: 'leeftijd',
        operations: ['count', 'sum', 'average', 'min', 'max'] as ('count' | 'sum' | 'average' | 'min' | 'max')[]
      }];

      const result = service.processData(mockMembers, { aggregations });
      
      expect(result.aggregations?.leeftijd).toEqual({
        count: 4,
        sum: 164, // 45 + 52 + 38 + 29
        average: 41,
        min: 29,
        max: 52
      });
    });

    test('should calculate unique values', () => {
      const aggregations = [{
        field: 'regio',
        operations: ['unique'] as ('unique')[]
      }];

      const result = service.processData(mockMembers, { aggregations });
      
      expect(result.aggregations?.regio.unique).toEqual(
        expect.arrayContaining(['Noord-Holland', 'Zuid-Holland', 'Gelderland'])
      );
      expect(result.aggregations?.regio.unique).toHaveLength(3);
    });

    test('should group by field', () => {
      const aggregations = [{
        field: 'status',
        operations: ['groupBy'] as ('groupBy')[],
        groupByField: 'regio'
      }];

      const result = service.processData(mockMembers, { aggregations });
      
      expect(result.aggregations?.status.groupBy).toHaveProperty('Noord-Holland');
      expect(result.aggregations?.status.groupBy).toHaveProperty('Zuid-Holland');
      expect(result.aggregations?.status.groupBy).toHaveProperty('Gelderland');
    });
  });

  describe('Combined Operations', () => {
    test('should apply filters, sorting, and pagination together', () => {
      const filters: FilterCriteria[] = [
        { field: 'status', operator: 'equals', value: 'Actief' }
      ];
      const sorts: SortCriteria[] = [
        { field: 'leeftijd', direction: 'desc' }
      ];
      const pagination = { page: 1, pageSize: 2 };

      const result = service.processData(mockMembers, { filters, sorts, pagination });
      
      expect(result.data).toHaveLength(2);
      expect(result.data[0].leeftijd).toBe(52); // Piet (oldest active member)
      expect(result.data[1].leeftijd).toBe(45); // Jan (second oldest active member)
      expect(result.filteredCount).toBe(3); // Total active members
      expect(result.totalCount).toBe(4); // Total members
    });
  });

  describe('Field Statistics', () => {
    test('should calculate field statistics', () => {
      const stats = service.getFieldStatistics(mockMembers, 'leeftijd');
      
      expect(stats.count).toBe(4);
      expect(stats.uniqueCount).toBe(4);
      expect(stats.nullCount).toBe(0);
      expect(stats.numericStats).toEqual({
        min: 29,
        max: 52,
        average: 41,
        median: 41.5, // (38 + 45) / 2
        standardDeviation: expect.any(Number)
      });
    });

    test('should calculate distribution', () => {
      const stats = service.getFieldStatistics(mockMembers, 'regio');
      
      expect(stats.distribution).toEqual({
        'Noord-Holland': 2,
        'Zuid-Holland': 1,
        'Gelderland': 1
      });
    });
  });

  describe('Export Preparation', () => {
    test('should prepare data for export', () => {
      const columnMapping = {
        'korte_naam': 'Naam',
        'email': 'E-mail',
        'regio': 'Regio',
        'leeftijd': 'Leeftijd'
      };

      const exportData = service.prepareForExport(
        mockMembers.slice(0, 2),
        columnMapping,
        { includeHeaders: true }
      );
      
      expect(exportData[0]).toEqual(['Naam', 'E-mail', 'Regio', 'Leeftijd']);
      expect(exportData[1]).toEqual(['Jan Jansen', 'jan@example.com', 'Noord-Holland', '45']);
      expect(exportData[2]).toEqual(['Piet Pietersen', 'piet@example.com', 'Zuid-Holland', '52']);
    });
  });

  describe('Performance and Caching', () => {
    test('should cache results for identical queries', () => {
      const options = {
        filters: [{ field: 'status', operator: 'equals' as const, value: 'Actief' }]
      };

      const result1 = service.processData(mockMembers, options);
      const result2 = service.processData(mockMembers, options);
      
      // Second call should be faster due to caching
      expect(result2.processingTime).toBeLessThan(result1.processingTime);
      expect(result1.data).toEqual(result2.data);
    });

    test('should clear cache', () => {
      const options = {
        filters: [{ field: 'status', operator: 'equals' as const, value: 'Actief' }]
      };

      service.processData(mockMembers, options);
      service.clearCache();
      
      const result = service.processData(mockMembers, options);
      expect(result.processingTime).toBeGreaterThan(0);
    });
  });
});
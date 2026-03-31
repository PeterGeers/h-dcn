/**
 * Data Processing Service for H-DCN Member Reporting
 * 
 * This service provides comprehensive client-side data processing utilities including:
 * - Advanced filtering with multiple criteria and operators
 * - Multi-column sorting with custom sort functions
 * - Data aggregation and statistical analysis
 * - Search functionality with fuzzy matching
 * - Data transformation and export preparation
 * - Performance optimization for large datasets
 */

import { Member } from '../types/index';
import { webWorkerManager } from './WebWorkerManager';

export interface FilterCriteria {
  field: string;
  operator: 'equals' | 'contains' | 'startsWith' | 'endsWith' | 'greaterThan' | 'lessThan' | 'between' | 'in' | 'notIn' | 'isEmpty' | 'isNotEmpty';
  value: any;
  secondValue?: any; // For 'between' operator
}

export interface SortCriteria {
  field: string;
  direction: 'asc' | 'desc';
  customSortFn?: (a: any, b: any) => number;
}

export interface SearchOptions {
  fields: string[];
  fuzzy?: boolean;
  caseSensitive?: boolean;
  threshold?: number; // For fuzzy matching (0-1)
}

export interface AggregationResult {
  count: number;
  sum?: number;
  average?: number;
  min?: any;
  max?: any;
  unique?: any[];
  groupBy?: Record<string, any>;
}

export interface DataProcessingOptions {
  filters?: FilterCriteria[];
  sorts?: SortCriteria[];
  search?: {
    query: string;
    options: SearchOptions;
  };
  pagination?: {
    page: number;
    pageSize: number;
  };
  aggregations?: {
    field: string;
    operations: ('count' | 'sum' | 'average' | 'min' | 'max' | 'unique' | 'groupBy')[];
    groupByField?: string;
  }[];
}

export interface ProcessedDataResult {
  data: Member[];
  totalCount: number;
  filteredCount: number;
  aggregations?: Record<string, AggregationResult>;
  processingTime: number;
}

export class DataProcessingService {
  private static instance: DataProcessingService;
  private cache = new Map<string, ProcessedDataResult>();
  private cacheMaxSize = 50;

  public static getInstance(): DataProcessingService {
    if (!DataProcessingService.instance) {
      DataProcessingService.instance = new DataProcessingService();
    }
    return DataProcessingService.instance;
  }

  /**
   * Main processing method that applies all filters, sorts, search, and aggregations
   */
  public processData(
    data: Member[],
    options: DataProcessingOptions = {}
  ): ProcessedDataResult {
    const startTime = performance.now();
    const cacheKey = this.generateCacheKey(data, options);
    
    // Check cache first
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey)!;
      return {
        ...cached,
        processingTime: performance.now() - startTime
      };
    }

    let processedData = [...data];
    const originalCount = data.length;

    // Apply search first (most selective)
    if (options.search?.query) {
      processedData = this.applySearch(processedData, options.search.query, options.search.options);
    }

    // Apply filters
    if (options.filters?.length) {
      processedData = this.applyFilters(processedData, options.filters);
    }

    const filteredCount = processedData.length;

    // Apply sorting
    if (options.sorts?.length) {
      processedData = this.applySorting(processedData, options.sorts);
    }

    // Calculate aggregations before pagination
    const aggregations = options.aggregations?.length 
      ? this.calculateAggregations(processedData, options.aggregations)
      : undefined;

    // Apply pagination
    if (options.pagination) {
      const { page, pageSize } = options.pagination;
      const startIndex = (page - 1) * pageSize;
      processedData = processedData.slice(startIndex, startIndex + pageSize);
    }

    const result: ProcessedDataResult = {
      data: processedData,
      totalCount: originalCount,
      filteredCount,
      aggregations,
      processingTime: performance.now() - startTime
    };

    // Cache result
    this.cacheResult(cacheKey, result);

    return result;
  }

  /**
   * Apply multiple filters with AND logic
   * Optimized: pre-computes normalized filter values
   */
  public applyFilters(data: Member[], filters: FilterCriteria[]): Member[] {
    // Pre-compute normalized filter values to avoid repeated toLowerCase calls
    const normalizedFilters = filters.map(filter => ({
      ...filter,
      _normalizedValue: filter.value !== undefined && filter.value !== null 
        ? String(filter.value).toLowerCase() 
        : undefined,
      _normalizedSecondValue: filter.secondValue !== undefined && filter.secondValue !== null
        ? String(filter.secondValue).toLowerCase()
        : undefined
    }));

    return data.filter(item => {
      return normalizedFilters.every(filter => this.evaluateFilter(item, filter));
    });
  }

  /**
   * Evaluate a single filter against a data item
   * Uses pre-normalized values from normalizedFilters
   */
  private evaluateFilter(item: Member, filter: FilterCriteria & { _normalizedValue?: string; _normalizedSecondValue?: string }): boolean {
    const fieldValue = this.getNestedValue(item, filter.field);
    const { operator, value, secondValue, _normalizedValue, _normalizedSecondValue } = filter;

    switch (operator) {
      case 'equals':
        return fieldValue === value;
      
      case 'contains':
        return String(fieldValue).toLowerCase().includes(_normalizedValue!);
      
      case 'startsWith':
        return String(fieldValue).toLowerCase().startsWith(_normalizedValue!);
      
      case 'endsWith':
        return String(fieldValue).toLowerCase().endsWith(_normalizedValue!);
      
      case 'greaterThan':
        return this.compareValues(fieldValue, value) > 0;
      
      case 'lessThan':
        return this.compareValues(fieldValue, value) < 0;
      
      case 'between':
        const comparison1 = this.compareValues(fieldValue, value);
        const comparison2 = this.compareValues(fieldValue, secondValue);
        return comparison1 >= 0 && comparison2 <= 0;
      
      case 'in':
        return Array.isArray(value) && value.includes(fieldValue);
      
      case 'notIn':
        return Array.isArray(value) && !value.includes(fieldValue);
      
      case 'isEmpty':
        return fieldValue === null || fieldValue === undefined || fieldValue === '';
      
      case 'isNotEmpty':
        return fieldValue !== null && fieldValue !== undefined && fieldValue !== '';
      
      default:
        return true;
    }
  }

  /**
   * Apply multi-column sorting (modifies array in-place since caller makes defensive copy)
   */
  public applySorting(data: Member[], sorts: SortCriteria[]): Member[] {
    // Sort in-place - caller has already created defensive copy
    return data.sort((a, b) => {
      for (const sort of sorts) {
        let comparison: number;
        
        if (sort.customSortFn) {
          comparison = sort.customSortFn(
            this.getNestedValue(a, sort.field),
            this.getNestedValue(b, sort.field)
          );
        } else {
          comparison = this.compareValues(
            this.getNestedValue(a, sort.field),
            this.getNestedValue(b, sort.field)
          );
        }

        if (comparison !== 0) {
          return sort.direction === 'desc' ? -comparison : comparison;
        }
      }
      return 0;
    });
  }

  /**
   * Apply search with fuzzy matching support
   * Optimized: pre-normalizes query and uses explicit loop over some()
   */
  public applySearch(data: Member[], query: string, options: SearchOptions): Member[] {
    if (!query.trim()) return data;

    const normalizedQuery = options.caseSensitive ? query : query.toLowerCase();
    
    return data.filter(item => {
      return options.fields.some(field => {
        const fieldValue = this.getNestedValue(item, field);
        if (fieldValue === null || fieldValue === undefined) return false;
        
        const normalizedValue = options.caseSensitive 
          ? String(fieldValue) 
          : String(fieldValue).toLowerCase();

        if (options.fuzzy) {
          return this.fuzzyMatch(normalizedValue, normalizedQuery, options.threshold || 0.6);
        } else {
          return normalizedValue.includes(normalizedQuery);
        }
      });
    });
  }

  /**
   * Calculate aggregations on the dataset
   */
  public calculateAggregations(
    data: Member[], 
    aggregationConfigs: DataProcessingOptions['aggregations']
  ): Record<string, AggregationResult> {
    const results: Record<string, AggregationResult> = {};

    aggregationConfigs?.forEach(config => {
      const { field, operations, groupByField } = config;
      const values = data.map(item => this.getNestedValue(item, field)).filter(v => v !== null && v !== undefined);
      
      const result: AggregationResult = {
        count: values.length
      };

      if (operations.includes('sum') && values.every(v => typeof v === 'number')) {
        result.sum = values.reduce((sum, val) => sum + val, 0);
      }

      if (operations.includes('average') && values.every(v => typeof v === 'number')) {
        result.average = result.sum! / values.length;
      }

      if (operations.includes('min')) {
        result.min = Math.min(...values.filter(v => typeof v === 'number'));
      }

      if (operations.includes('max')) {
        result.max = Math.max(...values.filter(v => typeof v === 'number'));
      }

      if (operations.includes('unique')) {
        result.unique = [...new Set(values)];
      }

      if (operations.includes('groupBy') && groupByField) {
        const groups: Record<string, any> = {};
        data.forEach(item => {
          const groupKey = String(this.getNestedValue(item, groupByField));
          if (!groups[groupKey]) {
            groups[groupKey] = [];
          }
          groups[groupKey].push(this.getNestedValue(item, field));
        });
        
        result.groupBy = Object.entries(groups).reduce((acc, [key, groupValues]) => {
          acc[key] = {
            count: groupValues.length,
            values: groupValues
          };
          return acc;
        }, {} as Record<string, any>);
      }

      results[field] = result;
    });

    return results;
  }

  /**
   * Advanced filtering with complex conditions
   */
  public createAdvancedFilter(conditions: {
    logic: 'AND' | 'OR';
    groups: FilterCriteria[][];
  }): (item: Member) => boolean {
    return (item: Member) => {
      if (conditions.logic === 'AND') {
        return conditions.groups.every(group => 
          group.some(filter => this.evaluateFilter(item, filter))
        );
      } else {
        return conditions.groups.some(group => 
          group.every(filter => this.evaluateFilter(item, filter))
        );
      }
    };
  }

  /**
   * Get statistics for a specific field
   */
  public getFieldStatistics(data: Member[], field: string): {
    count: number;
    uniqueCount: number;
    nullCount: number;
    distribution: Record<string, number>;
    numericStats?: {
      min: number;
      max: number;
      average: number;
      median: number;
      standardDeviation: number;
    };
  } {
    const values = data.map(item => this.getNestedValue(item, field));
    const nonNullValues = values.filter(v => v !== null && v !== undefined);
    const numericValues = nonNullValues.filter(v => typeof v === 'number');
    
    const distribution: Record<string, number> = {};
    nonNullValues.forEach(value => {
      const key = String(value);
      distribution[key] = (distribution[key] || 0) + 1;
    });

    const result = {
      count: values.length,
      uniqueCount: new Set(nonNullValues).size,
      nullCount: values.length - nonNullValues.length,
      distribution
    };

    if (numericValues.length > 0) {
      const sorted = [...numericValues].sort((a, b) => a - b);
      const sum = numericValues.reduce((acc, val) => acc + val, 0);
      const average = sum / numericValues.length;
      
      const variance = numericValues.reduce((acc, val) => acc + Math.pow(val - average, 2), 0) / numericValues.length;
      const standardDeviation = Math.sqrt(variance);
      
      const median = sorted.length % 2 === 0
        ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
        : sorted[Math.floor(sorted.length / 2)];

      (result as any).numericStats = {
        min: Math.min(...numericValues),
        max: Math.max(...numericValues),
        average,
        median,
        standardDeviation
      };
    }

    return result;
  }

  /**
   * Export data preparation with column mapping
   */
  public prepareForExport(
    data: Member[],
    columnMapping: Record<string, string>,
    options: {
      includeHeaders?: boolean;
      dateFormat?: string;
      numberFormat?: string;
    } = {}
  ): any[][] {
    const headers = options.includeHeaders 
      ? [Object.values(columnMapping)]
      : [];

    const rows = data.map(item => {
      return Object.keys(columnMapping).map(field => {
        const value = this.getNestedValue(item, field);
        return this.formatValueForExport(value, options);
      });
    });

    return [...headers, ...rows];
  }

  /**
   * Utility methods
   */
  private getNestedValue(obj: any, path: string): any {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  }

  private compareValues(a: any, b: any): number {
    if (a === null || a === undefined) return b === null || b === undefined ? 0 : -1;
    if (b === null || b === undefined) return 1;
    
    if (typeof a === 'number' && typeof b === 'number') {
      return a - b;
    }
    
    if (a instanceof Date && b instanceof Date) {
      return a.getTime() - b.getTime();
    }
    
    return String(a).localeCompare(String(b));
  }

  private fuzzyMatch(text: string, pattern: string, threshold: number): boolean {
    if (text === pattern) return true;
    if (pattern.length === 0) return true;
    if (text.length === 0) return false;

    // Use optimized version with early termination for threshold < 1
    if (threshold < 1.0) {
      return this.fuzzyMatchOptimized(text, pattern, threshold);
    }

    // For exact match (threshold = 1), use simple comparison
    return text === pattern;
  }

  private levenshteinDistance(str1: string, str2: string): number {
    // Ensure str1 is the shorter string for space optimization
    if (str1.length > str2.length) {
      [str1, str2] = [str2, str1];
    }
    
    const len1 = str1.length;
    const len2 = str2.length;
    
    // Edge cases
    if (len1 === 0) return len2;
    if (len2 === 0) return len1;
    
    // Use only two rows instead of full matrix - O(min(n,m)) space
    let prevRow = new Array(len1 + 1);
    let currRow = new Array(len1 + 1);
    
    // Initialize first row
    for (let i = 0; i <= len1; i++) {
      prevRow[i] = i;
    }
    
    // Fill the matrix row by row
    for (let j = 1; j <= len2; j++) {
      currRow[0] = j;
      
      for (let i = 1; i <= len1; i++) {
        const cost = str1[i - 1] === str2[j - 1] ? 0 : 1;
        currRow[i] = Math.min(
          prevRow[i] + 1,      // deletion
          currRow[i - 1] + 1,  // insertion
          prevRow[i - 1] + cost // substitution
        );
      }
      
      // Swap rows for next iteration
      [prevRow, currRow] = [currRow, prevRow];
    }
    
    return prevRow[len1];
  }
  
  /**
   * Optimized fuzzy match with early termination
   */
  private fuzzyMatchOptimized(text: string, pattern: string, threshold: number): boolean {
    if (text === pattern) return true;
    if (pattern.length === 0) return true;
    if (text.length === 0) return false;
    
    // Quick reject: if length difference is too large, impossible to match
    const maxLength = Math.max(text.length, pattern.length);
    const minLength = Math.min(text.length, pattern.length);
    const maxAllowedDistance = Math.floor((1 - threshold) * maxLength);
    
    if (maxLength - minLength > maxAllowedDistance) {
      return false;
    }
    
    // Use optimized Levenshtein with early termination
    const distance = this.levenshteinDistanceEarly(text, pattern, maxAllowedDistance);
    const similarity = 1 - (distance / maxLength);
    
    return similarity >= threshold;
  }
  
  private levenshteinDistanceEarly(str1: string, str2: string, maxDistance: number): number {
    // Ensure str1 is shorter
    if (str1.length > str2.length) {
      [str1, str2] = [str2, str1];
    }
    
    const len1 = str1.length;
    const len2 = str2.length;
    
    if (len1 === 0) return len2;
    if (len2 === 0) return len1;
    
    // If impossible to be within maxDistance, return early
    if (len2 - len1 > maxDistance) {
      return maxDistance + 1;
    }
    
    // Use two rows with early termination check
    let prevRow = new Array(len1 + 1);
    let currRow = new Array(len1 + 1);
    
    for (let i = 0; i <= len1; i++) {
      prevRow[i] = i;
    }
    
    for (let j = 1; j <= len2; j++) {
      currRow[0] = j;
      let minInRow = j;
      
      for (let i = 1; i <= len1; i++) {
        const cost = str1[i - 1] === str2[j - 1] ? 0 : 1;
        currRow[i] = Math.min(
          prevRow[i] + 1,
          currRow[i - 1] + 1,
          prevRow[i - 1] + cost
        );
        minInRow = Math.min(minInRow, currRow[i]);
      }
      
      // Early termination: if minimum in row exceeds maxDistance, give up
      if (minInRow > maxDistance) {
        return maxDistance + 1;
      }
      
      [prevRow, currRow] = [currRow, prevRow];
    }
    
    return prevRow[len1];
  }

  private formatValueForExport(value: any, options: any): string {
    if (value === null || value === undefined) return '';
    
    if (value instanceof Date) {
      return options.dateFormat 
        ? value.toLocaleDateString('nl-NL')
        : value.toISOString();
    }
    
    if (typeof value === 'number') {
      return options.numberFormat 
        ? value.toLocaleString('nl-NL')
        : String(value);
    }
    
    return String(value);
  }

  private generateCacheKey(data: Member[], options: DataProcessingOptions): string {
    const dataHash = data.length + '_' + (data[0]?.id || '');
    const optionsHash = JSON.stringify(options);
    return `${dataHash}_${btoa(optionsHash).slice(0, 20)}`;
  }

  private cacheResult(key: string, result: ProcessedDataResult): void {
    if (this.cache.size >= this.cacheMaxSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    this.cache.set(key, result);
  }

  /**
   * Clear cache
   */
  public clearCache(): void {
    this.cache.clear();
  }

  /**
   * Batch processing for large datasets with Web Worker support
   */
  public async processBatch(
    data: Member[],
    options: DataProcessingOptions,
    batchSize: number = 1000,
    useWebWorkers: boolean = true
  ): Promise<ProcessedDataResult> {
    // For small datasets, use regular processing
    if (data.length <= batchSize) {
      return this.processData(data, options);
    }

    // Try to use Web Workers for large datasets
    if (useWebWorkers && webWorkerManager.isAvailable() && data.length > 500) {
      try {
        // For now, we'll use the existing batch processing approach
        // In the future, we could extend the Web Worker to handle complex filtering and sorting
        console.log(`[DataProcessingService] Processing large dataset (${data.length} records) with Web Workers not yet implemented for complex operations, falling back to batch processing`);
      } catch (error) {
        console.error('[DataProcessingService] Web Worker processing failed, falling back to batch processing', error);
      }
    }

    // Fallback to existing batch processing
    const batches: Member[][] = [];
    for (let i = 0; i < data.length; i += batchSize) {
      batches.push(data.slice(i, i + batchSize));
    }

    const results = await Promise.all(
      batches.map(batch => 
        new Promise<Member[]>(resolve => {
          setTimeout(() => {
            resolve(this.processData(batch, { ...options, pagination: undefined }).data);
          }, 0);
        })
      )
    );

    const combinedData = results.flat();
    
    // Apply pagination to combined results
    let finalData = combinedData;
    if (options.pagination) {
      const { page, pageSize } = options.pagination;
      const startIndex = (page - 1) * pageSize;
      finalData = combinedData.slice(startIndex, startIndex + pageSize);
    }

    return {
      data: finalData,
      totalCount: data.length,
      filteredCount: combinedData.length,
      processingTime: 0 // Batch processing time not tracked
    };
  }
}
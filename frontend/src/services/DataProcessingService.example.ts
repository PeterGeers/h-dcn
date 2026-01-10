/**
 * DataProcessingService Usage Examples
 * 
 * This file demonstrates how to use the DataProcessingService
 * in various member reporting scenarios.
 */

import { DataProcessingService, FilterCriteria, SortCriteria } from './DataProcessingService';
import { Member } from '../types/index';

// Example: Regional Address Labels Export
export const createRegionalAddressLabels = (
  members: Member[],
  userRegion: string
) => {
  const service = DataProcessingService.getInstance();
  
  const filters: FilterCriteria[] = [
    { field: 'status', operator: 'equals', value: 'Actief' },
    { field: 'regio', operator: 'equals', value: userRegion },
    { field: 'straat', operator: 'isNotEmpty', value: null } // Has address
  ];

  const sorts: SortCriteria[] = [
    { field: 'postcode', direction: 'asc' },
    { field: 'achternaam', direction: 'asc' }
  ];

  const result = service.processData(members, { filters, sorts });
  
  // Prepare for export with specific columns
  const columnMapping = {
    'korte_naam': 'Naam',
    'straat': 'Straat',
    'postcode': 'Postcode',
    'woonplaats': 'Woonplaats',
    'land': 'Land'
  };

  return service.prepareForExport(result.data, columnMapping, {
    includeHeaders: true,
    dateFormat: 'nl-NL'
  });
};

// Example: Birthday List for Current Month
export const createBirthdayList = (
  members: Member[],
  month: number,
  year: number
) => {
  const service = DataProcessingService.getInstance();
  
  // Custom filter function for birthday month
  const birthdayFilter = (member: Member): boolean => {
    if (!member.geboortedatum) return false;
    const birthDate = new Date(member.geboortedatum);
    return birthDate.getMonth() === month - 1; // JavaScript months are 0-based
  };

  // Apply basic filters first
  const filters: FilterCriteria[] = [
    { field: 'status', operator: 'equals', value: 'Actief' },
    { field: 'geboortedatum', operator: 'isNotEmpty', value: null }
  ];

  let result = service.processData(members, { filters });
  
  // Apply custom birthday filter
  const birthdayMembers = result.data.filter(birthdayFilter);
  
  // Sort by birthday day
  const sorts: SortCriteria[] = [{
    field: 'geboortedatum',
    direction: 'asc',
    customSortFn: (a: string, b: string) => {
      const dayA = new Date(a).getDate();
      const dayB = new Date(b).getDate();
      return dayA - dayB;
    }
  }];

  return service.applySorting(birthdayMembers, sorts);
};

// Example: ALV Certificate Eligibility
export const getALVCertificateEligible = (
  members: Member[],
  alvYear: number
) => {
  const service = DataProcessingService.getInstance();
  
  const filters: FilterCriteria[] = [
    { field: 'status', operator: 'equals', value: 'Actief' },
    { field: 'jaren_lid', operator: 'greaterThan', value: 24 } // 25+ years
  ];

  const result = service.processData(members, { filters });
  
  // Group by milestone years
  const milestoneGroups: Record<string, Member[]> = {};
  
  result.data.forEach(member => {
    const years = member.jaren_lid;
    let milestone: string;
    
    if (years >= 50) milestone = '50+';
    else if (years >= 45) milestone = '45';
    else if (years >= 40) milestone = '40';
    else if (years >= 35) milestone = '35';
    else if (years >= 30) milestone = '30';
    else milestone = '25';
    
    if (!milestoneGroups[milestone]) {
      milestoneGroups[milestone] = [];
    }
    milestoneGroups[milestone].push(member);
  });

  return milestoneGroups;
};

// Example: Regional Statistics Dashboard
export const getRegionalStatistics = (members: Member[]) => {
  const service = DataProcessingService.getInstance();
  
  const aggregations = [
    {
      field: 'leeftijd',
      operations: ['count', 'average', 'min', 'max'] as ('count' | 'average' | 'min' | 'max')[],
      groupByField: 'regio'
    },
    {
      field: 'jaren_lid',
      operations: ['average', 'max'] as ('average' | 'max')[],
      groupByField: 'regio'
    },
    {
      field: 'status',
      operations: ['groupBy'] as ('groupBy')[],
      groupByField: 'regio'
    }
  ];

  const result = service.processData(members, { aggregations });
  
  return result.aggregations;
};

// Example: Advanced Member Search
export const searchMembers = (
  members: Member[],
  searchQuery: string,
  searchOptions: {
    includeInactive?: boolean;
    regions?: string[];
    membershipTypes?: string[];
    fuzzySearch?: boolean;
  } = {}
) => {
  const service = DataProcessingService.getInstance();
  
  const filters: FilterCriteria[] = [];
  
  // Status filter
  if (!searchOptions.includeInactive) {
    filters.push({ field: 'status', operator: 'equals', value: 'Actief' });
  }
  
  // Region filter
  if (searchOptions.regions?.length) {
    filters.push({ field: 'regio', operator: 'in', value: searchOptions.regions });
  }
  
  // Membership type filter
  if (searchOptions.membershipTypes?.length) {
    filters.push({ field: 'lidmaatschap', operator: 'in', value: searchOptions.membershipTypes });
  }

  const search = {
    query: searchQuery,
    options: {
      fields: ['voornaam', 'achternaam', 'korte_naam', 'email', 'telefoon'],
      fuzzy: searchOptions.fuzzySearch || false,
      caseSensitive: false,
      threshold: 0.7
    }
  };

  return service.processData(members, { filters, search });
};

// Example: Export Configuration for Different Views
export const EXPORT_CONFIGURATIONS = {
  addressStickers: {
    name: 'Address Stickers',
    filters: [
      { field: 'status', operator: 'equals', value: 'Actief' },
      { field: 'straat', operator: 'isNotEmpty', value: null }
    ] as FilterCriteria[],
    sorts: [
      { field: 'postcode', direction: 'asc' },
      { field: 'achternaam', direction: 'asc' }
    ] as SortCriteria[],
    columns: {
      'korte_naam': 'Naam',
      'straat': 'Straat',
      'postcode': 'Postcode',
      'woonplaats': 'Woonplaats',
      'land': 'Land'
    }
  },
  
  emailList: {
    name: 'Email List',
    filters: [
      { field: 'status', operator: 'equals', value: 'Actief' },
      { field: 'email', operator: 'isNotEmpty', value: null }
    ] as FilterCriteria[],
    sorts: [
      { field: 'achternaam', direction: 'asc' },
      { field: 'voornaam', direction: 'asc' }
    ] as SortCriteria[],
    columns: {
      'korte_naam': 'Naam',
      'email': 'E-mail'
    }
  },
  
  memberOverview: {
    name: 'Member Overview',
    filters: [
      { field: 'status', operator: 'equals', value: 'Actief' }
    ] as FilterCriteria[],
    sorts: [
      { field: 'achternaam', direction: 'asc' },
      { field: 'voornaam', direction: 'asc' }
    ] as SortCriteria[],
    columns: {
      'korte_naam': 'Naam',
      'email': 'E-mail',
      'telefoon': 'Telefoon',
      'regio': 'Regio',
      'lidmaatschap': 'Lidmaatschap',
      'leeftijd': 'Leeftijd',
      'jaren_lid': 'Jaren Lid'
    }
  }
};

// Example: React Hook Integration
export const useProcessedMemberData = (
  members: Member[],
  viewConfig: keyof typeof EXPORT_CONFIGURATIONS,
  additionalFilters: FilterCriteria[] = [],
  searchQuery: string = ''
) => {
  const service = DataProcessingService.getInstance();
  const config = EXPORT_CONFIGURATIONS[viewConfig];
  
  const filters = [...config.filters, ...additionalFilters];
  const search = searchQuery ? {
    query: searchQuery,
    options: {
      fields: ['voornaam', 'achternaam', 'korte_naam', 'email'],
      caseSensitive: false
    }
  } : undefined;

  return service.processData(members, {
    filters,
    sorts: config.sorts,
    search
  });
};

// Example: Performance Monitoring
export const processLargeDataset = async (
  members: Member[],
  options: any
) => {
  const service = DataProcessingService.getInstance();
  
  console.time('DataProcessing');
  
  let result;
  if (members.length > 5000) {
    // Use batch processing for very large datasets
    result = await service.processBatch(members, options, 1000);
  } else {
    result = service.processData(members, options);
  }
  
  console.timeEnd('DataProcessing');
  console.log(`Processed ${result.totalCount} members in ${result.processingTime}ms`);
  console.log(`Filtered to ${result.filteredCount} members`);
  
  return result;
};
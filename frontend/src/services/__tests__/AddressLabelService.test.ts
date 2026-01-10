/**
 * Address Label Service Tests
 * 
 * Tests for the address label generation functionality
 */

import { AddressLabelService, STANDARD_LABEL_FORMATS, DEFAULT_LABEL_STYLE } from '../AddressLabelService';
import { Member } from '../../types/index';

// Mock jsPDF
jest.mock('jspdf', () => {
  const mockDoc = {
    setFontSize: jest.fn(),
    setFont: jest.fn(),
    setLineWidth: jest.fn(),
    rect: jest.fn(),
    text: jest.fn(),
    addPage: jest.fn(),
    save: jest.fn(),
  };
  
  return {
    __esModule: true,
    default: jest.fn(() => mockDoc),
  };
});

describe('AddressLabelService', () => {
  let service: AddressLabelService;
  let mockMembers: Member[];

  beforeEach(() => {
    service = AddressLabelService.getInstance();
    
    mockMembers = [
      {
        member_id: '1',
        korte_naam: 'Jan van der Berg',
        straat: 'Hoofdstraat 123',
        postcode: '1234AB',
        woonplaats: 'Amsterdam',
        land: 'Nederland',
        regio: 'Noord-Holland',
        status: 'Actief',
        clubblad: 'Papier'
      } as Member,
      {
        member_id: '2',
        korte_naam: 'Marie Dubois',
        straat: 'Rue de la Paix 45',
        postcode: '75001',
        woonplaats: 'Paris',
        land: 'Frankrijk',
        regio: 'Overig',
        status: 'Actief',
        clubblad: 'Digitaal'
      } as Member,
      {
        member_id: '3',
        korte_naam: 'Incomplete Member',
        straat: '',
        postcode: '',
        woonplaats: '',
        land: 'Nederland',
        regio: 'Utrecht',
        status: 'Actief',
        clubblad: 'Papier'
      } as Member
    ];
  });

  describe('isValidAddress', () => {
    it('should return true for complete address', () => {
      const result = service.isValidAddress(mockMembers[0]);
      expect(result).toBe(true);
    });

    it('should return false for incomplete address', () => {
      const result = service.isValidAddress(mockMembers[2]);
      expect(result).toBe(false);
    });
  });

  describe('formatAddress', () => {
    it('should format Dutch address correctly', () => {
      const result = service.formatAddress(mockMembers[0], false);
      expect(result).toEqual([
        'Jan van der Berg',
        'Hoofdstraat 123',
        '1234AB  Amsterdam'
      ]);
    });

    it('should format foreign address with country', () => {
      const result = service.formatAddress(mockMembers[1], true);
      expect(result).toEqual([
        'Marie Dubois',
        'Rue de la Paix 45',
        '75001  Paris',
        'FRANKRIJK'
      ]);
    });

    it('should not include country for Netherlands when includeCountry is true', () => {
      const result = service.formatAddress(mockMembers[0], true);
      expect(result).toEqual([
        'Jan van der Berg',
        'Hoofdstraat 123',
        '1234AB  Amsterdam'
      ]);
    });
  });

  describe('processMembers', () => {
    it('should filter out invalid addresses', () => {
      const result = service.processMembers(mockMembers, {});
      expect(result).toHaveLength(2);
      expect(result.map(m => m.member_id)).toEqual(['1', '2']);
    });

    it('should filter by country', () => {
      const result = service.processMembers(mockMembers, {
        countryFilter: 'Frankrijk'
      });
      expect(result).toHaveLength(1);
      expect(result[0].member_id).toBe('2');
    });

    it('should sort by name', () => {
      const result = service.processMembers(mockMembers, {
        sortBy: 'name'
      });
      expect(result[0].korte_naam).toBe('Jan van der Berg');
      expect(result[1].korte_naam).toBe('Marie Dubois');
    });

    it('should sort by postcode', () => {
      const result = service.processMembers(mockMembers, {
        sortBy: 'postcode'
      });
      expect(result[0].postcode).toBe('1234AB');
      expect(result[1].postcode).toBe('75001');
    });
  });

  describe('getAvailableCountries', () => {
    it('should return unique countries sorted', () => {
      const result = service.getAvailableCountries(mockMembers);
      expect(result).toEqual(['Frankrijk', 'Nederland']);
    });
  });

  describe('calculatePageCount', () => {
    it('should calculate correct page count', () => {
      const format = STANDARD_LABEL_FORMATS[0]; // 21 labels per page
      const result = service.calculatePageCount(25, format, 0);
      expect(result).toBe(2); // 25 labels = 2 pages
    });

    it('should account for start position', () => {
      const format = STANDARD_LABEL_FORMATS[0]; // 21 labels per page
      const result = service.calculatePageCount(20, format, 5);
      expect(result).toBe(2); // 20 labels + 5 start position = 25 total = 2 pages
    });
  });

  describe('validateOptions', () => {
    it('should return no errors for valid options', () => {
      const options = {
        format: STANDARD_LABEL_FORMATS[0],
        style: DEFAULT_LABEL_STYLE,
        includeCountry: false,
        countryFilter: 'all',
        sortBy: 'name' as const,
        startPosition: 0
      };
      
      const errors = service.validateOptions(options);
      expect(errors).toHaveLength(0);
    });

    it('should return error for missing format', () => {
      const options = {
        format: undefined as any,
        style: DEFAULT_LABEL_STYLE,
        includeCountry: false,
        countryFilter: 'all',
        sortBy: 'name' as const,
        startPosition: 0
      };
      
      const errors = service.validateOptions(options);
      expect(errors).toContain('Label format is required');
    });

    it('should return error for invalid font size', () => {
      const options = {
        format: STANDARD_LABEL_FORMATS[0],
        style: { ...DEFAULT_LABEL_STYLE, fontSize: 3 },
        includeCountry: false,
        countryFilter: 'all',
        sortBy: 'name' as const,
        startPosition: 0
      };
      
      const errors = service.validateOptions(options);
      expect(errors).toContain('Font size must be at least 6pt');
    });

    it('should return error for invalid start position', () => {
      const options = {
        format: STANDARD_LABEL_FORMATS[0],
        style: DEFAULT_LABEL_STYLE,
        includeCountry: false,
        countryFilter: 'all',
        sortBy: 'name' as const,
        startPosition: 25 // More than labels per page (21)
      };
      
      const errors = service.validateOptions(options);
      expect(errors).toContain('Start position exceeds labels per page');
    });
  });

  describe('generatePreviewData', () => {
    it('should generate preview data with address lines', () => {
      const result = service.generatePreviewData(mockMembers, {}, 5);
      expect(result).toHaveLength(2); // Only valid addresses
      expect(result[0].member).toBe(mockMembers[0]);
      expect(result[0].addressLines).toEqual([
        'Jan van der Berg',
        'Hoofdstraat 123',
        '1234AB  Amsterdam'
      ]);
    });

    it('should limit preview data to maxLabels', () => {
      const result = service.generatePreviewData(mockMembers, {}, 1);
      expect(result).toHaveLength(1);
    });
  });

  describe('exportToCSV', () => {
    it('should export valid addresses to CSV', () => {
      const result = service.exportToCSV(mockMembers, {});
      const lines = result.split('\n');
      
      expect(lines[0]).toBe('Naam,Straat,Postcode,Woonplaats,Regio');
      expect(lines[1]).toBe('Jan van der Berg,Hoofdstraat 123,1234AB,Amsterdam,Noord-Holland');
      expect(lines[2]).toBe('Marie Dubois,Rue de la Paix 45,75001,Paris,Overig');
      expect(lines).toHaveLength(3); // Header + 2 valid members
    });

    it('should include country when requested', () => {
      const result = service.exportToCSV(mockMembers, { includeCountry: true });
      const lines = result.split('\n');
      
      expect(lines[0]).toBe('Naam,Straat,Postcode,Woonplaats,Land,Regio');
      expect(lines[1]).toBe('Jan van der Berg,Hoofdstraat 123,1234AB,Amsterdam,Nederland,Noord-Holland');
      expect(lines[2]).toBe('Marie Dubois,Rue de la Paix 45,75001,Paris,Frankrijk,Overig');
    });
  });

  describe('getAvailableFormats', () => {
    it('should return all standard formats', () => {
      const result = service.getAvailableFormats();
      expect(result).toBe(STANDARD_LABEL_FORMATS);
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe('getFormatById', () => {
    it('should return format by ID', () => {
      const result = service.getFormatById('avery-l7160');
      expect(result).toBeDefined();
      expect(result?.name).toBe('Avery L7160 (21 labels)');
    });

    it('should return undefined for invalid ID', () => {
      const result = service.getFormatById('invalid-id');
      expect(result).toBeUndefined();
    });
  });
});
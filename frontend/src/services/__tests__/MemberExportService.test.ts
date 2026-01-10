/**
 * Tests for MemberExportService
 * 
 * These tests verify the core functionality of exporting member data
 * to various formats (CSV, XLSX, PDF, TXT) using different export views
 * and configurations.
 */

import { MemberExportService, EXPORT_VIEWS } from '../MemberExportService';
import { Member } from '../../types/index';

// Mock the config and utils modules
jest.mock('../../config/memberFields', () => ({
  MEMBER_TABLE_CONTEXTS: {
    memberOverview: {
      name: 'Member Overview',
      columns: [
        { fieldKey: 'korte_naam', visible: true, order: 1 },
        { fieldKey: 'email', visible: true, order: 2 },
        { fieldKey: 'status', visible: true, order: 3 }
      ]
    }
  },
  MEMBER_FIELDS: {
    korte_naam: { label: 'Name', displayFormat: 'text' },
    email: { label: 'Email', displayFormat: 'text' },
    status: { label: 'Status', displayFormat: 'text' }
  }
}));

jest.mock('../../utils/fieldRenderers', () => ({
  renderFieldValue: jest.fn((value, field) => value?.toString() || '')
}));

// Mock the external dependencies
jest.mock('xlsx', () => ({
  utils: {
    book_new: jest.fn(() => ({ SheetNames: [], Sheets: {} })),
    aoa_to_sheet: jest.fn(() => ({ '!ref': 'A1:C3' })),
    book_append_sheet: jest.fn(),
    decode_range: jest.fn(() => ({ s: { r: 0, c: 0 }, e: { r: 2, c: 2 } })),
    encode_cell: jest.fn((cell) => `${String.fromCharCode(65 + cell.c)}${cell.r + 1}`)
  },
  write: jest.fn(() => new ArrayBuffer(100))
}));

jest.mock('jspdf', () => {
  const mockDoc = {
    setFontSize: jest.fn(),
    text: jest.fn(),
    save: jest.fn(),
    autoTable: jest.fn()
  };
  return jest.fn().mockImplementation(() => mockDoc);
});

jest.mock('jspdf-autotable', () => ({}));

// Mock DOM methods for file download
Object.defineProperty(window, 'URL', {
  value: {
    createObjectURL: jest.fn(() => 'mock-url'),
    revokeObjectURL: jest.fn()
  },
  writable: true
});

// Mock document.createElement to return a proper mock element
const mockElement = {
  href: '',
  download: '',
  style: { visibility: '' },
  click: jest.fn(),
  setAttribute: jest.fn()
};

Object.defineProperty(document, 'createElement', {
  value: jest.fn(() => mockElement),
  writable: true
});

Object.defineProperty(document.body, 'appendChild', {
  value: jest.fn(),
  writable: true
});

Object.defineProperty(document.body, 'removeChild', {
  value: jest.fn(),
  writable: true
});

describe('MemberExportService', () => {
  let service: MemberExportService;
  let mockMembers: Member[];

  beforeEach(() => {
    service = MemberExportService.getInstance();
    
    // Create mock member data
    mockMembers = [
      {
        member_id: '1',
        korte_naam: 'Jan van der Berg',
        voornaam: 'Jan',
        tussenvoegsel: 'van der',
        achternaam: 'Berg',
        email: 'jan@example.com',
        telefoon: '06-12345678',
        straat: 'Hoofdstraat 123',
        postcode: '1234AB',
        woonplaats: 'Amsterdam',
        land: 'Nederland',
        regio: 'Noord-Holland',
        status: 'Actief',
        lidmaatschap: 'Gewoon lid',
        clubblad: 'Digitaal',
        nieuwsbrief: 'Ja',
        privacy: 'Ja',
        verjaardag: 'maart 15',
        leeftijd: 45,
        jaren_lid: 5,
        aanmeldingsjaar: 2018
      } as Member,
      {
        member_id: '2',
        korte_naam: 'Marie de Vries',
        voornaam: 'Marie',
        tussenvoegsel: 'de',
        achternaam: 'Vries',
        email: 'marie@example.com',
        telefoon: '06-87654321',
        straat: 'Kerkstraat 456',
        postcode: '5678CD',
        woonplaats: 'Utrecht',
        land: 'Nederland',
        regio: 'Utrecht',
        status: 'Actief',
        lidmaatschap: 'Gezins lid',
        clubblad: 'Papier',
        nieuwsbrief: 'Nee',
        privacy: 'Ja',
        verjaardag: 'september 22',
        leeftijd: 38,
        jaren_lid: 3,
        aanmeldingsjaar: 2020
      } as Member,
      {
        member_id: '3',
        korte_naam: 'Peter Jansen',
        voornaam: 'Peter',
        tussenvoegsel: '',
        achternaam: 'Jansen',
        email: 'peter@example.com',
        telefoon: '06-11223344',
        straat: 'Dorpsstraat 789',
        postcode: '9012EF',
        woonplaats: 'Groningen',
        land: 'Nederland',
        regio: 'Groningen/Drenthe',
        status: 'Opgezegd',
        lidmaatschap: 'Donateur',
        clubblad: 'Geen',
        nieuwsbrief: 'Ja',
        privacy: 'Nee',
        verjaardag: 'december 3',
        leeftijd: 52,
        jaren_lid: 8,
        aanmeldingsjaar: 2015
      } as Member
    ];

    // Clear all mocks
    jest.clearAllMocks();
  });

  describe('Singleton Pattern', () => {
    it('should return the same instance', () => {
      const instance1 = MemberExportService.getInstance();
      const instance2 = MemberExportService.getInstance();
      expect(instance1).toBe(instance2);
    });
  });

  describe('Export Views Configuration', () => {
    it('should have predefined export views', () => {
      expect(EXPORT_VIEWS).toBeDefined();
      expect(Object.keys(EXPORT_VIEWS).length).toBeGreaterThan(0);
    });

    it('should have valid export view configurations', () => {
      Object.values(EXPORT_VIEWS).forEach(view => {
        expect(view.name).toBeDefined();
        expect(view.description).toBeDefined();
        expect(view.defaultFormat).toBeDefined();
        expect(view.permissions).toBeDefined();
        expect(view.permissions.view).toBeInstanceOf(Array);
        expect(view.permissions.export).toBeInstanceOf(Array);
      });
    });
  });

  describe('Permission Checking', () => {
    it('should check export permissions correctly', () => {
      const userRoles = ['Members_CRUD'];
      const canExport = service.canExportView('addressStickersPaper', userRoles);
      expect(canExport).toBe(true);
    });

    it('should deny export for insufficient permissions', () => {
      const userRoles = ['Members_Read'];
      const canExport = service.canExportView('addressStickersPaper', userRoles);
      expect(canExport).toBe(false);
    });

    it('should get available views for user roles', () => {
      const userRoles = ['Members_CRUD'];
      const availableViews = service.getAvailableViews(userRoles);
      expect(availableViews.length).toBeGreaterThan(0);
      
      // All returned views should be viewable by the user
      availableViews.forEach(view => {
        expect(view.permissions.view.some(role => userRoles.includes(role))).toBe(true);
      });
    });
  });

  describe('Export View Filtering', () => {
    it('should filter members for paper clubblad export', () => {
      const view = EXPORT_VIEWS.addressStickersPaper;
      expect(view.filter).toBeDefined();
      
      if (view.filter) {
        const filteredMembers = mockMembers.filter(view.filter);
        // Should only include Marie (status: Actief, clubblad: Papier)
        expect(filteredMembers).toHaveLength(1);
        expect(filteredMembers[0].korte_naam).toBe('Marie de Vries');
      }
    });

    it('should filter members for digital email export', () => {
      const view = EXPORT_VIEWS.emailGroupsDigital;
      expect(view.filter).toBeDefined();
      
      if (view.filter) {
        const filteredMembers = mockMembers.filter(view.filter);
        // Should only include Jan (status: Actief, clubblad: Digitaal, has email)
        expect(filteredMembers).toHaveLength(1);
        expect(filteredMembers[0].korte_naam).toBe('Jan van der Berg');
      }
    });

    it('should filter members for birthday list', () => {
      const view = EXPORT_VIEWS.birthdayList;
      expect(view.filter).toBeDefined();
      
      if (view.filter) {
        const filteredMembers = mockMembers.filter(view.filter);
        // Should include Jan and Marie (status: Actief)
        expect(filteredMembers).toHaveLength(2);
        expect(filteredMembers.map(m => m.korte_naam)).toEqual(['Jan van der Berg', 'Marie de Vries']);
      }
    });
  });

  describe('Export View Execution', () => {
    it('should export using predefined view', async () => {
      const result = await service.exportView('birthdayList', mockMembers);
      
      expect(result.success).toBe(true);
      expect(result.recordCount).toBe(2); // Only active members
      expect(result.filename).toContain('birthday-list');
    });

    it('should handle invalid export view', async () => {
      const result = await service.exportView('nonexistentView', mockMembers);
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('not found');
    });

    it('should export with custom options', async () => {
      const result = await service.exportView('birthdayList', mockMembers, {
        format: 'xlsx',
        filename: 'custom-birthday-list.xlsx'
      });
      
      expect(result.success).toBe(true);
      expect(result.filename).toBe('custom-birthday-list.xlsx');
    });
  });

  describe('Table Context Export', () => {
    it('should export using table context', async () => {
      const result = await service.exportTableContext('memberOverview', mockMembers);
      
      expect(result.success).toBe(true);
      expect(result.recordCount).toBe(3); // All members
      expect(result.filename).toContain('member-overview');
    });

    it('should handle invalid table context', async () => {
      const result = await service.exportTableContext('nonexistentContext', mockMembers);
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('not found');
    });
  });

  describe('Custom Columns Export', () => {
    it('should export using custom columns', async () => {
      const customColumns = [
        { key: 'name', label: 'Name', getValue: (m: Member) => m.korte_naam || '' },
        { key: 'email', label: 'Email', getValue: (m: Member) => m.email || '' }
      ];

      const result = await service.exportCustomColumns(mockMembers, customColumns);
      
      expect(result.success).toBe(true);
      expect(result.recordCount).toBe(3);
    });

    it('should handle empty custom columns', async () => {
      const result = await service.exportCustomColumns(mockMembers, []);
      
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe('Export Preview', () => {
    it('should generate export preview', () => {
      const preview = service.generatePreview('birthdayList', mockMembers, 2);
      
      expect(preview.headers).toBeInstanceOf(Array);
      expect(preview.headers.length).toBeGreaterThan(0);
      expect(preview.sampleRows).toBeInstanceOf(Array);
      expect(preview.sampleRows.length).toBeLessThanOrEqual(2);
      expect(preview.totalRecords).toBe(2); // Only active members
      expect(preview.estimatedFileSize).toBeDefined();
    });

    it('should handle invalid view in preview', () => {
      const preview = service.generatePreview('nonexistentView', mockMembers);
      
      expect(preview.headers).toEqual([]);
      expect(preview.sampleRows).toEqual([]);
      expect(preview.totalRecords).toBe(0);
    });

    it('should handle empty members in preview', () => {
      const preview = service.generatePreview('birthdayList', []);
      
      expect(preview.headers).toBeInstanceOf(Array);
      expect(preview.sampleRows).toEqual([]);
      expect(preview.totalRecords).toBe(0);
    });
  });

  describe('Format-Specific Exports', () => {
    it('should export to CSV format', async () => {
      const result = await service.exportView('birthdayList', mockMembers, { format: 'csv' });
      
      expect(result.success).toBe(true);
      expect(result.filename).toContain('.csv');
    });

    it('should export to XLSX format', async () => {
      const result = await service.exportView('birthdayList', mockMembers, { format: 'xlsx' });
      
      expect(result.success).toBe(true);
      expect(result.filename).toContain('.xlsx');
    });

    it('should export to PDF format', async () => {
      const result = await service.exportView('birthdayList', mockMembers, { format: 'pdf' });
      
      expect(result.success).toBe(true);
      expect(result.filename).toContain('.pdf');
    });

    it('should export to TXT format', async () => {
      const result = await service.exportView('birthdayList', mockMembers, { format: 'txt' });
      
      expect(result.success).toBe(true);
      expect(result.filename).toContain('.txt');
    });
  });

  describe('Error Handling', () => {
    it('should handle empty member array', async () => {
      const result = await service.exportView('birthdayList', []);
      
      expect(result.success).toBe(true);
      expect(result.recordCount).toBe(0);
    });

    it('should handle null/undefined members', async () => {
      const result = await service.exportView('birthdayList', null as any);
      
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('should handle export errors gracefully', async () => {
      // Test with invalid members data to trigger an error
      const result = await service.exportView('birthdayList', null as any);
      
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe('Filename Generation', () => {
    it('should generate valid filenames', () => {
      const filename = service['generateFilename']('Test Export View', 'csv');
      
      expect(filename).toMatch(/^hdcn-test-export-view-\d{4}-\d{2}-\d{2}\.csv$/);
    });

    it('should sanitize special characters in filenames', () => {
      const filename = service['generateFilename']('Test@#$%Export!View', 'xlsx');
      
      expect(filename).toMatch(/^hdcn-test----export-view-\d{4}-\d{2}-\d{2}\.xlsx$/);
    });
  });

  describe('CSV Value Escaping', () => {
    it('should escape CSV values with commas', () => {
      const escaped = service['escapeCsvValue']('Last, First');
      expect(escaped).toBe('"Last, First"');
    });

    it('should escape CSV values with quotes', () => {
      const escaped = service['escapeCsvValue']('He said "Hello"');
      expect(escaped).toBe('"He said ""Hello"""');
    });

    it('should escape CSV values with newlines', () => {
      const escaped = service['escapeCsvValue']('Line 1\nLine 2');
      expect(escaped).toBe('"Line 1\nLine 2"');
    });

    it('should not escape simple values', () => {
      const escaped = service['escapeCsvValue']('Simple Value');
      expect(escaped).toBe('Simple Value');
    });

    it('should handle empty values', () => {
      const escaped = service['escapeCsvValue']('');
      expect(escaped).toBe('');
    });
  });

  describe('File Size Formatting', () => {
    it('should format bytes correctly', () => {
      expect(service['formatFileSize'](0)).toBe('0 B');
      expect(service['formatFileSize'](1024)).toBe('1 KB');
      expect(service['formatFileSize'](1048576)).toBe('1 MB');
      expect(service['formatFileSize'](1073741824)).toBe('1 GB');
    });

    it('should format partial sizes correctly', () => {
      expect(service['formatFileSize'](1536)).toBe('1.5 KB');
      expect(service['formatFileSize'](2621440)).toBe('2.5 MB');
    });
  });
});
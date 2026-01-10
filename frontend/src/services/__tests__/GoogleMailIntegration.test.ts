/**
 * Google Mail Integration Tests
 * 
 * Tests for the integration between MemberExportService and GoogleMailService
 */

import { MemberExportService } from '../MemberExportService';
import { GoogleMailService } from '../GoogleMailService';
import { Member } from '../../types/index';

// Mock fetch globally
global.fetch = jest.fn();

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

describe('Google Mail Integration', () => {
  let exportService: MemberExportService;
  let googleService: GoogleMailService;
  const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

  const mockMembers: Member[] = [
    {
      id: '1',
      korte_naam: 'John Doe',
      email: 'john@example.com',
      status: 'Actief',
      clubblad: 'Digitaal',
      voornaam: 'John',
      achternaam: 'Doe'
    } as Member,
    {
      id: '2',
      korte_naam: 'Jane Smith',
      email: 'jane@example.com',
      status: 'Actief',
      clubblad: 'Digitaal',
      voornaam: 'Jane',
      achternaam: 'Smith'
    } as Member
  ];

  beforeEach(() => {
    exportService = MemberExportService.getInstance();
    googleService = GoogleMailService.getInstance();
    mockFetch.mockClear();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();

    // Mock authenticated state
    localStorageMock.getItem.mockImplementation((key) => {
      if (key === 'google_access_token') return 'mock-token';
      if (key === 'google_expires_at') return (Date.now() + 3600000).toString();
      return null;
    });
    
    // Force reload tokens
    (googleService as any).loadStoredTokens();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  // ============================================================================
  // INTEGRATION TESTS
  // ============================================================================

  describe('MemberExportService Integration', () => {
    test('should support google-contacts format', () => {
      const formats = exportService.getSupportedFormats('emailGroupsDigital');
      expect(formats).toContain('google-contacts');
    });

    test('should not support google-contacts when not authenticated', () => {
      // Clear authentication
      localStorageMock.getItem.mockReturnValue(null);
      (googleService as any).loadStoredTokens();

      const formats = exportService.getSupportedFormats('emailGroupsDigital');
      expect(formats).not.toContain('google-contacts');
    });

    test('should export view to Google Contacts', async () => {
      // Mock Google API responses
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          resourceName: 'contactGroups/mock-group-id',
          name: 'H-DCN Email Groups (Digital)',
          groupType: 'USER_CONTACT_GROUP'
        })
      } as Response);

      // Mock contact search (no existing contacts)
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ results: [] })
      } as Response);

      // Mock contact creation
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          resourceName: 'people/mock-contact-id'
        })
      } as Response);

      const result = await exportService.exportViewToGoogleContacts(
        'emailGroupsDigital',
        mockMembers,
        'Test Distribution List'
      );

      expect(result.success).toBe(true);
      expect(result.googleResult).toBeDefined();
      expect(result.googleResult?.groupName).toBe('Test Distribution List');
      expect(result.googleResult?.memberCount).toBe(2);
    });

    test('should handle Google Contacts export failure', async () => {
      // Mock Google API failure
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        text: async () => 'Insufficient permissions'
      } as Response);

      const result = await exportService.exportViewToGoogleContacts(
        'emailGroupsDigital',
        mockMembers
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('Failed to create contact group');
    });

    test('should check Google Contacts availability', () => {
      expect(exportService.isGoogleContactsAvailable()).toBe(true);

      // Clear authentication
      localStorageMock.getItem.mockReturnValue(null);
      (googleService as any).loadStoredTokens();

      expect(exportService.isGoogleContactsAvailable()).toBe(false);
    });
  });

  // ============================================================================
  // FORMAT SUPPORT TESTS
  // ============================================================================

  describe('Format Support', () => {
    test('should include google-contacts for email views when authenticated', () => {
      const emailViews = ['emailGroupsDigital', 'emailGroupsRegional'];
      
      emailViews.forEach(viewName => {
        const formats = exportService.getSupportedFormats(viewName);
        expect(formats).toContain('google-contacts');
      });
    });

    test('should not include google-contacts for non-email views', () => {
      const nonEmailViews = ['addressStickersPaper', 'birthdayList'];
      
      nonEmailViews.forEach(viewName => {
        const formats = exportService.getSupportedFormats(viewName);
        expect(formats).not.toContain('google-contacts');
      });
    });

    test('should include standard formats for all views', () => {
      const allViews = ['emailGroupsDigital', 'addressStickersPaper', 'birthdayList'];
      
      allViews.forEach(viewName => {
        const formats = exportService.getSupportedFormats(viewName);
        expect(formats).toContain('csv');
        expect(formats).toContain('xlsx');
        expect(formats).toContain('pdf');
      });
    });
  });

  // ============================================================================
  // ERROR HANDLING TESTS
  // ============================================================================

  describe('Error Handling', () => {
    test('should handle authentication errors gracefully', async () => {
      // Clear authentication
      localStorageMock.getItem.mockReturnValue(null);
      (googleService as any).loadStoredTokens();

      const result = await exportService.exportView('emailGroupsDigital', mockMembers, {
        format: 'google-contacts'
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain('Not authenticated');
    });

    test('should handle invalid view names', async () => {
      const result = await exportService.exportViewToGoogleContacts(
        'invalidView',
        mockMembers
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('not found');
    });

    test('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await exportService.exportViewToGoogleContacts(
        'emailGroupsDigital',
        mockMembers
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network error');
    });
  });

  // ============================================================================
  // MEMBER FILTERING TESTS
  // ============================================================================

  describe('Member Filtering', () => {
    test('should filter members correctly for email views', async () => {
      const mixedMembers: Member[] = [
        ...mockMembers,
        {
          id: '3',
          korte_naam: 'Bob Wilson',
          email: 'bob@example.com',
          status: 'Actief',
          clubblad: 'Papier', // Should be filtered out for digital view
          voornaam: 'Bob',
          achternaam: 'Wilson'
        } as Member,
        {
          id: '4',
          korte_naam: 'Alice Brown',
          email: '', // Should be filtered out (no email)
          status: 'Actief',
          clubblad: 'Digitaal',
          voornaam: 'Alice',
          achternaam: 'Brown'
        } as Member
      ];

      // Mock Google API responses
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          resourceName: 'contactGroups/mock-group-id',
          name: 'Test Group',
          groupType: 'USER_CONTACT_GROUP'
        })
      } as Response);

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ results: [] })
      } as Response);

      const result = await exportService.exportViewToGoogleContacts(
        'emailGroupsDigital',
        mixedMembers
      );

      expect(result.success).toBe(true);
      // Should only include the 2 members with digital clubblad and valid email
      expect(result.googleResult?.memberCount).toBe(2);
    });
  });
});
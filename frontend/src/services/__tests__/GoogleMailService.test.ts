/**
 * Google Mail Service Tests
 * 
 * Tests for the Google Mail integration service including authentication,
 * distribution list creation, and error handling.
 */

import { GoogleMailService, googleMailService } from '../GoogleMailService';
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

// Mock window.open
Object.defineProperty(window, 'open', {
  value: jest.fn(),
});

describe('GoogleMailService', () => {
  let service: GoogleMailService;
  const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

  beforeEach(() => {
    service = GoogleMailService.getInstance();
    mockFetch.mockClear();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  // ============================================================================
  // AUTHENTICATION TESTS
  // ============================================================================

  describe('Authentication', () => {
    test('should return false for isAuthenticated when no token', () => {
      localStorageMock.getItem.mockReturnValue(null);
      expect(service.isAuthenticated()).toBe(false);
    });

    test('should return false for isAuthenticated when token expired', () => {
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'google_access_token') return 'mock-token';
        if (key === 'google_expires_at') return (Date.now() - 1000).toString();
        return null;
      });
      expect(service.isAuthenticated()).toBe(false);
    });

    test('should return true for isAuthenticated when token valid', () => {
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'google_access_token') return 'mock-token';
        if (key === 'google_expires_at') return (Date.now() + 3600000).toString();
        return null;
      });
      
      // Force reload tokens
      (service as any).loadStoredTokens();
      
      expect(service.isAuthenticated()).toBe(true);
    });

    test('should initiate auth by opening popup window', () => {
      const mockOpen = window.open as jest.MockedFunction<typeof window.open>;
      service.initiateAuth();
      
      expect(mockOpen).toHaveBeenCalledWith(
        expect.stringContaining('accounts.google.com/o/oauth2/v2/auth'),
        'google-auth',
        'width=500,height=600'
      );
    });

    test('should handle auth callback successfully', async () => {
      // Mock token exchange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'mock-access-token',
          refresh_token: 'mock-refresh-token',
          expires_in: 3600
        })
      } as Response);

      // Mock user info
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          email: 'test@example.com',
          name: 'Test User',
          id: '123456789'
        })
      } as Response);

      const result = await service.handleAuthCallback('mock-auth-code');

      expect(result.user.email).toBe('test@example.com');
      expect(result.user.name).toBe('Test User');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('google_access_token', 'mock-access-token');
    });

    test('should handle auth callback failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => 'Invalid authorization code'
      } as Response);

      await expect(service.handleAuthCallback('invalid-code')).rejects.toThrow('Token exchange failed');
    });

    test('should clear tokens on logout', () => {
      service.logout();
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('google_access_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('google_refresh_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('google_expires_at');
    });
  });

  // ============================================================================
  // DISTRIBUTION LIST TESTS
  // ============================================================================

  describe('Distribution Lists', () => {
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
      // Mock authenticated state
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'google_access_token') return 'mock-token';
        if (key === 'google_expires_at') return (Date.now() + 3600000).toString();
        return null;
      });
      
      // Force reload tokens
      (service as any).loadStoredTokens();
    });

    test('should create distribution list from view successfully', async () => {
      // Mock contact group creation
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

      const result = await service.createDistributionListFromView(
        'emailGroupsDigital',
        mockMembers
      );

      expect(result.success).toBe(true);
      expect(result.memberCount).toBe(2);
      expect(result.groupName).toBe('H-DCN Email Groups (Digital)');
    });

    test('should fail when not authenticated', async () => {
      // Clear authentication
      localStorageMock.getItem.mockReturnValue(null);
      (service as any).loadStoredTokens();

      const result = await service.createDistributionListFromView(
        'emailGroupsDigital',
        mockMembers
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('Not authenticated');
    });

    test('should fail with invalid view name', async () => {
      const result = await service.createDistributionListFromView(
        'invalidView',
        mockMembers
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('not found');
    });

    test('should handle contact group creation failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        text: async () => 'Insufficient permissions'
      } as Response);

      const result = await service.createDistributionListFromView(
        'emailGroupsDigital',
        mockMembers
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('Failed to create contact group');
    });
  });

  // ============================================================================
  // UTILITY TESTS
  // ============================================================================

  describe('Utilities', () => {
    test('should return distribution list templates', () => {
      const templates = service.getDistributionListTemplates();
      
      expect(templates).toHaveLength(4);
      expect(templates[0]).toHaveProperty('key', 'emailGroupsDigital');
      expect(templates[0]).toHaveProperty('name', 'Digital Clubblad Recipients');
      expect(templates[0]).toHaveProperty('useCase');
    });

    test('should get correct fields for email views', () => {
      const service = GoogleMailService.getInstance();
      // Access private method for testing
      const getFieldsForView = (service as any).getFieldsForView.bind(service);
      
      expect(getFieldsForView('emailGroupsDigital')).toEqual(['name', 'email']);
      expect(getFieldsForView('addressStickersPaper')).toEqual(['name', 'email', 'address']);
      expect(getFieldsForView('birthdayList')).toEqual(['name', 'email', 'phone', 'address']);
    });

    test('should generate gmail address from group resource name', () => {
      const service = GoogleMailService.getInstance();
      // Access private method for testing
      const generateGmailAddress = (service as any).generateGmailAddress.bind(service);
      
      const address = generateGmailAddress('contactGroups/abc123');
      expect(address).toBe('group-abc123@contacts.google.com');
    });
  });

  // ============================================================================
  // SINGLETON TESTS
  // ============================================================================

  describe('Singleton Pattern', () => {
    test('should return same instance', () => {
      const instance1 = GoogleMailService.getInstance();
      const instance2 = GoogleMailService.getInstance();
      
      expect(instance1).toBe(instance2);
    });

    test('should use exported singleton', () => {
      const instance = GoogleMailService.getInstance();
      expect(googleMailService).toBe(instance);
    });
  });

  // ============================================================================
  // ERROR HANDLING TESTS
  // ============================================================================

  describe('Error Handling', () => {
    test('should handle network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(service.handleAuthCallback('test-code')).rejects.toThrow('Network error');
    });

    test('should handle malformed responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => { throw new Error('Invalid JSON'); },
        headers: new Headers(),
        redirected: false,
        status: 200,
        statusText: 'OK',
        type: 'basic',
        url: '',
        clone: jest.fn(),
        body: null,
        bodyUsed: false,
        arrayBuffer: jest.fn(),
        blob: jest.fn(),
        formData: jest.fn(),
        text: jest.fn()
      } as Response);

      await expect(service.handleAuthCallback('test-code')).rejects.toThrow();
    });

    test('should handle rate limiting', async () => {
      // Mock authenticated state
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'google_access_token') return 'mock-token';
        if (key === 'google_expires_at') return (Date.now() + 3600000).toString();
        return null;
      });
      
      // Force reload tokens
      (service as any).loadStoredTokens();

      // Mock rate limit response
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        text: async () => 'Rate limit exceeded'
      } as Response);

      const result = await service.createDistributionListFromView(
        'emailGroupsDigital',
        []
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('Failed to create contact group');
    });
  });
});
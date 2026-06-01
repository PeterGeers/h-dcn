/**
 * Auth Headers Tests
 *
 * Tests for authentication header generation using Amplify v6 fetchAuthSession().
 * Validates token retrieval, error handling, and role filtering.
 *
 * Requirements: R4.3, R6.6
 */

import { getAuthHeaders, getAuthHeadersForGet } from '../authHeaders';

// Mock aws-amplify/auth
jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: jest.fn(),
}));

import { fetchAuthSession } from 'aws-amplify/auth';

const mockedFetchAuthSession = fetchAuthSession as jest.MockedFunction<typeof fetchAuthSession>;

describe('Auth Headers', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('getAuthHeaders', () => {
    test('should return Bearer token from fetchAuthSession', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => 'mock-access-token',
            payload: {
              'cognito:groups': ['hdcnLeden'],
              sub: 'user-123',
            },
          },
          idToken: {
            toString: () => 'mock-id-token',
            payload: { email: 'test@example.com' },
          },
        },
      } as any);

      const headers = await getAuthHeaders();

      expect(headers['Authorization']).toBe('Bearer mock-access-token');
      expect(headers['Content-Type']).toBe('application/json');
    });

    test('should throw error when no session exists', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: undefined,
      } as any);

      await expect(getAuthHeaders()).rejects.toThrow('Not authenticated');
    });

    test('should throw error when accessToken is undefined', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: undefined,
          idToken: undefined,
        },
      } as any);

      await expect(getAuthHeaders()).rejects.toThrow('Not authenticated');
    });

    test('should include X-Enhanced-Groups header with valid groups', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => 'mock-token',
            payload: {
              'cognito:groups': ['hdcnLeden', 'Members_CRUD', 'Regio_Utrecht'],
            },
          },
        },
      } as any);

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['hdcnLeden', 'Members_CRUD', 'Regio_Utrecht']);
    });

    test('should not include X-Enhanced-Groups when no groups exist', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => 'mock-token',
            payload: {},
          },
        },
      } as any);

      const headers = await getAuthHeaders();

      expect(headers['X-Enhanced-Groups']).toBeUndefined();
    });

    test('should filter out invalid roles', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => 'mock-token',
            payload: {
              'cognito:groups': ['hdcnLeden', 'InvalidRole', 'Members_CRUD_All'],
            },
          },
        },
      } as any);

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['hdcnLeden']);
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: InvalidRole');
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: Members_CRUD_All');
    });

    test('should throw when fetchAuthSession rejects', async () => {
      mockedFetchAuthSession.mockRejectedValue(new Error('Network error'));

      await expect(getAuthHeaders()).rejects.toThrow('Network error');
    });
  });

  describe('getAuthHeadersForGet', () => {
    test('should return Authorization header without Content-Type', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => 'mock-get-token',
            payload: {
              'cognito:groups': ['hdcnLeden'],
            },
          },
        },
      } as any);

      const headers = await getAuthHeadersForGet();

      expect(headers['Authorization']).toBe('Bearer mock-get-token');
      expect(headers['Content-Type']).toBeUndefined();
    });

    test('should throw error when not authenticated', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: undefined,
      } as any);

      await expect(getAuthHeadersForGet()).rejects.toThrow('Not authenticated');
    });

    test('should include X-Enhanced-Groups for GET requests', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => 'mock-token',
            payload: {
              'cognito:groups': ['Members_Read', 'Regio_All'],
            },
          },
        },
      } as any);

      const headers = await getAuthHeadersForGet();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['Members_Read', 'Regio_All']);
    });
  });

  describe('Role Filtering Logic', () => {
    test('should allow permission-based roles', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => 'mock-token',
            payload: {
              'cognito:groups': ['Members_CRUD', 'Events_Read', 'Products_Export', 'Members_Status_Approve'],
            },
          },
        },
      } as any);

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['Members_CRUD', 'Events_Read', 'Products_Export', 'Members_Status_Approve']);
    });

    test('should allow regional roles', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => 'mock-token',
            payload: {
              'cognito:groups': ['Regio_All', 'Regio_Utrecht', 'Regio_Limburg'],
            },
          },
        },
      } as any);

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['Regio_All', 'Regio_Utrecht', 'Regio_Limburg']);
    });

    test('should allow system roles', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => 'mock-token',
            payload: {
              'cognito:groups': ['System_User_Management', 'System_Logs_Read'],
            },
          },
        },
      } as any);

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['System_User_Management', 'System_Logs_Read']);
    });

    test('should reject invalid _All roles except Regio_All', async () => {
      mockedFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => 'mock-token',
            payload: {
              'cognito:groups': ['Members_CRUD_All', 'Events_Read_All', 'Regio_All'],
            },
          },
        },
      } as any);

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['Regio_All']);
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: Members_CRUD_All');
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: Events_Read_All');
    });
  });
});

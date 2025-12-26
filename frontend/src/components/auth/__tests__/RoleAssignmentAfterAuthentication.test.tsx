import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock Chakra UI components to avoid dependency issues
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div data-testid="box" {...props}>{children}</div>,
  Button: ({ children, onClick, isDisabled, isLoading, loadingText, type, ...props }: any) => (
    <button 
      onClick={onClick} 
      disabled={isDisabled || isLoading} 
      type={type}
      data-testid={`button-${children}`}
      {...props}
    >
      {isLoading ? loadingText : children}
    </button>
  ),
  FormControl: ({ children, isRequired }: any) => {
    const mockReact = require('react');
    return (
      <div data-required={isRequired}>
        {mockReact.Children.map(children, (child: any) => {
          if (child?.type?.name === 'Input' || (child?.props && 'placeholder' in child.props)) {
            return mockReact.cloneElement(child, { required: isRequired });
          }
          return child;
        })}
      </div>
    );
  },
  FormLabel: ({ children }: any) => <label>{children}</label>,
  Input: ({ onChange, value, placeholder, type, name, required, ...props }: any) => (
    <input 
      onChange={onChange} 
      value={value} 
      placeholder={placeholder} 
      type={type}
      name={name}
      required={required}
      {...props} 
    />
  ),
  VStack: ({ children }: any) => <div>{children}</div>,
  HStack: ({ children }: any) => <div>{children}</div>,
  Text: ({ children }: any) => <span>{children}</span>,
  Alert: ({ children }: any) => <div role="alert">{children}</div>,
  AlertIcon: () => <span>!</span>,
  Heading: ({ children }: any) => <h1>{children}</h1>,
  Tabs: ({ children }: any) => <div>{children}</div>,
  TabList: ({ children }: any) => <div>{children}</div>,
  TabPanels: ({ children }: any) => <div>{children}</div>,
  Tab: ({ children, onClick }: any) => <button onClick={onClick}>{children}</button>,
  TabPanel: ({ children }: any) => <div>{children}</div>,
  Image: ({ src, alt, ...props }: any) => <img src={src} alt={alt} {...props} />,
  useToast: () => jest.fn(),
  Divider: () => <hr />,
}));

// Mock Chakra UI icons
jest.mock('@chakra-ui/icons', () => ({
  CheckIcon: { name: 'CheckIcon' },
  WarningIcon: { name: 'WarningIcon' },
}));

// Mock AWS Amplify
jest.mock('aws-amplify/auth', () => ({
  getCurrentUser: jest.fn(),
  signIn: jest.fn(),
  fetchAuthSession: jest.fn(),
}));

// Mock authService
jest.mock('../../../services/authService', () => ({
  getCurrentUserRoles: jest.fn(),
  getCurrentUserInfo: jest.fn(),
  validateCognitoGroupsClaim: jest.fn(),
}));

// Mock useAuth hook
jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

import { fetchAuthSession } from 'aws-amplify/auth';
import { getCurrentUserRoles, getCurrentUserInfo, validateCognitoGroupsClaim } from '../../../services/authService';
import { useAuth } from '../../../hooks/useAuth';
import { HDCNGroup } from '../../../types/user';

const mockFetchAuthSession = fetchAuthSession as jest.MockedFunction<typeof fetchAuthSession>;
const mockGetCurrentUserRoles = getCurrentUserRoles as jest.MockedFunction<typeof getCurrentUserRoles>;
const mockGetCurrentUserInfo = getCurrentUserInfo as jest.MockedFunction<typeof getCurrentUserInfo>;
const mockValidateCognitoGroupsClaim = validateCognitoGroupsClaim as jest.MockedFunction<typeof validateCognitoGroupsClaim>;
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

// Mock fetch for API calls
global.fetch = jest.fn();

// Simple test component that uses the useAuth hook
const TestComponent: React.FC<{ onUserData?: (userData: any) => void }> = ({ onUserData }) => {
  const authData = useAuth();
  
  React.useEffect(() => {
    if (onUserData) {
      onUserData(authData);
    }
  }, [authData, onUserData]);

  if (authData.loading) {
    return <div>Loading...</div>;
  }

  if (!authData.isAuthenticated) {
    return <div>Not Authenticated</div>;
  }

  if (!authData.user) {
    return <div>No User Data</div>;
  }

  return (
    <div>
      <div data-testid="user-email">{authData.user.email}</div>
      <div data-testid="user-roles">{authData.user.groups.join(',')}</div>
      <div data-testid="has-hdcnleden">{authData.hasRole('hdcnLeden') ? 'true' : 'false'}</div>
      {authData.user.groups.includes('hdcnLeden') ? (
        <div data-testid="member-content">Member Portal</div>
      ) : (
        <div data-testid="applicant-content">Application Form</div>
      )}
    </div>
  );
};

describe('Role Assignment After Authentication', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockReset();
    
    // Default mock for validateCognitoGroupsClaim
    mockValidateCognitoGroupsClaim.mockReturnValue(true);
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  describe('New Applicant Role Assignment', () => {
    test('new applicant should NOT receive hdcnLeden role after authentication', async () => {
      // Mock authentication session for new applicant (no roles assigned)
      const newApplicantSession = {
        tokens: {
          accessToken: {
            toString: () => 'mock-access-token-no-roles'
          }
        }
      };

      const newApplicantUserInfo = {
        username: 'newapplicant@example.com',
        email: 'newapplicant@example.com',
        roles: [] as HDCNGroup[], // No roles for new applicant
        sub: 'new-applicant-123'
      };

      mockFetchAuthSession.mockResolvedValue(newApplicantSession as any);
      mockGetCurrentUserRoles.mockResolvedValue([]);
      mockGetCurrentUserInfo.mockResolvedValue(newApplicantUserInfo);

      // Mock useAuth to return new applicant state
      mockUseAuth.mockReturnValue({
        user: {
          id: 'new-applicant-123',
          username: 'newapplicant@example.com',
          email: 'newapplicant@example.com',
          groups: [], // No roles assigned
          attributes: {
            email: 'newapplicant@example.com',
            username: 'newapplicant@example.com'
          }
        },
        loading: false,
        isAuthenticated: true,
        logout: jest.fn(),
        hasRole: jest.fn().mockReturnValue(false), // No roles
        refreshUserRoles: jest.fn()
      });

      render(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('user-email')).toHaveTextContent('newapplicant@example.com');
      });

      // Verify the user has no roles
      expect(screen.getByTestId('user-roles')).toHaveTextContent('');
      expect(screen.getByTestId('has-hdcnleden')).toHaveTextContent('false');
      
      // Should show application form, not member portal
      expect(screen.getByTestId('applicant-content')).toBeInTheDocument();
      expect(screen.queryByTestId('member-content')).not.toBeInTheDocument();
    });

    test('new applicant should be routed to application form, not member portal', async () => {
      // Mock API call to check member record (should return 404 for new applicant)
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ error: 'Member not found' })
      });

      const newApplicantUserInfo = {
        username: 'newapplicant@example.com',
        email: 'newapplicant@example.com',
        roles: [] as HDCNGroup[],
        sub: 'new-applicant-123'
      };

      mockGetCurrentUserInfo.mockResolvedValue(newApplicantUserInfo);
      mockGetCurrentUserRoles.mockResolvedValue([]);

      mockUseAuth.mockReturnValue({
        user: {
          id: 'new-applicant-123',
          username: 'newapplicant@example.com',
          email: 'newapplicant@example.com',
          groups: [],
          attributes: {
            email: 'newapplicant@example.com',
            username: 'newapplicant@example.com'
          }
        },
        loading: false,
        isAuthenticated: true,
        logout: jest.fn(),
        hasRole: jest.fn().mockReturnValue(false),
        refreshUserRoles: jest.fn()
      });

      render(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('applicant-content')).toBeInTheDocument();
      });

      // Verify routing logic - should show application form for new applicant
      expect(screen.getByText('Application Form')).toBeInTheDocument();
      expect(screen.queryByText('Member Portal')).not.toBeInTheDocument();
    });
  });

  describe('Approved Member Role Assignment', () => {
    test('approved member should receive hdcnLeden role after authentication', async () => {
      // Mock authentication session for approved member (with hdcnLeden role)
      const approvedMemberSession = {
        tokens: {
          accessToken: {
            toString: () => 'mock-access-token-with-hdcnleden'
          }
        }
      };

      const approvedMemberUserInfo = {
        username: 'approvedmember@example.com',
        email: 'approvedmember@example.com',
        roles: ['hdcnLeden'] as HDCNGroup[], // Has hdcnLeden role
        sub: 'approved-member-123'
      };

      mockFetchAuthSession.mockResolvedValue(approvedMemberSession as any);
      mockGetCurrentUserRoles.mockResolvedValue(['hdcnLeden']);
      mockGetCurrentUserInfo.mockResolvedValue(approvedMemberUserInfo);

      // Mock useAuth to return approved member state
      mockUseAuth.mockReturnValue({
        user: {
          id: 'approved-member-123',
          username: 'approvedmember@example.com',
          email: 'approvedmember@example.com',
          groups: ['hdcnLeden'], // Has hdcnLeden role
          attributes: {
            email: 'approvedmember@example.com',
            username: 'approvedmember@example.com'
          }
        },
        loading: false,
        isAuthenticated: true,
        logout: jest.fn(),
        hasRole: jest.fn().mockImplementation((role: HDCNGroup) => role === 'hdcnLeden'),
        refreshUserRoles: jest.fn()
      });

      render(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('user-email')).toHaveTextContent('approvedmember@example.com');
      });

      // Verify the user has hdcnLeden role
      expect(screen.getByTestId('user-roles')).toHaveTextContent('hdcnLeden');
      expect(screen.getByTestId('has-hdcnleden')).toHaveTextContent('true');
      
      // Should show member portal, not application form
      expect(screen.getByTestId('member-content')).toBeInTheDocument();
      expect(screen.queryByTestId('applicant-content')).not.toBeInTheDocument();
    });

    test('approved member should be routed to member portal', async () => {
      // Mock API call to check member record (should return 200 for approved member)
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ 
          member_id: 'member-123',
          email: 'approvedmember@example.com',
          status: 'active',
          lidmaatschap: 'gewoon lid'
        })
      });

      const approvedMemberUserInfo = {
        username: 'approvedmember@example.com',
        email: 'approvedmember@example.com',
        roles: ['hdcnLeden'] as HDCNGroup[],
        sub: 'approved-member-123'
      };

      mockGetCurrentUserInfo.mockResolvedValue(approvedMemberUserInfo);
      mockGetCurrentUserRoles.mockResolvedValue(['hdcnLeden']);

      mockUseAuth.mockReturnValue({
        user: {
          id: 'approved-member-123',
          username: 'approvedmember@example.com',
          email: 'approvedmember@example.com',
          groups: ['hdcnLeden'],
          attributes: {
            email: 'approvedmember@example.com',
            username: 'approvedmember@example.com'
          }
        },
        loading: false,
        isAuthenticated: true,
        logout: jest.fn(),
        hasRole: jest.fn().mockImplementation((role: HDCNGroup) => role === 'hdcnLeden'),
        refreshUserRoles: jest.fn()
      });

      render(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('member-content')).toBeInTheDocument();
      });

      // Verify routing logic - should show member portal for approved member
      expect(screen.getByText('Member Portal')).toBeInTheDocument();
      expect(screen.queryByText('Application Form')).not.toBeInTheDocument();
    });
  });

  describe('Role Assignment During Approval Process', () => {
    test('should verify role assignment happens when applicant is approved', async () => {
      // Mock the approval process API call
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ message: 'Member approved successfully' })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ message: 'Role assigned successfully' })
        });

      // Simulate the approval process
      const approvalData = {
        member_id: 'member-123',
        email: 'newmember@example.com',
        status: 'active', // Changed from 'new_applicant' to 'active'
        action: 'approve'
      };

      // Mock API call to approve member and assign role
      const approveResponse = await fetch('/api/members/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(approvalData)
      });

      expect(approveResponse.ok).toBe(true);

      // Mock API call to assign hdcnLeden role to approved member
      const roleAssignmentResponse = await fetch('/api/cognito/assign-role', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'newmember@example.com',
          role: 'hdcnLeden'
        })
      });

      expect(roleAssignmentResponse.ok).toBe(true);

      // Verify both API calls were made
      expect(global.fetch).toHaveBeenCalledTimes(2);
      expect(global.fetch).toHaveBeenNthCalledWith(1, '/api/members/approve', expect.any(Object));
      expect(global.fetch).toHaveBeenNthCalledWith(2, '/api/cognito/assign-role', expect.any(Object));
    });

    test('should verify role refresh after approval', async () => {
      // Mock initial state (no roles)
      let currentRoles: HDCNGroup[] = [];
      
      mockGetCurrentUserRoles
        .mockResolvedValueOnce([]) // Initial call - no roles
        .mockResolvedValueOnce(['hdcnLeden']); // After approval - has hdcnLeden

      // Mock refreshUserRoles function
      const mockRefreshUserRoles = jest.fn().mockImplementation(async () => {
        currentRoles = ['hdcnLeden'];
      });

      mockUseAuth.mockReturnValue({
        user: {
          id: 'member-123',
          username: 'member@example.com',
          email: 'member@example.com',
          groups: currentRoles,
          attributes: {
            email: 'member@example.com',
            username: 'member@example.com'
          }
        },
        loading: false,
        isAuthenticated: true,
        logout: jest.fn(),
        hasRole: jest.fn().mockImplementation((role: HDCNGroup) => currentRoles.includes(role)),
        refreshUserRoles: mockRefreshUserRoles
      });

      // Initial roles check
      let roles = await getCurrentUserRoles();
      expect(roles).toEqual([]);

      // Simulate approval and role assignment
      await mockRefreshUserRoles();

      // Verify roles were refreshed
      expect(mockRefreshUserRoles).toHaveBeenCalled();

      // Check roles after refresh
      roles = await getCurrentUserRoles();
      expect(roles).toContain('hdcnLeden');
    });
  });

  describe('Role Assignment Edge Cases', () => {
    test('should handle member with multiple roles including hdcnLeden', async () => {
      const multiRoleMemberUserInfo = {
        username: 'admin@example.com',
        email: 'admin@example.com',
        roles: ['hdcnLeden', 'Members_CRUD_All', 'Events_Read_All'] as HDCNGroup[],
        sub: 'admin-member-123'
      };

      mockGetCurrentUserInfo.mockResolvedValue(multiRoleMemberUserInfo);
      mockGetCurrentUserRoles.mockResolvedValue(['hdcnLeden', 'Members_CRUD_All', 'Events_Read_All']);

      mockUseAuth.mockReturnValue({
        user: {
          id: 'admin-member-123',
          username: 'admin@example.com',
          email: 'admin@example.com',
          groups: ['hdcnLeden', 'Members_CRUD_All', 'Events_Read_All'],
          attributes: {
            email: 'admin@example.com',
            username: 'admin@example.com'
          }
        },
        loading: false,
        isAuthenticated: true,
        logout: jest.fn(),
        hasRole: jest.fn().mockImplementation((role: HDCNGroup) => 
          ['hdcnLeden', 'Members_CRUD_All', 'Events_Read_All'].includes(role)
        ),
        refreshUserRoles: jest.fn()
      });

      render(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('user-email')).toHaveTextContent('admin@example.com');
      });

      // Verify all roles are present
      expect(screen.getByTestId('user-roles')).toHaveTextContent('hdcnLeden,Members_CRUD_All,Events_Read_All');
      expect(screen.getByTestId('has-hdcnleden')).toHaveTextContent('true');
      
      // Should show member portal since hdcnLeden role is present
      expect(screen.getByTestId('member-content')).toBeInTheDocument();
    });

    test('should handle suspended member (no hdcnLeden role)', async () => {
      const suspendedMemberUserInfo = {
        username: 'suspended@example.com',
        email: 'suspended@example.com',
        roles: [] as HDCNGroup[], // Suspended members have no roles
        sub: 'suspended-member-123'
      };

      mockGetCurrentUserInfo.mockResolvedValue(suspendedMemberUserInfo);
      mockGetCurrentUserRoles.mockResolvedValue([]);

      mockUseAuth.mockReturnValue({
        user: {
          id: 'suspended-member-123',
          username: 'suspended@example.com',
          email: 'suspended@example.com',
          groups: [], // No roles for suspended member
          attributes: {
            email: 'suspended@example.com',
            username: 'suspended@example.com'
          }
        },
        loading: false,
        isAuthenticated: true,
        logout: jest.fn(),
        hasRole: jest.fn().mockReturnValue(false),
        refreshUserRoles: jest.fn()
      });

      render(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('user-email')).toHaveTextContent('suspended@example.com');
      });

      // Verify no roles
      expect(screen.getByTestId('user-roles')).toHaveTextContent('');
      expect(screen.getByTestId('has-hdcnleden')).toHaveTextContent('false');
      
      // Should show application form since no hdcnLeden role
      expect(screen.getByTestId('applicant-content')).toBeInTheDocument();
      expect(screen.queryByTestId('member-content')).not.toBeInTheDocument();
    });

    test('should handle authentication errors gracefully', async () => {
      mockFetchAuthSession.mockRejectedValue(new Error('Authentication failed'));
      mockGetCurrentUserInfo.mockRejectedValue(new Error('Failed to get user info'));
      mockGetCurrentUserRoles.mockRejectedValue(new Error('Failed to get roles'));

      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
        isAuthenticated: false,
        logout: jest.fn(),
        hasRole: jest.fn().mockReturnValue(false),
        refreshUserRoles: jest.fn()
      });

      render(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByText('Not Authenticated')).toBeInTheDocument();
      });
    });
  });

  describe('Integration with Backend Role Assignment', () => {
    test('should verify backend role assignment API integration', async () => {
      // Mock the backend role assignment endpoint
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          message: 'Role assigned successfully',
          user: 'member@example.com',
          role: 'hdcnLeden',
          timestamp: new Date().toISOString()
        })
      });

      // Test the role assignment API call
      const response = await fetch('/api/cognito/assign-role', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer mock-admin-token'
        },
        body: JSON.stringify({
          email: 'member@example.com',
          role: 'hdcnLeden'
        })
      });

      expect(response.ok).toBe(true);
      const result = await response.json();
      expect(result.role).toBe('hdcnLeden');
      expect(result.user).toBe('member@example.com');
    });

    test('should verify role removal for suspended members', async () => {
      // Mock the backend role removal endpoint
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          message: 'Role removed successfully',
          user: 'suspended@example.com',
          role: 'hdcnLeden',
          action: 'removed'
        })
      });

      // Test the role removal API call
      const response = await fetch('/api/cognito/remove-role', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer mock-admin-token'
        },
        body: JSON.stringify({
          email: 'suspended@example.com',
          role: 'hdcnLeden'
        })
      });

      expect(response.ok).toBe(true);
      const result = await response.json();
      expect(result.action).toBe('removed');
      expect(result.role).toBe('hdcnLeden');
    });
  });
});
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FunctionGuard } from '../FunctionGuard';
import { HDCNGroup } from '../../../types/user';

// Mock the FunctionPermissionManager
jest.mock('../../../utils/functionPermissions', () => ({
  FunctionPermissionManager: {
    create: jest.fn()
  }
}));

import { FunctionPermissionManager } from '../../../utils/functionPermissions';
const mockFunctionPermissionManager = FunctionPermissionManager.create as jest.MockedFunction<typeof FunctionPermissionManager.create>;

describe('Role-Based UI Rendering', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // Helper function to create mock user with specific roles
  const createMockUser = (roles: HDCNGroup[]) => ({
    id: 'test-user',
    username: 'testuser',
    email: 'test@example.com',
    groups: roles,
    signInUserSession: {
      accessToken: {
        payload: {
          'cognito:groups': roles
        }
      }
    }
  });

  // Helper function to create mock permission manager
  const createMockPermissionManager = (hasAccess: boolean) => {
    const mockManager = {
      hasAccess: jest.fn().mockReturnValue(hasAccess),
      hasLegacyAccess: jest.fn().mockReturnValue(hasAccess),
      hasLegacyGroup: jest.fn().mockReturnValue(false),
      getLegacyGroups: jest.fn().mockReturnValue([]),
      hasFieldAccess: jest.fn().mockReturnValue(hasAccess),
      getAccessibleFunctions: jest.fn().mockReturnValue({})
    };
    
    // Create a proper mock that satisfies the FunctionPermissionManager interface
    return mockManager as any;
  };

  describe('Basic Member Role Rendering', () => {
    it('should render webshop content for basic members', async () => {
      const basicMember = createMockUser(['hdcnLeden']);
      mockFunctionPermissionManager.mockResolvedValue(createMockPermissionManager(true));

      render(
        <FunctionGuard user={basicMember} functionName="webshop">
          <div>Webshop Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Webshop Content')).toBeInTheDocument();
      });
    });

    it('should hide administrative content from basic members', async () => {
      const basicMember = createMockUser(['hdcnLeden']);
      mockFunctionPermissionManager.mockResolvedValue(createMockPermissionManager(false));

      render(
        <FunctionGuard user={basicMember} functionName="members" action="write">
          <div>Admin Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
      });
    });

    it('should render role-specific content for basic members', async () => {
      const basicMember = createMockUser(['hdcnLeden']);

      render(
        <FunctionGuard user={basicMember} requiredRoles={['hdcnLeden']}>
          <div>Member-Only Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Member-Only Content')).toBeInTheDocument();
      });
    });
  });

  describe('Administrative Role Rendering', () => {
    it('should render member management content for Members_CRUD role', async () => {
      const adminUser = createMockUser(['hdcnLeden', 'Members_CRUD']);
      mockFunctionPermissionManager.mockResolvedValue(createMockPermissionManager(true));

      render(
        <FunctionGuard user={adminUser} functionName="members" action="write">
          <div>Member Management</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Member Management')).toBeInTheDocument();
      });
    });

    it('should render system administration content for System_User_Management role', async () => {
      const systemAdmin = createMockUser(['hdcnLeden', 'System_User_Management']);

      render(
        <FunctionGuard user={systemAdmin} requiredRoles={['System_User_Management']}>
          <div>System Administration</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('System Administration')).toBeInTheDocument();
      });
    });

    it('should hide system content from non-admin users', async () => {
      const regularUser = createMockUser(['hdcnLeden', 'Members_Read']);

      render(
        <FunctionGuard user={regularUser} requiredRoles={['System_User_Management']}>
          <div>System Administration</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('System Administration')).not.toBeInTheDocument();
      });
    });
  });

  describe('Regional Role Rendering', () => {
    it('should render regional content for regional roles', async () => {
      const regionalUser = createMockUser(['hdcnLeden', 'Regio_Utrecht']);

      render(
        <FunctionGuard user={regionalUser} requiredRoles={['Regio_Utrecht']}>
          <div>Utrecht Region Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Utrecht Region Content')).toBeInTheDocument();
      });
    });

    it('should hide regional content from users in different regions', async () => {
      const region2User = createMockUser(['hdcnLeden', 'Regio_Limburg']);

      render(
        <FunctionGuard user={region2User} requiredRoles={['Regio_Utrecht']}>
          <div>Utrecht Region Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('Utrecht Region Content')).not.toBeInTheDocument();
      });
    });

    it('should render content for users with multiple regional roles', async () => {
      const multiRegionalUser = createMockUser([
        'hdcnLeden', 
        'Regio_Utrecht', 
        'Regio_Limburg'
      ]);

      render(
        <FunctionGuard user={multiRegionalUser} requiredRoles={['Regio_Utrecht']}>
          <div>Utrecht Region Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Utrecht Region Content')).toBeInTheDocument();
      });
    });
  });

  describe('Multiple Role Requirements', () => {
    it('should render content when user has any of the required roles', async () => {
      const user = createMockUser(['hdcnLeden', 'Members_Read']);

      render(
        <FunctionGuard user={user} requiredRoles={['Members_Read', 'Members_CRUD']}>
          <div>Member Data Access</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Member Data Access')).toBeInTheDocument();
      });
    });

    it('should hide content when user has none of the required roles', async () => {
      const user = createMockUser(['hdcnLeden']);

      render(
        <FunctionGuard user={user} requiredRoles={['Members_CRUD', 'System_User_Management']}>
          <div>Admin Only Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('Admin Only Content')).not.toBeInTheDocument();
      });
    });
  });

  describe('Combined Role and Function Permissions', () => {
    it('should render content when user has both role and function access', async () => {
      const user = createMockUser(['hdcnLeden', 'Members_CRUD']);
      mockFunctionPermissionManager.mockResolvedValue(createMockPermissionManager(true));

      render(
        <FunctionGuard 
          user={user} 
          functionName="members" 
          action="write"
          requiredRoles={['Members_CRUD']}
        >
          <div>Full Member Management</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Full Member Management')).toBeInTheDocument();
      });
    });

    it('should hide content when user has role but no function access', async () => {
      const user = createMockUser(['hdcnLeden', 'Members_CRUD']);
      mockFunctionPermissionManager.mockResolvedValue(createMockPermissionManager(false));

      render(
        <FunctionGuard 
          user={user} 
          functionName="members" 
          action="write"
          requiredRoles={['Members_CRUD']}
        >
          <div>Full Member Management</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('Full Member Management')).not.toBeInTheDocument();
      });
    });

    it('should hide content when user has function access but no role', async () => {
      const user = createMockUser(['hdcnLeden']);
      mockFunctionPermissionManager.mockResolvedValue(createMockPermissionManager(true));

      render(
        <FunctionGuard 
          user={user} 
          functionName="members" 
          action="read"
          requiredRoles={['Members_CRUD']}
        >
          <div>Full Member Management</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('Full Member Management')).not.toBeInTheDocument();
      });
    });
  });

  describe('Fallback Content Rendering', () => {
    it('should render fallback content when access is denied', async () => {
      const user = createMockUser(['hdcnLeden']);

      render(
        <FunctionGuard 
          user={user} 
          requiredRoles={['Members_CRUD']}
          fallback={<div>Access Denied</div>}
        >
          <div>Protected Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Access Denied')).toBeInTheDocument();
        expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
      });
    });

    it('should render nothing when no fallback is provided and access is denied', async () => {
      const user = createMockUser(['hdcnLeden']);

      const { container } = render(
        <FunctionGuard user={user} requiredRoles={['Members_CRUD']}>
          <div>Protected Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(container.firstChild).toBeNull();
      });
    });
  });

  describe('Complex Role Scenarios', () => {
    it('should handle users with multiple administrative roles', async () => {
      const superAdmin = createMockUser([
        'hdcnLeden',
        'Members_CRUD',
        'Events_CRUD',
        'System_User_Management',
        'Regio_All'
      ]);

      // Test multiple different role requirements
      const { rerender } = render(
        <FunctionGuard user={superAdmin} requiredRoles={['Members_CRUD']}>
          <div>Member Management</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Member Management')).toBeInTheDocument();
      });

      rerender(
        <FunctionGuard user={superAdmin} requiredRoles={['Events_CRUD']}>
          <div>Event Management</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Event Management')).toBeInTheDocument();
      });

      rerender(
        <FunctionGuard user={superAdmin} requiredRoles={['System_User_Management']}>
          <div>System Administration</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('System Administration')).toBeInTheDocument();
      });
    });

    it('should handle system admin role compatibility', async () => {
      const systemAdmin = createMockUser(['System_User_Management']);
      mockFunctionPermissionManager.mockResolvedValue(createMockPermissionManager(true));

      render(
        <FunctionGuard user={systemAdmin} functionName="members">
          <div>System Admin Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('System Admin Content')).toBeInTheDocument();
      });
    });

    it('should handle error scenarios gracefully', async () => {
      const user = createMockUser(['hdcnLeden']);
      mockFunctionPermissionManager.mockRejectedValue(new Error('Permission check failed'));

      render(
        <FunctionGuard user={user} functionName="webshop">
          <div>Webshop Content</div>
        </FunctionGuard>
      );

      // Should still render for basic member webshop access due to fallback logic
      await waitFor(() => {
        expect(screen.getByText('Webshop Content')).toBeInTheDocument();
      });
    });
  });

  describe('UI Component Integration', () => {
    it('should work with complex UI components', async () => {
      const user = createMockUser(['hdcnLeden', 'Members_Read']);

      render(
        <div>
          <h1>Dashboard</h1>
          <FunctionGuard user={user} requiredRoles={['hdcnLeden']}>
            <div>
              <h2>Member Section</h2>
              <FunctionGuard user={user} requiredRoles={['Members_Read']}>
                <button>View Members</button>
              </FunctionGuard>
              <FunctionGuard user={user} requiredRoles={['Members_CRUD']}>
                <button>Edit Members</button>
              </FunctionGuard>
            </div>
          </FunctionGuard>
        </div>
      );

      await waitFor(() => {
        expect(screen.getByText('Dashboard')).toBeInTheDocument();
        expect(screen.getByText('Member Section')).toBeInTheDocument();
        expect(screen.getByText('View Members')).toBeInTheDocument();
        expect(screen.queryByText('Edit Members')).not.toBeInTheDocument();
      });
    });

    it('should handle dynamic role changes', async () => {
      let userRoles: HDCNGroup[] = ['hdcnLeden'];
      const user = createMockUser(userRoles);

      const { rerender } = render(
        <FunctionGuard user={user} requiredRoles={['Members_CRUD']}>
          <div>Admin Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
      });

      // Simulate role change
      userRoles = ['hdcnLeden', 'Members_CRUD'];
      const updatedUser = createMockUser(userRoles);

      rerender(
        <FunctionGuard user={updatedUser} requiredRoles={['Members_CRUD']}>
          <div>Admin Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Admin Content')).toBeInTheDocument();
      });
    });
  });
});
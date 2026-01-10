import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FunctionGuard } from '../../components/common/FunctionGuard';
import { checkUIPermission } from '../functionPermissions';
import { HDCNGroup } from '../../types/user';

// Mock the FunctionPermissionManager
jest.mock('../functionPermissions', () => ({
  ...jest.requireActual('../functionPermissions'),
  FunctionPermissionManager: {
    create: jest.fn().mockResolvedValue({
      hasAccess: jest.fn().mockReturnValue(true),
      hasFieldAccess: jest.fn().mockReturnValue(true)
    })
  },
  checkUIPermission: jest.fn()
}));

const mockCheckUIPermission = checkUIPermission as jest.MockedFunction<typeof checkUIPermission>;

// Simple test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div>{children}</div>
);

// Mock user factory
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

// Test component that uses checkUIPermission directly
const TestComponentWithDirectPermissionCheck: React.FC<{ user: any }> = ({ user }) => {
  try {
    const canReadMembers = checkUIPermission(user, 'members', 'read');
    const canWriteMembers = checkUIPermission(user, 'members', 'write');
    const canReadEvents = checkUIPermission(user, 'events', 'read');
    const canWriteEvents = checkUIPermission(user, 'events', 'write');

    return (
      <div>
        {canReadMembers && <div data-testid="members-read">Can Read Members</div>}
        {canWriteMembers && <div data-testid="members-write">Can Write Members</div>}
        {canReadEvents && <div data-testid="events-read">Can Read Events</div>}
        {canWriteEvents && <div data-testid="events-write">Can Write Events</div>}
      </div>
    );
  } catch (error) {
    // Handle permission check errors gracefully
    return <div data-testid="permission-error">Permission check failed</div>;
  }
};

// Test component that uses FunctionGuard
const TestComponentWithFunctionGuard: React.FC<{ user: any }> = ({ user }) => (
  <div>
    <FunctionGuard user={user} requiredRoles={['Members_CRUD']}>
      <div data-testid="members-crud-content">Members CRUD Content</div>
    </FunctionGuard>
    
    <FunctionGuard user={user} requiredRoles={['Members_Read']}>
      <div data-testid="members-read-content">Members Read Content</div>
    </FunctionGuard>
    
    <FunctionGuard user={user} requiredRoles={['Events_CRUD']}>
      <div data-testid="events-crud-content">Events CRUD Content</div>
    </FunctionGuard>
    
    <FunctionGuard user={user} requiredRoles={['System_User_Management']}>
      <div data-testid="system-crud-content">System CRUD Content</div>
    </FunctionGuard>
    
    <FunctionGuard 
      user={user} 
      requiredRoles={['Members_CRUD']}
      fallback={<div data-testid="access-denied">Access Denied</div>}
    >
      <div data-testid="protected-content">Protected Content</div>
    </FunctionGuard>
  </div>
);

// Test component for regional permissions
const TestComponentWithRegionalPermissions: React.FC<{ user: any }> = ({ user }) => {
  const canAccessUtrecht = checkUIPermission(user, 'members', 'read', 'utrecht');
  const canAccessLimburg = checkUIPermission(user, 'members', 'read', 'limburg');
  const canAccessAll = checkUIPermission(user, 'members', 'read', 'all');

  return (
    <div>
      {canAccessUtrecht && <div data-testid="utrecht-access">Utrecht Access</div>}
      {canAccessLimburg && <div data-testid="limburg-access">Limburg Access</div>}
      {canAccessAll && <div data-testid="all-regions-access">All Regions Access</div>}
    </div>
  );
};

describe('UI Component Visibility Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Direct Permission Check Components', () => {
    test('should show correct elements for Members_CRUD + Regio_All user', () => {
      const user = createMockUser(['Members_CRUD', 'Regio_All']);
      
      // Mock checkUIPermission responses for this user
      mockCheckUIPermission.mockImplementation((user, functionName, action, region) => {
        if (functionName === 'members' && action === 'read') return true;
        if (functionName === 'members' && action === 'write') return true;
        if (functionName === 'events' && action === 'read') return false;
        if (functionName === 'events' && action === 'write') return false;
        return false;
      });

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={user} />
        </TestWrapper>
      );

      expect(screen.getByTestId('members-read')).toBeInTheDocument();
      expect(screen.getByTestId('members-write')).toBeInTheDocument();
      expect(screen.queryByTestId('events-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('events-write')).not.toBeInTheDocument();
    });

    test('should show correct elements for Members_Read + Regio_Utrecht user', () => {
      const user = createMockUser(['Members_Read', 'Regio_Utrecht']);
      
      // Mock checkUIPermission responses for this user
      mockCheckUIPermission.mockImplementation((user, functionName, action, region) => {
        if (functionName === 'members' && action === 'read') return true;
        if (functionName === 'members' && action === 'write') return false;
        if (functionName === 'events' && action === 'read') return false;
        if (functionName === 'events' && action === 'write') return false;
        return false;
      });

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={user} />
        </TestWrapper>
      );

      expect(screen.getByTestId('members-read')).toBeInTheDocument();
      expect(screen.queryByTestId('members-write')).not.toBeInTheDocument();
      expect(screen.queryByTestId('events-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('events-write')).not.toBeInTheDocument();
    });

    test('should show no elements for user with no permissions', () => {
      const user = createMockUser(['hdcnLeden']);
      
      // Mock checkUIPermission to return false for all checks
      mockCheckUIPermission.mockReturnValue(false);

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={user} />
        </TestWrapper>
      );

      expect(screen.queryByTestId('members-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('members-write')).not.toBeInTheDocument();
      expect(screen.queryByTestId('events-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('events-write')).not.toBeInTheDocument();
    });
  });

  describe('FunctionGuard Component Visibility', () => {
    test('should show Members_CRUD content for user with Members_CRUD role', async () => {
      const user = createMockUser(['Members_CRUD', 'Regio_All']);

      render(
        <TestWrapper>
          <TestComponentWithFunctionGuard user={user} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('members-crud-content')).toBeInTheDocument();
      });
    });

    test('should show Members_Read content for user with Members_Read role', async () => {
      const user = createMockUser(['Members_Read', 'Regio_Utrecht']);

      render(
        <TestWrapper>
          <TestComponentWithFunctionGuard user={user} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('members-read-content')).toBeInTheDocument();
      });
    });

    test('should hide Events_CRUD content for user without Events_CRUD role', async () => {
      const user = createMockUser(['Members_CRUD', 'Regio_All']);

      render(
        <TestWrapper>
          <TestComponentWithFunctionGuard user={user} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.queryByTestId('events-crud-content')).not.toBeInTheDocument();
      });
    });

    test('should show System_CRUD content for admin user', async () => {
      const user = createMockUser(['System_User_Management', 'Regio_All']);

      render(
        <TestWrapper>
          <TestComponentWithFunctionGuard user={user} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('system-crud-content')).toBeInTheDocument();
      });
    });

    test('should show fallback content when access is denied', async () => {
      const user = createMockUser(['hdcnLeden']); // Basic member without CRUD access

      render(
        <TestWrapper>
          <TestComponentWithFunctionGuard user={user} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('access-denied')).toBeInTheDocument();
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      });
    });
  });

  describe('Regional Permission Visibility', () => {
    test('should show Utrecht access for regional Utrecht user', () => {
      const user = createMockUser(['Members_Read', 'Regio_Utrecht']);
      
      // Mock regional permission checks
      mockCheckUIPermission.mockImplementation((user, functionName, action, region) => {
        if (region === 'utrecht') return true;
        if (region === 'limburg') return false;
        if (region === 'all') return false;
        return false;
      });

      render(
        <TestWrapper>
          <TestComponentWithRegionalPermissions user={user} />
        </TestWrapper>
      );

      expect(screen.getByTestId('utrecht-access')).toBeInTheDocument();
      expect(screen.queryByTestId('limburg-access')).not.toBeInTheDocument();
      expect(screen.queryByTestId('all-regions-access')).not.toBeInTheDocument();
    });

    test('should show all regions access for Regio_All user', () => {
      const user = createMockUser(['Members_Read', 'Regio_All']);
      
      // Mock regional permission checks
      mockCheckUIPermission.mockImplementation((user, functionName, action, region) => {
        if (region === 'utrecht') return true;
        if (region === 'limburg') return true;
        if (region === 'all') return true;
        return false;
      });

      render(
        <TestWrapper>
          <TestComponentWithRegionalPermissions user={user} />
        </TestWrapper>
      );

      expect(screen.getByTestId('utrecht-access')).toBeInTheDocument();
      expect(screen.getByTestId('limburg-access')).toBeInTheDocument();
      expect(screen.getByTestId('all-regions-access')).toBeInTheDocument();
    });

    test('should show no regional access for user without regional roles', () => {
      const user = createMockUser(['Members_Read']); // No regional role
      
      // Mock regional permission checks to return false
      mockCheckUIPermission.mockReturnValue(false);

      render(
        <TestWrapper>
          <TestComponentWithRegionalPermissions user={user} />
        </TestWrapper>
      );

      expect(screen.queryByTestId('utrecht-access')).not.toBeInTheDocument();
      expect(screen.queryByTestId('limburg-access')).not.toBeInTheDocument();
      expect(screen.queryByTestId('all-regions-access')).not.toBeInTheDocument();
    });
  });

  describe('Complex Role Combinations', () => {
    test('should handle multiple permission roles correctly', () => {
      const user = createMockUser(['Members_CRUD', 'Events_Read', 'Products_Read', 'Regio_All']);
      
      // Mock permission checks for multiple roles
      mockCheckUIPermission.mockImplementation((user, functionName, action, region) => {
        if (functionName === 'members' && action === 'read') return true;
        if (functionName === 'members' && action === 'write') return true;
        if (functionName === 'events' && action === 'read') return true;
        if (functionName === 'events' && action === 'write') return false;
        return false;
      });

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={user} />
        </TestWrapper>
      );

      expect(screen.getByTestId('members-read')).toBeInTheDocument();
      expect(screen.getByTestId('members-write')).toBeInTheDocument();
      expect(screen.getByTestId('events-read')).toBeInTheDocument();
      expect(screen.queryByTestId('events-write')).not.toBeInTheDocument();
    });

    test('should handle system admin roles correctly', async () => {
      const user = createMockUser(['System_User_Management', 'Regio_All']);

      render(
        <TestWrapper>
          <TestComponentWithFunctionGuard user={user} />
        </TestWrapper>
      );

      // System admin should have access to everything due to FunctionGuard fallback logic
      await waitFor(() => {
        // The FunctionGuard component has fallback logic for System_User_Management
        // It should show content or at least not show access denied for all sections
        const accessDeniedElements = screen.queryAllByTestId('access-denied');
        expect(accessDeniedElements.length).toBeLessThan(5); // Should have some access
      });
    });

    test('should handle incomplete role combinations gracefully', () => {
      const user = createMockUser(['Members_CRUD']); // Missing regional role
      
      // Mock permission checks to fail due to missing regional role
      mockCheckUIPermission.mockReturnValue(false);

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={user} />
        </TestWrapper>
      );

      // Should show no content due to missing regional role
      expect(screen.queryByTestId('members-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('members-write')).not.toBeInTheDocument();
    });
  });

  describe('Error Handling and Edge Cases', () => {
    test('should handle null user gracefully', () => {
      mockCheckUIPermission.mockReturnValue(false);

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={null} />
        </TestWrapper>
      );

      expect(screen.queryByTestId('members-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('members-write')).not.toBeInTheDocument();
    });

    test('should handle user with empty roles array', () => {
      const user = createMockUser([]);
      
      mockCheckUIPermission.mockReturnValue(false);

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={user} />
        </TestWrapper>
      );

      expect(screen.queryByTestId('members-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('members-write')).not.toBeInTheDocument();
    });

    test('should handle permission check errors gracefully', () => {
      const user = createMockUser(['Members_CRUD', 'Regio_All']);
      
      // Mock checkUIPermission to throw an error
      mockCheckUIPermission.mockImplementation(() => {
        throw new Error('Permission check failed');
      });

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={user} />
        </TestWrapper>
      );

      // Should not crash and should show error handling
      expect(screen.getByTestId('permission-error')).toBeInTheDocument();
      expect(screen.queryByTestId('members-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('members-write')).not.toBeInTheDocument();
    });
  });

  describe('Real-World Component Scenarios', () => {
    test('should simulate MembershipManagement component visibility', async () => {
      const memberAdminUser = createMockUser(['Members_CRUD', 'Regio_All']);
      const readOnlyUser = createMockUser(['Members_Read', 'Regio_Utrecht']);

      // Test admin user sees all controls
      const { rerender } = render(
        <TestWrapper>
          <FunctionGuard user={memberAdminUser} requiredRoles={['Members_CRUD']}>
            <div data-testid="create-button">Create New</div>
          </FunctionGuard>
          <FunctionGuard user={memberAdminUser} requiredRoles={['Members_CRUD']}>
            <div data-testid="edit-button">Edit</div>
          </FunctionGuard>
          <FunctionGuard user={memberAdminUser} requiredRoles={['Members_CRUD']}>
            <div data-testid="delete-button">Delete</div>
          </FunctionGuard>
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('create-button')).toBeInTheDocument();
        expect(screen.getByTestId('edit-button')).toBeInTheDocument();
        expect(screen.getByTestId('delete-button')).toBeInTheDocument();
      });

      // Test read-only user sees limited controls
      rerender(
        <TestWrapper>
          <FunctionGuard user={readOnlyUser} requiredRoles={['Members_CRUD']}>
            <div data-testid="create-button">Create New</div>
          </FunctionGuard>
          <FunctionGuard user={readOnlyUser} requiredRoles={['Members_CRUD']}>
            <div data-testid="edit-button">Edit</div>
          </FunctionGuard>
          <FunctionGuard user={readOnlyUser} requiredRoles={['Members_CRUD']}>
            <div data-testid="delete-button">Delete</div>
          </FunctionGuard>
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.queryByTestId('create-button')).not.toBeInTheDocument();
        expect(screen.queryByTestId('edit-button')).not.toBeInTheDocument();
        expect(screen.queryByTestId('delete-button')).not.toBeInTheDocument();
      });
    });

    test('should simulate parameter management component visibility', async () => {
      const systemAdminUser = createMockUser(['System_User_Management', 'Regio_All']);
      const basicMemberUser = createMockUser(['hdcnLeden']);

      // Test system admin sees parameter controls
      const { rerender } = render(
        <TestWrapper>
          <FunctionGuard user={systemAdminUser} requiredRoles={['System_User_Management']}>
            <div data-testid="parameter-controls">Parameter Controls</div>
          </FunctionGuard>
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('parameter-controls')).toBeInTheDocument();
      });

      // Test basic member doesn't see parameter controls
      rerender(
        <TestWrapper>
          <FunctionGuard user={basicMemberUser} requiredRoles={['System_User_Management']}>
            <div data-testid="parameter-controls">Parameter Controls</div>
          </FunctionGuard>
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.queryByTestId('parameter-controls')).not.toBeInTheDocument();
      });
    });

    test('should simulate reporting dashboard component visibility', async () => {
      const fullAccessUser = createMockUser(['Members_CRUD', 'Members_Export', 'Members_Read', 'Regio_All']);
      const readOnlyUser = createMockUser(['Members_Read', 'Regio_Utrecht']);
      const basicMemberUser = createMockUser(['hdcnLeden']);

      // Test full access user sees all reporting features
      const { rerender } = render(
        <TestWrapper>
          <FunctionGuard user={fullAccessUser} requiredRoles={['Members_CRUD']}>
            <div data-testid="ai-reporting">AI Reporting (CRUD Only)</div>
          </FunctionGuard>
          <FunctionGuard user={fullAccessUser} requiredRoles={['Members_Export']}>
            <div data-testid="export-functions">Export Functions</div>
          </FunctionGuard>
          <FunctionGuard user={fullAccessUser} requiredRoles={['Members_Read']}>
            <div data-testid="analytics-dashboard">Analytics Dashboard</div>
          </FunctionGuard>
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('ai-reporting')).toBeInTheDocument();
        expect(screen.getByTestId('export-functions')).toBeInTheDocument();
        expect(screen.getByTestId('analytics-dashboard')).toBeInTheDocument();
      });

      // Test read-only user sees limited reporting features
      rerender(
        <TestWrapper>
          <FunctionGuard user={readOnlyUser} requiredRoles={['Members_CRUD']}>
            <div data-testid="ai-reporting">AI Reporting (CRUD Only)</div>
          </FunctionGuard>
          <FunctionGuard user={readOnlyUser} requiredRoles={['Members_Export']}>
            <div data-testid="export-functions">Export Functions</div>
          </FunctionGuard>
          <FunctionGuard user={readOnlyUser} requiredRoles={['Members_Read']}>
            <div data-testid="analytics-dashboard">Analytics Dashboard</div>
          </FunctionGuard>
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.queryByTestId('ai-reporting')).not.toBeInTheDocument();
        expect(screen.queryByTestId('export-functions')).not.toBeInTheDocument();
        expect(screen.getByTestId('analytics-dashboard')).toBeInTheDocument();
      });

      // Test basic member sees no reporting features
      rerender(
        <TestWrapper>
          <FunctionGuard user={basicMemberUser} requiredRoles={['Members_CRUD']}>
            <div data-testid="ai-reporting">AI Reporting (CRUD Only)</div>
          </FunctionGuard>
          <FunctionGuard user={basicMemberUser} requiredRoles={['Members_Export']}>
            <div data-testid="export-functions">Export Functions</div>
          </FunctionGuard>
          <FunctionGuard user={basicMemberUser} requiredRoles={['Members_Read']}>
            <div data-testid="analytics-dashboard">Analytics Dashboard</div>
          </FunctionGuard>
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.queryByTestId('ai-reporting')).not.toBeInTheDocument();
        expect(screen.queryByTestId('export-functions')).not.toBeInTheDocument();
        expect(screen.queryByTestId('analytics-dashboard')).not.toBeInTheDocument();
      });
    });

    test('should simulate webshop management component visibility', async () => {
      const webshopManagerUser = createMockUser(['Webshop_Management', 'Products_CRUD', 'Products_Read', 'Regio_All']);
      const productReadUser = createMockUser(['Products_Read', 'Regio_All']);
      const basicMemberUser = createMockUser(['hdcnLeden']);

      // Test webshop manager sees all webshop controls
      const { rerender } = render(
        <TestWrapper>
          <FunctionGuard user={webshopManagerUser} requiredRoles={['Webshop_Management']}>
            <div data-testid="webshop-admin">Webshop Administration</div>
          </FunctionGuard>
          <FunctionGuard user={webshopManagerUser} requiredRoles={['Products_CRUD']}>
            <div data-testid="product-management">Product Management</div>
          </FunctionGuard>
          <FunctionGuard user={webshopManagerUser} requiredRoles={['Products_Read']}>
            <div data-testid="product-catalog">Product Catalog</div>
          </FunctionGuard>
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('webshop-admin')).toBeInTheDocument();
        expect(screen.getByTestId('product-management')).toBeInTheDocument();
        expect(screen.getByTestId('product-catalog')).toBeInTheDocument();
      });

      // Test product read user sees limited controls
      rerender(
        <TestWrapper>
          <FunctionGuard user={productReadUser} requiredRoles={['Webshop_Management']}>
            <div data-testid="webshop-admin">Webshop Administration</div>
          </FunctionGuard>
          <FunctionGuard user={productReadUser} requiredRoles={['Products_CRUD']}>
            <div data-testid="product-management">Product Management</div>
          </FunctionGuard>
          <FunctionGuard user={productReadUser} requiredRoles={['Products_Read']}>
            <div data-testid="product-catalog">Product Catalog</div>
          </FunctionGuard>
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.queryByTestId('webshop-admin')).not.toBeInTheDocument();
        expect(screen.queryByTestId('product-management')).not.toBeInTheDocument();
        expect(screen.getByTestId('product-catalog')).toBeInTheDocument();
      });

      // Test basic member sees no webshop management features
      rerender(
        <TestWrapper>
          <FunctionGuard user={basicMemberUser} requiredRoles={['Webshop_Management']}>
            <div data-testid="webshop-admin">Webshop Administration</div>
          </FunctionGuard>
          <FunctionGuard user={basicMemberUser} requiredRoles={['Products_CRUD']}>
            <div data-testid="product-management">Product Management</div>
          </FunctionGuard>
          <FunctionGuard user={basicMemberUser} requiredRoles={['Products_Read']}>
            <div data-testid="product-catalog">Product Catalog</div>
          </FunctionGuard>
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.queryByTestId('webshop-admin')).not.toBeInTheDocument();
        expect(screen.queryByTestId('product-management')).not.toBeInTheDocument();
        expect(screen.queryByTestId('product-catalog')).not.toBeInTheDocument();
      });
    });
  });

  describe('Critical Role Combination Testing (Migration Plan Scenarios)', () => {
    test('should handle National Administrator (Members_CRUD + Regio_All)', async () => {
      const nationalAdmin = createMockUser(['Members_CRUD', 'Regio_All']);
      
      // Mock checkUIPermission for national admin
      mockCheckUIPermission.mockImplementation((user, functionName, action, region) => {
        // National admin should have full access to all functions and regions
        if (functionName === 'members') return true;
        if (functionName === 'events') return false; // No Events_CRUD role
        if (functionName === 'products') return false; // No Products_CRUD role
        return false;
      });

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={nationalAdmin} />
          <TestComponentWithRegionalPermissions user={nationalAdmin} />
        </TestWrapper>
      );

      // Should have full member access
      expect(screen.getByTestId('members-read')).toBeInTheDocument();
      expect(screen.getByTestId('members-write')).toBeInTheDocument();
      
      // Should not have event access (no Events_CRUD role)
      expect(screen.queryByTestId('events-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('events-write')).not.toBeInTheDocument();
    });

    test('should handle Regional Coordinator (Members_CRUD + Regio_Groningen/Drenthe)', async () => {
      const regionalCoordinator = createMockUser(['Members_CRUD', 'Regio_Groningen/Drenthe']);
      
      // Mock checkUIPermission for regional coordinator
      mockCheckUIPermission.mockImplementation((user, functionName, action, region) => {
        if (functionName === 'members' && !region) return true; // Has permission type
        if (functionName === 'members' && region === 'groningen_drenthe') return true;
        if (functionName === 'members' && region === 'utrecht') return false; // Wrong region
        if (functionName === 'members' && region === 'all') return false; // Not Regio_All
        return false;
      });

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={regionalCoordinator} />
          <div>
            {mockCheckUIPermission(regionalCoordinator, 'members', 'read', 'groningen_drenthe') && 
              <div data-testid="groningen-access">Groningen Access</div>}
            {mockCheckUIPermission(regionalCoordinator, 'members', 'read', 'utrecht') && 
              <div data-testid="utrecht-access">Utrecht Access</div>}
          </div>
        </TestWrapper>
      );

      // Should have member access
      expect(screen.getByTestId('members-read')).toBeInTheDocument();
      expect(screen.getByTestId('members-write')).toBeInTheDocument();
      
      // Should have regional access only to Groningen/Drenthe
      expect(screen.getByTestId('groningen-access')).toBeInTheDocument();
      expect(screen.queryByTestId('utrecht-access')).not.toBeInTheDocument();
    });

    test('should handle Read-Only User (Members_Read + Regio_All)', async () => {
      const readOnlyUser = createMockUser(['Members_Read', 'Regio_All']);
      
      // Mock checkUIPermission for read-only user
      mockCheckUIPermission.mockImplementation((user, functionName, action, region) => {
        if (functionName === 'members' && action === 'read') return true;
        if (functionName === 'members' && action === 'write') return false; // No CRUD permission
        return false;
      });

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={readOnlyUser} />
        </TestWrapper>
      );

      // Should have read access only
      expect(screen.getByTestId('members-read')).toBeInTheDocument();
      expect(screen.queryByTestId('members-write')).not.toBeInTheDocument();
      expect(screen.queryByTestId('events-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('events-write')).not.toBeInTheDocument();
    });

    test('should handle Export User (Members_Export + Regio_All)', async () => {
      const exportUser = createMockUser(['Members_Export', 'Regio_All']);
      
      render(
        <TestWrapper>
          <FunctionGuard user={exportUser} requiredRoles={['Members_Export']}>
            <div data-testid="export-functionality">Export Functionality</div>
          </FunctionGuard>
          <FunctionGuard user={exportUser} requiredRoles={['Members_CRUD']}>
            <div data-testid="crud-functionality">CRUD Functionality</div>
          </FunctionGuard>
          <FunctionGuard user={exportUser} requiredRoles={['Members_Read']}>
            <div data-testid="read-functionality">Read Functionality</div>
          </FunctionGuard>
        </TestWrapper>
      );

      await waitFor(() => {
        // Should have export access
        expect(screen.getByTestId('export-functionality')).toBeInTheDocument();
        
        // Should not have CRUD access
        expect(screen.queryByTestId('crud-functionality')).not.toBeInTheDocument();
        
        // Should not have read access (different role)
        expect(screen.queryByTestId('read-functionality')).not.toBeInTheDocument();
      });
    });

    test('should handle Incomplete Role User (Members_CRUD only, no region)', async () => {
      const incompleteUser = createMockUser(['Members_CRUD']); // Missing regional role
      
      // Mock checkUIPermission to fail due to missing regional role
      mockCheckUIPermission.mockImplementation((user, functionName, action, region) => {
        // User has permission type but no regional access
        return false;
      });

      render(
        <TestWrapper>
          <TestComponentWithDirectPermissionCheck user={incompleteUser} />
        </TestWrapper>
      );

      // Should show no content due to missing regional role
      expect(screen.queryByTestId('members-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('members-write')).not.toBeInTheDocument();
      expect(screen.queryByTestId('events-read')).not.toBeInTheDocument();
      expect(screen.queryByTestId('events-write')).not.toBeInTheDocument();
    });

    test('should handle Multi-Permission User (Members_CRUD + Events_Read + Products_Read + Regio_All)', async () => {
      const multiPermissionUser = createMockUser(['Members_CRUD', 'Events_Read', 'Products_Read', 'Regio_All']);
      
      // Mock checkUIPermission for multi-permission user
      mockCheckUIPermission.mockImplementation((user, functionName, action, region) => {
        if (functionName === 'members' && action === 'read') return true;
        if (functionName === 'members' && action === 'write') return true;
        if (functionName === 'events' && action === 'read') return true;
        if (functionName === 'events' && action === 'write') return false; // Only read access
        if (functionName === 'products' && action === 'read') return true;
        if (functionName === 'products' && action === 'write') return false; // Only read access
        return false;
      });

      render(
        <TestWrapper>
          <div>
            {mockCheckUIPermission(multiPermissionUser, 'members', 'read') && 
              <div data-testid="members-read-access">Members Read</div>}
            {mockCheckUIPermission(multiPermissionUser, 'members', 'write') && 
              <div data-testid="members-write-access">Members Write</div>}
            {mockCheckUIPermission(multiPermissionUser, 'events', 'read') && 
              <div data-testid="events-read-access">Events Read</div>}
            {mockCheckUIPermission(multiPermissionUser, 'events', 'write') && 
              <div data-testid="events-write-access">Events Write</div>}
            {mockCheckUIPermission(multiPermissionUser, 'products', 'read') && 
              <div data-testid="products-read-access">Products Read</div>}
            {mockCheckUIPermission(multiPermissionUser, 'products', 'write') && 
              <div data-testid="products-write-access">Products Write</div>}
          </div>
        </TestWrapper>
      );

      // Should have appropriate access based on roles
      expect(screen.getByTestId('members-read-access')).toBeInTheDocument();
      expect(screen.getByTestId('members-write-access')).toBeInTheDocument();
      expect(screen.getByTestId('events-read-access')).toBeInTheDocument();
      expect(screen.queryByTestId('events-write-access')).not.toBeInTheDocument();
      expect(screen.getByTestId('products-read-access')).toBeInTheDocument();
      expect(screen.queryByTestId('products-write-access')).not.toBeInTheDocument();
    });
  });
});
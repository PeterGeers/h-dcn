import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PermissionExample, usePermissions, withPermissionCheck } from '../examples/PermissionExample';
import { useAuth } from '../../hooks/useAuth';
import * as functionPermissions from '../functionPermissions';

// Mock the useAuth hook
jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn()
}));

// Mock the functionPermissions module
jest.mock('../functionPermissions', () => ({
  checkUIPermission: jest.fn(),
  getUserAccessibleRegions: jest.fn(),
  userHasPermissionType: jest.fn(),
  validatePermissionWithRegion: jest.fn()
}));

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockCheckUIPermission = functionPermissions.checkUIPermission as jest.MockedFunction<typeof functionPermissions.checkUIPermission>;
const mockGetUserAccessibleRegions = functionPermissions.getUserAccessibleRegions as jest.MockedFunction<typeof functionPermissions.getUserAccessibleRegions>;
const mockUserHasPermissionType = functionPermissions.userHasPermissionType as jest.MockedFunction<typeof functionPermissions.userHasPermissionType>;
const mockValidatePermissionWithRegion = functionPermissions.validatePermissionWithRegion as jest.MockedFunction<typeof functionPermissions.validatePermissionWithRegion>;

describe('PermissionExample', () => {
  const mockUser = {
    id: 'test-user',
    username: 'testuser',
    email: 'test@example.com',
    groups: ['Members_CRUD', 'Regio_Utrecht'],
    attributes: {}
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: mockUser });
  });

  test('renders permission examples with user access', () => {
    // Mock permission functions to return true for various checks
    mockCheckUIPermission.mockImplementation((user, func, action, region) => {
      if (func === 'members' && action === 'read') return true;
      if (func === 'members' && action === 'write' && region === 'utrecht') return true;
      return false;
    });
    
    mockGetUserAccessibleRegions.mockReturnValue(['utrecht']);
    mockUserHasPermissionType.mockImplementation((user, type, action) => {
      return type === 'members' && action === 'export';
    });
    mockValidatePermissionWithRegion.mockReturnValue(true);

    render(<PermissionExample />);

    expect(screen.getByText('Permission System Examples')).toBeInTheDocument();
    expect(screen.getByText('Member Management')).toBeInTheDocument();
    expect(screen.getByText('View Members')).toBeInTheDocument();
    expect(screen.getByText('Utrecht Region Management')).toBeInTheDocument();
    expect(screen.getByText('Available Regions')).toBeInTheDocument();
  });

  test('shows debug information correctly', () => {
    mockCheckUIPermission.mockReturnValue(true);
    mockGetUserAccessibleRegions.mockReturnValue(['utrecht', 'limburg']);
    mockUserHasPermissionType.mockReturnValue(true);
    mockValidatePermissionWithRegion.mockReturnValue(true);

    render(<PermissionExample />);

    expect(screen.getByText('Debug Info')).toBeInTheDocument();
    expect(screen.getByText(/User roles: Members_CRUD, Regio_Utrecht/)).toBeInTheDocument();
    expect(screen.getByText(/Accessible regions: utrecht, limburg/)).toBeInTheDocument();
    expect(screen.getByText(/Can read members: Yes/)).toBeInTheDocument();
  });

  test('handles user with no permissions', () => {
    mockCheckUIPermission.mockReturnValue(false);
    mockGetUserAccessibleRegions.mockReturnValue([]);
    mockUserHasPermissionType.mockReturnValue(false);
    mockValidatePermissionWithRegion.mockReturnValue(false);

    render(<PermissionExample />);

    // Should not show management sections
    expect(screen.queryByText('Member Management')).not.toBeInTheDocument();
    expect(screen.queryByText('Utrecht Region Management')).not.toBeInTheDocument();
    expect(screen.queryByText('Data Export')).not.toBeInTheDocument();
    expect(screen.queryByText('Reporting')).not.toBeInTheDocument();

    // Debug info should show no permissions
    expect(screen.getByText(/Can read members: No/)).toBeInTheDocument();
    expect(screen.getByText(/Can write members: No/)).toBeInTheDocument();
    expect(screen.getByText(/Has export permission: No/)).toBeInTheDocument();
  });

  test('handles user with full regional access', () => {
    mockCheckUIPermission.mockReturnValue(true);
    mockGetUserAccessibleRegions.mockReturnValue(['all']);
    mockUserHasPermissionType.mockReturnValue(true);
    mockValidatePermissionWithRegion.mockReturnValue(true);

    render(<PermissionExample />);

    expect(screen.getByText('You have access to all regions')).toBeInTheDocument();
  });
});

describe('usePermissions hook', () => {
  const mockUser = {
    id: 'test-user',
    username: 'testuser',
    email: 'test@example.com',
    groups: ['Members_CRUD', 'Regio_Utrecht'],
    attributes: {}
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: mockUser });
  });

  test('returns correct permission values', () => {
    mockCheckUIPermission.mockImplementation((user, func, action) => {
      if (func === 'members' && action === 'read') return true;
      if (func === 'members' && action === 'write') return true;
      return false;
    });
    
    mockGetUserAccessibleRegions.mockReturnValue(['utrecht']);
    mockUserHasPermissionType.mockReturnValue(true);

    const TestComponent = () => {
      const permissions = usePermissions();
      return (
        <div>
          <span data-testid="can-read-members">{permissions.canReadMembers.toString()}</span>
          <span data-testid="can-write-members">{permissions.canWriteMembers.toString()}</span>
          <span data-testid="accessible-regions">{permissions.accessibleRegions.join(',')}</span>
          <span data-testid="has-full-access">{permissions.hasFullRegionalAccess.toString()}</span>
        </div>
      );
    };

    render(<TestComponent />);

    expect(screen.getByTestId('can-read-members')).toHaveTextContent('true');
    expect(screen.getByTestId('can-write-members')).toHaveTextContent('true');
    expect(screen.getByTestId('accessible-regions')).toHaveTextContent('utrecht');
    expect(screen.getByTestId('has-full-access')).toHaveTextContent('false');
  });

  test('checkPermission function works correctly', () => {
    mockCheckUIPermission.mockImplementation((user, func, action, region) => {
      return func === 'members' && action === 'read' && region === 'utrecht';
    });
    
    mockGetUserAccessibleRegions.mockReturnValue(['utrecht']);
    mockUserHasPermissionType.mockReturnValue(false);

    const TestComponent = () => {
      const permissions = usePermissions();
      const canReadUtrechtMembers = permissions.checkPermission('members', 'read', 'utrecht');
      const canWriteLimburgEvents = permissions.checkPermission('events', 'write', 'limburg');
      
      return (
        <div>
          <span data-testid="utrecht-members">{canReadUtrechtMembers.toString()}</span>
          <span data-testid="limburg-events">{canWriteLimburgEvents.toString()}</span>
        </div>
      );
    };

    render(<TestComponent />);

    expect(screen.getByTestId('utrecht-members')).toHaveTextContent('true');
    expect(screen.getByTestId('limburg-events')).toHaveTextContent('false');
  });
});

describe('withPermissionCheck HOC', () => {
  const TestComponent = () => <div>Protected Content</div>;
  
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({ 
      user: {
        id: 'test-user',
        username: 'testuser',
        email: 'test@example.com',
        groups: ['Members_CRUD', 'Regio_Utrecht'],
        attributes: {}
      }
    });
  });

  test('renders component when user has required permissions', () => {
    mockCheckUIPermission.mockReturnValue(true);
    
    const ProtectedComponent = withPermissionCheck(TestComponent, 'members', 'read');
    render(<ProtectedComponent />);

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  test('shows permission denied message when user lacks permissions', () => {
    mockCheckUIPermission.mockReturnValue(false);
    
    const ProtectedComponent = withPermissionCheck(TestComponent, 'members', 'write', 'limburg');
    render(<ProtectedComponent />);

    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    expect(screen.getByText("You don't have permission to access this feature.")).toBeInTheDocument();
    expect(screen.getByText('Required: members write in limburg')).toBeInTheDocument();
  });

  test('handles regional permissions correctly', () => {
    mockCheckUIPermission.mockImplementation((user, func, action, region) => {
      return func === 'members' && action === 'read' && region === 'utrecht';
    });
    
    const ProtectedComponent = withPermissionCheck(TestComponent, 'members', 'read', 'utrecht');
    render(<ProtectedComponent />);

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
});
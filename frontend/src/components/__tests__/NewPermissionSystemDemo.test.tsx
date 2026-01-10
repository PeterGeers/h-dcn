import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { NewPermissionSystemDemo } from '../examples/NewPermissionSystemDemo';
import { usePermissions } from '../../utils/examples/PermissionExample';

// Mock the usePermissions hook
jest.mock('../../utils/examples/PermissionExample', () => ({
  usePermissions: jest.fn()
}));

const mockUsePermissions = usePermissions as jest.MockedFunction<typeof usePermissions>;

describe('NewPermissionSystemDemo', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders demo title and sections', () => {
    // Mock permissions for a user with full access
    mockUsePermissions.mockReturnValue({
      canReadMembers: true,
      canWriteMembers: true,
      canReadEvents: true,
      canWriteEvents: true,
      canReadProducts: true,
      canWriteProducts: true,
      accessibleRegions: ['all'],
      hasFullRegionalAccess: true,
      hasExportPermission: true,
      checkPermission: jest.fn().mockReturnValue(true),
      validateMultiplePermissions: jest.fn().mockReturnValue(true)
    });

    render(<NewPermissionSystemDemo />);

    // Check main title
    expect(screen.getByText('New Permission + Region Role System Demo')).toBeInTheDocument();
    
    // Check section headers
    expect(screen.getByText('Your Permissions')).toBeInTheDocument();
    expect(screen.getByText('Regional Access')).toBeInTheDocument();
    expect(screen.getByText('Regional Permission Examples')).toBeInTheDocument();
  });

  test('displays correct permissions for user with full access', () => {
    mockUsePermissions.mockReturnValue({
      canReadMembers: true,
      canWriteMembers: true,
      canReadEvents: true,
      canWriteEvents: true,
      canReadProducts: true,
      canWriteProducts: true,
      accessibleRegions: ['all'],
      hasFullRegionalAccess: true,
      hasExportPermission: true,
      checkPermission: jest.fn().mockReturnValue(true),
      validateMultiplePermissions: jest.fn().mockReturnValue(true)
    });

    render(<NewPermissionSystemDemo />);

    // Check that all permissions show as granted (✅) - use getAllByText for multiple matches
    const readPermissions = screen.getAllByText(/Read: ✅/);
    const writePermissions = screen.getAllByText(/Write: ✅/);
    const exportPermissions = screen.getAllByText(/Export: ✅/);
    
    expect(readPermissions.length).toBeGreaterThan(0);
    expect(writePermissions.length).toBeGreaterThan(0);
    expect(exportPermissions.length).toBeGreaterThan(0);
    
    // Check regional access - use more flexible text matching
    expect(screen.getByText('✅ All Regions')).toBeInTheDocument();
    expect(screen.getByText('all')).toBeInTheDocument();
  });

  test('displays correct permissions for user with limited access', () => {
    mockUsePermissions.mockReturnValue({
      canReadMembers: true,
      canWriteMembers: false,
      canReadEvents: false,
      canWriteEvents: false,
      canReadProducts: false,
      canWriteProducts: false,
      accessibleRegions: ['utrecht'],
      hasFullRegionalAccess: false,
      hasExportPermission: false,
      checkPermission: jest.fn((func, action, region) => {
        // Only allow members read in utrecht
        return func === 'members' && action === 'read' && region === 'utrecht';
      }),
      validateMultiplePermissions: jest.fn().mockReturnValue(false)
    });

    render(<NewPermissionSystemDemo />);

    // Check that some permissions show as denied (❌) - use getAllByText for multiple matches
    const writePermissionsDenied = screen.getAllByText(/Write: ❌/);
    const exportPermissionsDenied = screen.getAllByText(/Export: ❌/);
    
    expect(writePermissionsDenied.length).toBeGreaterThan(0);
    expect(exportPermissionsDenied.length).toBeGreaterThan(0);
    
    // Check regional access - use more flexible text matching
    expect(screen.getByText('❌ Limited')).toBeInTheDocument();
    expect(screen.getByText('utrecht')).toBeInTheDocument();
  });

  test('shows management sections based on permissions', () => {
    mockUsePermissions.mockReturnValue({
      canReadMembers: true,
      canWriteMembers: true,
      canReadEvents: false,
      canWriteEvents: false,
      canReadProducts: false,
      canWriteProducts: false,
      accessibleRegions: ['utrecht'],
      hasFullRegionalAccess: false,
      hasExportPermission: true,
      checkPermission: jest.fn().mockReturnValue(false),
      validateMultiplePermissions: jest.fn().mockReturnValue(false)
    });

    render(<NewPermissionSystemDemo />);

    // Should show member management section
    expect(screen.getByText('Member Management Section')).toBeInTheDocument();
    expect(screen.getByText('Edit Members')).toBeInTheDocument();
    expect(screen.getByText('Export Member Data')).toBeInTheDocument();

    // Should not show event or product management sections
    expect(screen.queryByText('Event Management Section')).not.toBeInTheDocument();
    expect(screen.queryByText('Product Management Section')).not.toBeInTheDocument();
  });

  test('shows no access message when user has no permissions', () => {
    mockUsePermissions.mockReturnValue({
      canReadMembers: false,
      canWriteMembers: false,
      canReadEvents: false,
      canWriteEvents: false,
      canReadProducts: false,
      canWriteProducts: false,
      accessibleRegions: [],
      hasFullRegionalAccess: false,
      hasExportPermission: false,
      checkPermission: jest.fn().mockReturnValue(false),
      validateMultiplePermissions: jest.fn().mockReturnValue(false)
    });

    render(<NewPermissionSystemDemo />);

    // Should show no access message
    expect(screen.getByText('No Access')).toBeInTheDocument();
    expect(screen.getByText("You don't have permission to access any management features.")).toBeInTheDocument();
  });

  test('displays regional permission examples correctly', () => {
    const mockCheckPermission = jest.fn((func, action, region) => {
      // Grant different permissions for different regions
      if (region === 'utrecht') return func === 'members';
      if (region === 'limburg') return func === 'events';
      return false;
    });

    mockUsePermissions.mockReturnValue({
      canReadMembers: true,
      canWriteMembers: false,
      canReadEvents: true,
      canWriteEvents: false,
      canReadProducts: false,
      canWriteProducts: false,
      accessibleRegions: ['utrecht', 'limburg'],
      hasFullRegionalAccess: false,
      hasExportPermission: false,
      checkPermission: mockCheckPermission,
      validateMultiplePermissions: jest.fn().mockReturnValue(false)
    });

    render(<NewPermissionSystemDemo />);

    // Check that regional examples are displayed
    expect(screen.getByText('Utrecht')).toBeInTheDocument();
    expect(screen.getByText('Limburg')).toBeInTheDocument();
    expect(screen.getByText('Groningen_drenthe')).toBeInTheDocument();

    // Verify checkPermission is called for regional examples
    expect(mockCheckPermission).toHaveBeenCalledWith('members', 'read', 'utrecht');
    expect(mockCheckPermission).toHaveBeenCalledWith('members', 'write', 'utrecht');
    expect(mockCheckPermission).toHaveBeenCalledWith('events', 'read', 'utrecht');
    expect(mockCheckPermission).toHaveBeenCalledWith('events', 'write', 'utrecht');
  });
});
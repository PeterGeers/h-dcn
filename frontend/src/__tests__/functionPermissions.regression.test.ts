/**
 * Regression Tests for FunctionPermissionManager
 * Validates the fix for event-admin-permissions-fix bugfix spec.
 * 
 * Requirements covered:
 * - 2.1: Events_CRUD users can edit events
 * - 2.2: Events_CRUD users can delete events
 * - 3.1: Users without Events_CRUD/Events_Read get denied
 * - 3.2: Events_Read users cannot write
 */
import { FunctionPermissionManager, calculatePermissions } from '../utils/functionPermissions';

describe('FunctionPermissionManager regression tests', () => {
  // Helper to create a manager mimicking how create() now works
  const createManager = (roles: string[]) => {
    const mockUser = {
      groups: roles as any[],
      signInUserSession: {
        accessToken: {
          payload: { 'cognito:groups': roles },
        },
      },
    };
    const combinedPermissions = calculatePermissions(roles);
    return new FunctionPermissionManager(mockUser, combinedPermissions);
  };

  describe('Events_CRUD role permissions', () => {
    it('hasAccess("events", "write") returns true for Events_CRUD user', () => {
      const manager = createManager(['Events_CRUD', 'Regio_All']);
      expect(manager.hasAccess('events', 'write')).toBe(true);
    });

    it('hasAccess("events", "read") returns true for Events_CRUD user', () => {
      const manager = createManager(['Events_CRUD', 'Regio_All']);
      expect(manager.hasAccess('events', 'read')).toBe(true);
    });
  });

  describe('Events_Read role permissions', () => {
    it('hasAccess("events", "read") returns true for Events_Read user', () => {
      const manager = createManager(['Events_Read', 'Regio_Utrecht']);
      expect(manager.hasAccess('events', 'read')).toBe(true);
    });

    it('hasAccess("events", "write") returns false for Events_Read user (no CRUD)', () => {
      const manager = createManager(['Events_Read', 'Regio_Utrecht']);
      expect(manager.hasAccess('events', 'write')).toBe(false);
    });
  });

  describe('Users without event permissions', () => {
    it('hasAccess("events", "write") returns false for user with only hdcnLeden role', () => {
      const manager = createManager(['hdcnLeden']);
      expect(manager.hasAccess('events', 'write')).toBe(false);
    });

    it('hasAccess("events", "read") returns true for Members_Read user (Members_Read grants events.read)', () => {
      // Members_Read in ROLE_PERMISSIONS has events: { read: ['all'] }
      const manager = createManager(['Members_Read', 'Regio_Utrecht']);
      expect(manager.hasAccess('events', 'read')).toBe(true);
    });

    it('hasAccess("events", "write") returns false for user without Events_CRUD', () => {
      const manager = createManager(['Members_CRUD', 'Regio_All']);
      // Members_CRUD does NOT grant events write access
      expect(manager.hasAccess('events', 'write')).toBe(false);
    });
  });

  describe('Multiple roles combined', () => {
    it('hasAccess works with full admin role set (like webmaster@h-dcn.nl)', () => {
      const webmasterRoles = [
        'Events_CRUD', 'Events_Read', 'Events_Export',
        'Members_CRUD', 'Members_Read', 'Members_Export', 'Members_Status_Approve',
        'Products_CRUD', 'Products_Read', 'Products_Export',
        'Communication_CRUD', 'Communication_Read', 'Communication_Export',
        'System_User_Management', 'System_Logs_Read',
        'Webshop_Management', 'Regio_All', 'hdcnLeden'
      ];
      const manager = createManager(webmasterRoles);
      
      expect(manager.hasAccess('events', 'write')).toBe(true);
      expect(manager.hasAccess('events', 'read')).toBe(true);
      expect(manager.hasAccess('members', 'write')).toBe(true);
      expect(manager.hasAccess('members', 'read')).toBe(true);
      expect(manager.hasAccess('products', 'write')).toBe(true);
    });
  });
});

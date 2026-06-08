/**
 * Bug Condition Exploration Test
 * 
 * This test proves that the bug exists in `FunctionPermissionManager`:
 * - `FunctionPermissionManager.create()` passes raw `ROLE_PERMISSIONS` (keyed by role names)
 *   to the constructor, but `hasAccess('events', 'write')` looks up `this.permissions['events']`
 *   which doesn't exist because the top-level keys are role names like 'Events_CRUD'.
 * - The `calculatePermissions()` function exists but is never called in the factory methods.
 * 
 * **Validates: Requirements 1.1, 1.2**
 */
import { FunctionPermissionManager, ROLE_PERMISSIONS, calculatePermissions } from '../utils/functionPermissions';

describe('Bug Condition Exploration: FunctionPermissionManager permission resolution', () => {
  const mockUser = {
    groups: ['Events_CRUD', 'Regio_All'] as any[],
    signInUserSession: {
      accessToken: {
        payload: {
          'cognito:groups': ['Events_CRUD', 'Regio_All'],
        },
      },
    },
  };

  it('BUG: hasAccess("events", "write") returns FALSE with raw ROLE_PERMISSIONS (proving the bug exists)', () => {
    // This reproduces the bug: passing ROLE_PERMISSIONS directly to constructor
    // ROLE_PERMISSIONS is keyed by role names (Events_CRUD, Members_CRUD, etc.)
    // but hasAccess looks up by function name ('events', 'members', etc.)
    const permissionManager = new FunctionPermissionManager(mockUser, ROLE_PERMISSIONS);

    // This SHOULD return true for a user with Events_CRUD,
    // but returns false because this.permissions['events'] is undefined
    // (the keys are 'Events_CRUD', 'hdcnLeden', etc. — not 'events')
    const result = permissionManager.hasAccess('events', 'write');

    // Assert it returns FALSE — proving the bug exists
    expect(result).toBe(false);
  });

  it('calculatePermissions correctly merges Events_CRUD into function-keyed structure', () => {
    // The fix function exists but is never called in the factory methods
    const combinedPermissions = calculatePermissions(['Events_CRUD', 'Regio_All']);

    // calculatePermissions correctly produces function-keyed permissions
    expect(combinedPermissions).toHaveProperty('events');
    expect(combinedPermissions.events).toEqual(
      expect.objectContaining({ write: ['all'] })
    );
    expect(combinedPermissions.events.read).toEqual(expect.arrayContaining(['all']));
  });

  it('FIX PATH: calculatePermissions output has correct function-keyed structure that hasAccess can look up', () => {
    // This demonstrates that calculatePermissions produces the correct structure
    // that hasAccess can find (function-keyed instead of role-keyed)
    const combinedPermissions = calculatePermissions(['Events_CRUD', 'Regio_All']);
    const fixedManager = new FunctionPermissionManager(mockUser, combinedPermissions);

    // With calculatePermissions output, at least the lookup finds the 'events' key
    // (unlike with raw ROLE_PERMISSIONS where 'events' key doesn't exist at all)
    // The hasAccess method still needs the user's groups to match the allowedGroups values,
    // which is a separate concern from the bug being explored here
    expect(combinedPermissions['events']).toBeDefined();
    expect(combinedPermissions['events'].write).toContain('all');

    // Verify the raw ROLE_PERMISSIONS does NOT have 'events' as a top-level key
    // (it has role names like 'Events_CRUD' instead)
    expect(ROLE_PERMISSIONS['events']).toBeUndefined();
    expect(ROLE_PERMISSIONS['Events_CRUD']).toBeDefined();
  });

  it('FIX VERIFIED: hasAccess("events", "write") returns TRUE after fix (calculatePermissions + "all" handling)', () => {
    // This test verifies the complete fix works as the create() factory now does:
    // 1. calculatePermissions() merges roles into function-keyed structure
    // 2. hasAccess() now handles 'all' as a special permission value (like hasFieldAccess does)
    const combinedPermissions = calculatePermissions(['Events_CRUD', 'Regio_All']);
    const manager = new FunctionPermissionManager(mockUser, combinedPermissions);

    // After fix: hasAccess correctly resolves 'all' permission for Events_CRUD users
    expect(manager.hasAccess('events', 'write')).toBe(true);
    expect(manager.hasAccess('events', 'read')).toBe(true);
  });
});

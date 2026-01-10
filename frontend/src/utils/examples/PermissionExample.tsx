import React from 'react';
import { useAuth } from '../../hooks/useAuth';
import { 
  checkUIPermission, 
  getUserAccessibleRegions, 
  userHasPermissionType,
  validatePermissionWithRegion 
} from '../functionPermissions';

/**
 * Example component demonstrating how to use the new permission + region role system
 * This shows the recommended patterns for checking permissions in UI components
 */
export const PermissionExample: React.FC = () => {
  const { user } = useAuth();

  // Example 1: Simple permission check for UI visibility
  const canReadMembers = checkUIPermission(user, 'members', 'read');
  const canWriteMembers = checkUIPermission(user, 'members', 'write');

  // Example 2: Regional permission check for specific region
  const canManageUtrechtMembers = checkUIPermission(user, 'members', 'write', 'utrecht');
  const canViewLimburgEvents = checkUIPermission(user, 'events', 'read', 'limburg');

  // Example 3: Get user's accessible regions for dynamic UI
  const accessibleRegions = getUserAccessibleRegions(user);
  const hasFullAccess = accessibleRegions.includes('all');

  // Example 4: Check specific permission types without region
  const hasExportPermission = userHasPermissionType(user, 'members', 'export');
  const hasEventCRUD = userHasPermissionType(user, 'events', 'crud');

  // Example 5: Validate multiple permissions for complex operations
  const canGenerateReports = validatePermissionWithRegion(
    user,
    ['members_read', 'members_export'],
    'utrecht'
  );

  return (
    <div>
      <h2>Permission System Examples</h2>
      
      {/* Basic permission-based UI visibility */}
      {canReadMembers && (
        <div>
          <h3>Member Management</h3>
          <button>View Members</button>
          {canWriteMembers && <button>Edit Members</button>}
        </div>
      )}

      {/* Regional permission-based UI */}
      {canManageUtrechtMembers && (
        <div>
          <h3>Utrecht Region Management</h3>
          <button>Manage Utrecht Members</button>
        </div>
      )}

      {/* Dynamic region selection based on user access */}
      <div>
        <h3>Available Regions</h3>
        {hasFullAccess ? (
          <p>You have access to all regions</p>
        ) : (
          <ul>
            {accessibleRegions.map(region => (
              <li key={region}>
                {region}
                {checkUIPermission(user, 'events', 'read', region) && (
                  <span> - Can view events</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Feature-specific permissions */}
      {hasExportPermission && (
        <div>
          <h3>Data Export</h3>
          <button>Export Member Data</button>
        </div>
      )}

      {/* Complex operation permissions */}
      {canGenerateReports && (
        <div>
          <h3>Reporting</h3>
          <button>Generate Utrecht Member Report</button>
        </div>
      )}

      {/* Debug information (remove in production) */}
      <div style={{ marginTop: '20px', padding: '10px', backgroundColor: '#f5f5f5' }}>
        <h4>Debug Info</h4>
        <p>User roles: {user?.groups?.join(', ') || 'None'}</p>
        <p>Accessible regions: {accessibleRegions.join(', ') || 'None'}</p>
        <p>Can read members: {canReadMembers ? 'Yes' : 'No'}</p>
        <p>Can write members: {canWriteMembers ? 'Yes' : 'No'}</p>
        <p>Has export permission: {hasExportPermission ? 'Yes' : 'No'}</p>
      </div>
    </div>
  );
};

/**
 * Example of a higher-order component that wraps permission checking
 */
export const withPermissionCheck = (
  WrappedComponent: React.ComponentType<any>,
  requiredPermission: string,
  requiredAction: 'read' | 'write' = 'read',
  requiredRegion?: string
) => {
  return (props: any) => {
    const { user } = useAuth();
    
    if (!checkUIPermission(user, requiredPermission, requiredAction, requiredRegion)) {
      return (
        <div>
          <p>You don't have permission to access this feature.</p>
          <p>Required: {requiredPermission} {requiredAction} {requiredRegion ? `in ${requiredRegion}` : ''}</p>
        </div>
      );
    }
    
    return <WrappedComponent {...props} />;
  };
};

/**
 * Example usage of the HOC
 */
const MemberManagementComponent = () => <div>Member Management Interface</div>;
export const ProtectedMemberManagement = withPermissionCheck(
  MemberManagementComponent,
  'members',
  'write'
);

/**
 * Example of a custom hook for permission checking
 */
export const usePermissions = () => {
  const { user } = useAuth();
  
  return {
    // Basic permission checks
    canReadMembers: checkUIPermission(user, 'members', 'read'),
    canWriteMembers: checkUIPermission(user, 'members', 'write'),
    canReadEvents: checkUIPermission(user, 'events', 'read'),
    canWriteEvents: checkUIPermission(user, 'events', 'write'),
    canReadProducts: checkUIPermission(user, 'products', 'read'),
    canWriteProducts: checkUIPermission(user, 'products', 'write'),
    
    // Regional information
    accessibleRegions: getUserAccessibleRegions(user),
    hasFullRegionalAccess: getUserAccessibleRegions(user).includes('all'),
    
    // Permission type checks
    hasExportPermission: userHasPermissionType(user, 'members', 'export'),
    hasSystemAccess: userHasPermissionType(user, 'system', 'read'),
    
    // Utility functions
    checkPermission: (functionName: string, action: 'read' | 'write' = 'read', region?: string) =>
      checkUIPermission(user, functionName, action, region),
    
    validateMultiplePermissions: (permissions: string[], region?: string) =>
      validatePermissionWithRegion(user, permissions, region)
  };
};
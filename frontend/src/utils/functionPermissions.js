import { getParameters } from './parameterService';

// Function Permission Manager using existing parameter table
export class FunctionPermissionManager {
  constructor(user, permissionConfig = {}) {
    this.userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
    this.permissions = permissionConfig;
  }

  hasAccess(functionName, action = 'read') {
    const functionPerms = this.permissions[functionName];
    if (!functionPerms) return false;

    const allowedGroups = functionPerms[action] || [];
    
    return this.userGroups.some(userGroup => {
      return allowedGroups.some(allowedGroup => {
        // Handle wildcard patterns like hdcnRegio_*
        if (allowedGroup.endsWith('*')) {
          const prefix = allowedGroup.slice(0, -1);
          return userGroup.startsWith(prefix);
        }
        return userGroup === allowedGroup;
      });
    });
  }

  static async create(user) {
    const userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
    const isAdmin = userGroups.includes('hdcnAdmins');
    
    console.log('🔍 FunctionPermissionManager.create - User groups:', userGroups);
    console.log('🔍 FunctionPermissionManager.create - Is admin:', isAdmin);
    
    try {
      // Wait a bit for initialization to complete
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Test direct API call
      try {
        const apiResponse = await fetch('https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/parameters');
        const apiData = await apiResponse.json();
        console.log('🔍 Direct API call - all parameters:', apiData.map(p => p.name));
        const functionPermsFromAPI = apiData.find(p => p.name === 'function_permissions');
        console.log('🔍 Direct API - function_permissions:', functionPermsFromAPI);
      } catch (apiError) {
        console.log('🔍 API call failed:', apiError);
      }
      
      const parameters = await getParameters();
      console.log('🔍 Parameters loaded:', Object.keys(parameters));
      
      const functionPermissions = parameters['Function_permissions'] || [];
      console.log('🔍 Function permissions raw:', functionPermissions);
      
      // Find the function_permissions parameter
      const permissionParam = functionPermissions.find(p => p.value && typeof p.value === 'object');
      let config = permissionParam?.value || {};
      
      // If config is empty but user is admin, use fallback
      if (Object.keys(config).length === 0 && isAdmin) {
        console.log('🔄 Using fallback config for admin');
        config = {
          members: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
          events: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
          products: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
          orders: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
          webshop: { read: ['hdcnLeden', 'hdcnAdmins'], write: ['hdcnLeden', 'hdcnAdmins'] },
          parameters: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
          memberships: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] }
        };
      }
      
      console.log('🔍 Final permission config:', config);
      
      return new FunctionPermissionManager(user, config);
    } catch (error) {
      console.error('❌ Failed to load function permissions:', error);
      
      // Fallback: If admin, allow everything. Otherwise, basic permissions.
      const fallbackConfig = isAdmin ? {
        members: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
        events: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
        products: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
        orders: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
        webshop: { read: ['hdcnLeden', 'hdcnAdmins'], write: ['hdcnLeden', 'hdcnAdmins'] },
        parameters: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
        memberships: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] }
      } : {
        webshop: { read: ['hdcnLeden'], write: ['hdcnLeden'] }
      };
      
      return new FunctionPermissionManager(user, fallbackConfig);
    }
  }

  // Get all accessible functions for current user
  getAccessibleFunctions() {
    const accessible = {};
    
    Object.keys(this.permissions).forEach(functionName => {
      accessible[functionName] = {
        read: this.hasAccess(functionName, 'read'),
        write: this.hasAccess(functionName, 'write')
      };
    });
    
    return accessible;
  }
}

// Default function permissions template for parameter table
export const DEFAULT_FUNCTION_PERMISSIONS = {
  id: 'default',
  value: {
    members: {
      read: ['hdcnAdmins', 'hdcnRegio_*'],
      write: ['hdcnAdmins']
    },
    events: {
      read: ['hdcnAdmins', 'hdcnEvents_Read'],
      write: ['hdcnAdmins', 'hdcnEvents_Write']
    },
    products: {
      read: ['hdcnAdmins', 'hdcnProducts_Read'],
      write: ['hdcnAdmins', 'hdcnProducts_Write']
    },
    orders: {
      read: ['hdcnAdmins', 'hdcnOrders_Read'],
      write: ['hdcnAdmins', 'hdcnOrders_Write']
    },
    webshop: {
      read: ['hdcnLeden', 'hdcnAdmins'],
      write: ['hdcnLeden', 'hdcnAdmins']
    },
    parameters: {
      read: ['hdcnAdmins'],
      write: ['hdcnAdmins']
    },
    memberships: {
      read: ['hdcnAdmins'],
      write: ['hdcnAdmins']
    }
  }
};
// Test script for function permissions
import { FunctionPermissionManager } from './src/utils/functionPermissions.js';

// Mock user with different group combinations
const testUsers = [
  {
    name: 'Admin User',
    signInUserSession: {
      accessToken: {
        payload: {
          'cognito:groups': ['hdcnAdmins']
        }
      }
    }
  },
  {
    name: 'Member User',
    signInUserSession: {
      accessToken: {
        payload: {
          'cognito:groups': ['hdcnLeden']
        }
      }
    }
  },
  {
    name: 'Regional Admin',
    signInUserSession: {
      accessToken: {
        payload: {
          'cognito:groups': ['hdcnRegio_Amsterdam']
        }
      }
    }
  },
  {
    name: 'Events Manager',
    signInUserSession: {
      accessToken: {
        payload: {
          'cognito:groups': ['hdcnEvents_Read', 'hdcnEvents_Write']
        }
      }
    }
  }
];

// Test function permissions
const testPermissions = async () => {
  console.log('🧪 Testing Function Permissions\n');
  
  for (const user of testUsers) {
    console.log(`👤 Testing user: ${user.name}`);
    console.log(`   Groups: ${user.signInUserSession.accessToken.payload['cognito:groups'].join(', ')}`);
    
    try {
      const permissions = await FunctionPermissionManager.create(user);
      
      const functions = ['members', 'events', 'products', 'webshop', 'parameters'];
      const actions = ['read', 'write'];
      
      functions.forEach(func => {
        actions.forEach(action => {
          const hasAccess = permissions.hasAccess(func, action);
          const status = hasAccess ? '✅' : '❌';
          console.log(`   ${status} ${func}:${action}`);
        });
      });
      
      console.log('');
    } catch (error) {
      console.error(`   ❌ Error testing ${user.name}:`, error.message);
    }
  }
};

// Run tests
testPermissions().catch(console.error);
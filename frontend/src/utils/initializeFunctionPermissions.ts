import { parameterStore } from './parameterStore';
import { DEFAULT_FUNCTION_PERMISSIONS } from './functionPermissions';

// Initialize function permissions in parameter table if not exists
export const initializeFunctionPermissions = async (): Promise<boolean> => {
  try {
    const parameters = await parameterStore.getParameters();
    
    // Check if function_permissions already exists
    if (!parameters.function_permissions || parameters.function_permissions.length === 0) {
      
      // Add default function permissions
      const updatedParameters = {
        ...parameters,
        function_permissions: [DEFAULT_FUNCTION_PERMISSIONS]
      };
      
      await parameterStore.saveParameters(updatedParameters);
      
      return true;
    }
    
    console.log('Function permissions already exist');
    return false;
  } catch (error) {
    console.error('Failed to initialize function permissions:', error);
    throw error;
  }
};
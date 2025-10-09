// Simple test to check if function permissions work
console.log('🧪 Testing Function Permissions System');

// Test 1: Check if we can access parameterStore
import('./src/utils/parameterStore.js').then(async ({ parameterStore }) => {
  console.log('✅ ParameterStore imported');
  
  try {
    const params = await parameterStore.getParameters();
    console.log('✅ Parameters loaded:', Object.keys(params));
    
    // Check if function_permissions exists
    if (params.function_permissions) {
      console.log('✅ Function permissions found:', params.function_permissions);
    } else {
      console.log('❌ No function_permissions found');
    }
    
  } catch (error) {
    console.error('❌ Error loading parameters:', error);
  }
}).catch(error => {
  console.error('❌ Failed to import parameterStore:', error);
});
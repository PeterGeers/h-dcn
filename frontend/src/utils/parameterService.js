import React from 'react';
import { parameterStore } from './parameterStore';

// Fetch parameters using parameterStore (which handles S3/DynamoDB/localStorage fallbacks)
export const getParameters = async () => {
  try {
    // Force refresh to ensure we get latest data
    await parameterStore.refresh();
    const params = await parameterStore.getParameters();
    console.log('🔍 parameterService.getParameters result:', Object.keys(params));
    console.log('🔍 Function_permissions in params:', params.Function_permissions);
    return params;
  } catch (error) {
    console.error('Error loading parameters:', error);
    throw new Error('Fout bij laden parameters: ' + error.message);
  }
};

// Clear parameter cache
export const clearParameterCache = () => {
  parameterStore.clearCache();
};

// Save parameter using parameterStore
export const saveParameter = async (category, value, id = null) => {
  try {
    const parameters = await getParameters();
    
    if (!parameters[category]) {
      parameters[category] = [];
    }
    
    if (id) {
      // Update existing
      const index = parameters[category].findIndex(item => item.id === id);
      if (index !== -1) {
        parameters[category][index].value = value;
      }
    } else {
      // Add new
      const newId = crypto.randomUUID();
      parameters[category].push({ id: newId, value });
    }
    
    await parameterStore.saveParameters(parameters);
  } catch (error) {
    throw new Error('Fout bij opslaan parameter: ' + error.message);
  }
};

// Memoized conversion function
const memoizedConversions = new Map();

// Category-specific converters
const categoryConverters = {
  Productgroepen: (items) => items.map(item => {
    try {
      const parsed = JSON.parse(item.value);
      return { id: item.id, value: parsed.value, parent: parsed.parent };
    } catch {
      return item;
    }
  })
};

const convertToFlatStructure = (data) => {
  const cacheKey = JSON.stringify(data);
  if (memoizedConversions.has(cacheKey)) {
    return memoizedConversions.get(cacheKey);
  }
  
  const flat = { ...data };
  
  // Apply category-specific conversions
  for (const [category, converter] of Object.entries(categoryConverters)) {
    if (flat[category]) {
      flat[category] = converter(flat[category]);
    }
  }
  
  memoizedConversions.set(cacheKey, flat);
  return flat;
};

// Delete parameter using parameterStore
export const deleteParameter = async (category, id) => {
  try {
    const parameters = await getParameters();
    
    if (parameters[category]) {
      parameters[category] = parameters[category].filter(item => item.id !== id);
    }
    
    await parameterStore.saveParameters(parameters);
  } catch (error) {
    throw new Error('Fout bij verwijderen parameter: ' + error.message);
  }
};

// Hook for using parameters in components with memoization
export const useParameters = (category) => {
  const [parameters, setParameters] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  
  const loadParams = React.useCallback(async () => {
    try {
      const data = await getParameters();
      setParameters(data[category] || []);
    } catch (error) {
      console.error('Error loading parameters:', error);
    } finally {
      setLoading(false);
    }
  }, [category]);
  
  React.useEffect(() => {
    loadParams();
  }, [loadParams]);
  
  return React.useMemo(() => ({ parameters, loading }), [parameters, loading]);
};
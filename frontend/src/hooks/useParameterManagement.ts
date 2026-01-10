/**
 * Custom hook for parameter management
 */

import { useState, useEffect, useCallback } from 'react';
import { useToast } from '@chakra-ui/react';
import { Parameters } from '../services/parameterService';

export const useParameterManagement = (hasAccess: boolean, accessLoading: boolean) => {
  const [parameters, setParameters] = useState<Parameters>({});
  const [dataSource, setDataSource] = useState('loading');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const toast = useToast();

  const loadParameters = useCallback(async () => {
    try {
      setDataSource('loading');
      
      // Load parameters directly from S3 bucket
      const s3Url = 'https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/parameters.json';
      const timestamp = new Date().getTime();
      const response = await fetch(`${s3Url}?t=${timestamp}`);
      
      if (!response.ok) {
        throw new Error(`Failed to load parameters from S3: ${response.status}`);
      }
      
      const jsonData = await response.json();
      
      // Convert JSON structure to expected format for Parameter Management
      const formattedParameters: Parameters = {};
      const categoryMetadata: any = {};
      
      // Map JSON keys to display names
      const keyMapping: Record<string, string> = {
        'regio': 'Regio',
        'lidmaatschap': 'Lidmaatschap', 
        'statuslidmaatschap': 'StatusLidmaatschap',
        'motormerk': 'Motormerk',
        'clubblad': 'Clubblad',
        'productgroepen': 'Productgroepen'
      };
      
      // Convert each category
      Object.entries(jsonData).forEach(([key, items]) => {
        const displayName = keyMapping[key] || key.charAt(0).toUpperCase() + key.slice(1);
        
        if (key === 'productgroepen' && typeof items === 'object' && !Array.isArray(items)) {
          // Handle nested productgroepen structure
          const flatArray: any[] = [];
          Object.entries(items as any).forEach(([groupKey, groupData]: [string, any]) => {
            // Add parent item
            flatArray.push({
              id: groupData.id || groupKey,
              value: groupData.value || groupKey,
              parent: null
            });
            
            // Add children
            if (groupData.children) {
              Object.entries(groupData.children).forEach(([childKey, childData]: [string, any]) => {
                flatArray.push({
                  id: childData.id || childKey,
                  value: childData.value || childKey,
                  parent: groupData.id || groupKey
                });
              });
            }
          });
          formattedParameters[displayName] = flatArray;
        } else if (Array.isArray(items)) {
          // Convert simple array format to expected format with IDs
          formattedParameters[displayName] = items.map((item, index) => ({
            id: String(index + 1),
            value: typeof item === 'string' ? item : item.value || '',
            parent: null,
            ...item
          }));
        } else {
          formattedParameters[displayName] = items;
        }
        
        categoryMetadata[displayName] = {
          description: `Configuration data for ${displayName}`,
          created_at: new Date().toISOString(),
          parameter_id: key
        };
      });
      
      formattedParameters._metadata = categoryMetadata;
      setParameters(formattedParameters);
      setHasUnsavedChanges(false); // Reset unsaved changes flag
      setDataSource('S3 Bucket');
      
    } catch (error: any) {
      console.error('❌ Error loading parameters from S3:', error);
      toast({ 
        title: 'Geen toegang tot parameters', 
        description: 'Parameters zijn tijdelijk niet beschikbaar. Probeer het later opnieuw.', 
        status: 'error',
        duration: 5000,
        isClosable: true
      });
      setDataSource('Niet beschikbaar');
      setHasUnsavedChanges(false);
      // Set empty parameters - no fallback data
      setParameters({});
    }
  }, [toast]);

  // Function to update parameters locally (in memory)
  const updateParametersLocally = useCallback((updatedParameters: Parameters) => {
    setParameters(updatedParameters);
    setHasUnsavedChanges(true);
  }, []);

  const saveParameters = useCallback(async (updatedParameters?: Parameters) => {
    try {
      // Use current parameters if none provided
      const parametersToSave = updatedParameters || parameters;
      
      // Convert parameters back to the S3 JSON structure
      const s3Data: any = {};
      
      // Map display names back to JSON keys
      const keyMapping = {
        'Regio': 'regio',
        'Lidmaatschap': 'lidmaatschap',
        'StatusLidmaatschap': 'statuslidmaatschap',
        'Motormerk': 'motormerk',
        'Clubblad': 'clubblad',
        'Geslacht': 'geslacht',
        'WieWatWaar': 'wiewatwaar',
        'Productgroepen': 'productgroepen'
      };
      
      // Remove metadata
      const cleanParameters = { ...parametersToSave };
      delete cleanParameters._metadata;
      
      for (const [displayName, items] of Object.entries(cleanParameters)) {
        const jsonKey = keyMapping[displayName] || displayName.toLowerCase();
        
        if (jsonKey === 'productgroepen' && Array.isArray(items)) {
          // Handle nested productgroepen structure - convert back to S3 nested object format
          const nested: any = {};
          
          // First pass: create parent objects
          for (const item of items) {
            if (typeof item === 'object' && item.parent === null) {
              // This is a parent item
              const parentKey = item.value || item.id || '';
              nested[parentKey] = {
                id: item.id || parentKey,
                value: item.value || parentKey,
                children: {}
              };
            }
          }
          
          // Second pass: add children to their parents
          for (const item of items) {
            if (typeof item === 'object' && item.parent !== null) {
              // This is a child item - find its parent
              const parentItem = items.find(p => p.id === item.parent);
              if (parentItem) {
                const parentKey = parentItem.value || parentItem.id || '';
                const childKey = item.value || item.id || '';
                if (nested[parentKey] && nested[parentKey].children) {
                  nested[parentKey].children[childKey] = {
                    id: item.id || childKey,
                    value: item.value || childKey
                  };
                }
              }
            }
          }
          
          s3Data[jsonKey] = nested;
        } else if (Array.isArray(items)) {
          // Convert back to simple array format
          s3Data[jsonKey] = items.map(item => {
            if (typeof item === 'object' && 'value' in item) {
              return item.value;
            }
            return item;
          });
        } else {
          s3Data[jsonKey] = items;
        }
      }
      
      // Don't update local state here - it's already updated
      // setParameters(updatedParameters);
      
      // Upload directly to S3 via secure backend API
      const apiUrl = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/s3/files';
      
      // Get enhanced groups from localStorage for authentication
      const storedUser = localStorage.getItem('hdcn_auth_user');
      let enhancedGroups = ['System_User_Management']; // fallback with new role structure
      let authToken = '';
      
      if (storedUser) {
        const user = JSON.parse(storedUser);
        
        // Extract JWT token for Authorization header
        const jwtToken = user.signInUserSession?.accessToken?.jwtToken;
        if (jwtToken) {
          authToken = jwtToken;
        }
        
        const groups = user.signInUserSession?.accessToken?.payload?.['cognito:groups'];
        if (groups && Array.isArray(groups)) {
          enhancedGroups = groups;
        }
      } else {
        console.log('⚠️ No stored user found, using fallback groups');
      }
      
      const requestHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Enhanced-Groups': JSON.stringify(enhancedGroups)
      };
      
      // Add Authorization header if we have a token
      if (authToken) {
        requestHeaders['Authorization'] = `Bearer ${authToken}`;
      }
      
      const uploadResponse = await fetch(apiUrl, {
        method: 'POST',
        headers: requestHeaders,
        body: JSON.stringify({
          bucketName: 'my-hdcn-bucket',
          fileKey: 'parameters.json',
          fileData: s3Data,
          contentType: 'application/json',
          cacheControl: 'no-cache'
        })
      });
      
      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json().catch(() => ({}));
        throw new Error(errorData.error || `Upload failed: ${uploadResponse.status}`);
      }
      
      const result = await uploadResponse.json();
      
      // Mark as saved
      setHasUnsavedChanges(false);
      
      toast({
        title: 'Parameters opgeslagen',
        description: 'Alle wijzigingen zijn succesvol opgeslagen.',
        status: 'success',
        duration: 3000,
        isClosable: true
      });
      
    } catch (error: any) {
      console.error('❌ Error saving parameters:', error);
      toast({
        title: 'Fout bij opslaan parameters',
        description: error?.message || 'Onbekende fout bij opslaan parameters',
        status: 'error',
        duration: 5000,
        isClosable: true
      });
    }
  }, [parameters, toast]);

  useEffect(() => {
    // Only load parameters if user has access
    if (hasAccess && !accessLoading) {
      loadParameters();
    }
  }, [hasAccess, accessLoading, loadParameters]);

  return {
    parameters,
    dataSource,
    hasUnsavedChanges,
    loadParameters,
    updateParametersLocally,
    saveParameters
  };
};
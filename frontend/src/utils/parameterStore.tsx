import React from 'react';

interface ParameterItem {
  id?: string;
  value?: any;
  parent?: string;
  children?: Record<string, ParameterItem>;
  // Leveropties specific fields
  name?: string;
  cost?: string;
  // Display fields
  displayValue?: string;
}

interface Parameters {
  [category: string]: ParameterItem[] | any;
  _metadata?: Record<string, any>;
}

type ListenerCallback = (cache: Parameters | null) => void;

// Centralized parameter store - ONE source of truth
class ParameterStore {
  static CATEGORY_MAPPING: Record<string, string> = {
    'regio': 'Regio',
    'lidmaatschap': 'Lidmaatschap', 
    'motormerk': 'Motormerk',
    'clubblad': 'Clubblad',
    'wiewatwaar': 'WieWatWaar',
    'productgroepen': 'Productgroepen',
    'function_permissions': 'Function_permissions'
  };

  private cache: Parameters | null = null;
  private categoryMapCache: Map<string, string> | null = null;
  private listeners = new Set<ListenerCallback>();

  constructor() {
    this.cache = null;
    this.categoryMapCache = null;
    this.listeners = new Set();
  }

  // Get parameters from API
  async getParameters(): Promise<Parameters> {
    if (this.cache) {
      return this.cache;
    }

    try {
      // Load form parameters using individual API calls
      const formData = await this.convertApiToFormStructure();
      
      if (formData && Object.keys(formData).length > 0) {
        // BACKWARD COMPATIBILITY: Apply migration and validation
        const migratedData = this.migrateParameterStructure(formData);
        const validation = this.validateParameterCompatibility(migratedData);
        
        if (validation.autoFixApplied) {
          // Parameter compatibility auto-fixes applied
        }
        
        if (!validation.isCompatible) {
          // Parameter compatibility issues detected - continue with auto-fixes applied
          // Continue with the data but log issues for monitoring
        }
        
        this.cache = migratedData;
        try {
          localStorage.setItem('hdcn-form-parameters', JSON.stringify(migratedData));
        } catch (e) {
          console.warn('localStorage write failed:', e.message);
        }
        this.notifyListeners();
        return this.cache;
      }
    } catch (error) {
      console.log('API failed, using localStorage fallback:', error.message);
    }

    // Fallback to localStorage
    const stored = localStorage.getItem('hdcn-form-parameters');
    if (stored) {
      try {
        const data = JSON.parse(stored);
        if (data.Regio && data.Lidmaatschap && data.Motormerk) {
          // BACKWARD COMPATIBILITY: Apply migration and validation to stored data
          const migratedData = this.migrateParameterStructure(data);
          const validation = this.validateParameterCompatibility(migratedData);
          
          if (validation.autoFixApplied) {
            // Save the fixed data back to localStorage
            try {
              localStorage.setItem('hdcn-form-parameters', JSON.stringify(migratedData));
            } catch (e) {
              console.warn('localStorage write failed:', e.message);
            }
          }
          
          this.cache = migratedData;
          this.notifyListeners();
          return this.cache;
        }
      } catch (error) {
        console.log('Invalid localStorage data, applying migration');
      }
    }

    // Final fallback to defaults with compatibility enhancements
    console.log('🔄 Using enhanced defaults with backward compatibility');
    this.cache = this.getDefaults();
    
    // Validate even the defaults to ensure consistency
    const validation = this.validateParameterCompatibility(this.cache);
    if (!validation.isCompatible) {
      console.warn('⚠️ Default parameter structure has compatibility issues:', validation.issues);
    }
    
    try {
      localStorage.setItem('hdcn-form-parameters', JSON.stringify(this.cache));
    } catch (e) {
      console.warn('localStorage write failed:', e.message);
    }
    this.notifyListeners();
    return this.cache;
  }

  // Save parameters to localStorage only (no DynamoDB)
  async saveParameters(data: Parameters): Promise<void> {
    // BACKWARD COMPATIBILITY: Apply migration and validation before saving
    const migratedData = this.migrateParameterStructure(data);
    const validation = this.validateParameterCompatibility(migratedData);
    
    if (validation.autoFixApplied) {
      // Parameter compatibility auto-fixes applied before saving
    }
    
    if (!validation.isCompatible) {
      // Parameter compatibility issues detected before saving - continue with auto-fixes applied
      // Continue with save but log issues for monitoring
    }
    
    this.cache = migratedData;
    try {
      localStorage.setItem('hdcn-form-parameters', JSON.stringify(migratedData));
    } catch (e) {
      console.warn('localStorage write failed:', e.message);
    }
    
    this.notifyListeners();
  }

  // Clear cache and reload
  async refresh(): Promise<Parameters> {
    this.cache = null;
    this.categoryMapCache = null;
    localStorage.removeItem('hdcn-form-parameters');
    return await this.getParameters();
  }

  // Export current data for production
  exportForProduction(): Parameters | null {
    const data = localStorage.getItem('hdcn-form-parameters');
    if (data) {
      console.log('=== COPY THIS TO getDefaults() ===');
      console.log(JSON.stringify(JSON.parse(data), null, 2));
      console.log('=== END COPY ===');
      return JSON.parse(data);
    }
    return null;
  }

  // Subscribe to changes
  subscribe(callback: ListenerCallback): () => boolean {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  // Notify all listeners
  private notifyListeners(): void {
    this.listeners.forEach(callback => callback(this.cache));
  }

  // Helper to get proper category name from API name
  getCategoryName(apiName: string): string | null {
    // Check if it's a known mapping
    if (ParameterStore.CATEGORY_MAPPING[apiName]) {
      return ParameterStore.CATEGORY_MAPPING[apiName];
    }
    
    // For new categories, capitalize first letter
    if (apiName && apiName !== 'api_base_url') {
      return apiName.charAt(0).toUpperCase() + apiName.slice(1);
    }
    
    return null;
  }

  // Load parameters from static JSON file only - NO API calls
  private async convertApiToFormStructure(): Promise<Parameters> {
    try {
      // Load parameters from JSON file in data bucket - no API calls to avoid 500 errors
      // Add timestamp to force cache refresh
      const timestamp = new Date().getTime();
      const version = process.env.REACT_APP_CACHE_VERSION || '1.0';
      const imagesBaseUrl = process.env.REACT_APP_IMAGES_BASE_URL || 'https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com';
      const response = await fetch(`${imagesBaseUrl}/parameters.json?v=${version}&t=${timestamp}`);
      
      if (!response.ok) {
        throw new Error(`Failed to load parameters.json: ${response.status}`);
      }
      
      const jsonData = await response.json();
      
      // Convert JSON structure to expected format
      const formStructure: any = {};
      const categoryMetadata: any = {};
      
      // Map JSON keys to display names
      const keyMapping: Record<string, string> = {
        'regio': 'Regio',
        'lidmaatschap': 'Lidmaatschap', 
        'statuslidmaatschap': 'StatusLidmaatschap',
        'motormerk': 'Motormerk',
        'clubblad': 'Clubblad',
        'wiewatwaar': 'WieWatWaar'
      };
      
      // Convert each category
      Object.entries(jsonData).forEach(([key, items]) => {
        const displayName = keyMapping[key] || key.charAt(0).toUpperCase() + key.slice(1);
        
        if (Array.isArray(items)) {
          // For simple arrays, keep them simple - only add IDs where they're actually needed
          if (key === 'regio') {
            // Regions need IDs for Cognito access control
            formStructure[displayName] = items.map((item, index) => {
              if (typeof item === 'string') {
                return {
                  id: String(index + 1),
                  value: item
                };
              } else {
                return {
                  id: item.id || String(index + 1),
                  value: item.value || '',
                  ...item
                };
              }
            });
          } else {
            // For other arrays, keep them as simple text arrays
            formStructure[displayName] = items.map((item, index) => {
              if (typeof item === 'string') {
                return {
                  value: item
                };
              } else {
                return {
                  id: item.id,
                  value: item.value || '',
                  ...item
                };
              }
            });
          }
        } else {
          formStructure[displayName] = items;
        }
        
        categoryMetadata[displayName] = {
          description: `Configuration data for ${displayName}`,
          parameter_id: key
        };
      });
      
      // Add default function permissions if not present
      if (!formStructure.Function_permissions) {
        formStructure.Function_permissions = this.getDefaults().Function_permissions;
        categoryMetadata.Function_permissions = {
          description: 'Function permissions configuration',
          parameter_id: 'function_permissions'
        };
      }
      
      formStructure._metadata = categoryMetadata;
      return formStructure;
      
    } catch (error) {
      console.error('❌ Error loading parameters from JSON:', error);
      throw error;
    }
  }

  // Helper: Convert nested structure to flat array for dropdowns
  getFlatArray(category: string): ParameterItem[] {
    const data = this.cache?.[category];
    
    if (!data) return [];
    
    if (Array.isArray(data)) {
      return data; // Already flat
    }
    
    // Convert nested object to flat array
    const result = Object.entries(data).flatMap(([key, item]: [string, any]) => {
      const parent = { id: item.id, value: item.value };
      const children = item.children ? Object.values(item.children).map((child: any) => ({
        id: child.id, 
        value: child.value, 
        parent: item.id
      })) : [];
      return [parent, ...children];
    });
    
    return result;
  }

  // Helper: Get hierarchical structure for Parameter Management
  getHierarchical(category: string): ParameterItem[] {
    const data = this.cache?.[category];
    if (!data) return [];
    
    if (Array.isArray(data)) {
      // Convert flat to hierarchical display
      const parents = data.filter(item => !item.parent);
      const childrenMap = new Map();
      
      // Build children map once
      data.forEach(item => {
        if (item.parent) {
          if (!childrenMap.has(item.parent)) childrenMap.set(item.parent, []);
          childrenMap.get(item.parent).push(item);
        }
      });
      
      return parents.map((parent: any) => ({
        ...parent,
        children: childrenMap.get(parent.id) || []
      }));
    }
    
    // Already hierarchical
    return Object.entries(data).map(([key, item]: [string, any]) => ({
      ...item,
      children: Object.values(item.children || {})
    }));
  }

  // Default data
  private getDefaults(): Parameters {
    return {
      Regio: [
        { id: '1', value: 'Noord-Holland' },
        { id: '2', value: 'Zuid-Holland' },
        { id: '3', value: 'Friesland' },
        { id: '4', value: 'Utrecht' },
        { id: '5', value: 'Oost' },
        { id: '6', value: 'Limburg' },
        { id: '7', value: 'Groningen/Drente' },
        { id: '8', value: 'Noord-Brabant/Zeeland' },
        { id: '9', value: 'Duitsland' }
      ],
      Lidmaatschap: [
        { id: '1', value: 'Gewoon lid' },
        { id: '2', value: 'Gezins lid' },
        { id: '3', value: 'Gezins donateur zonder motor' },
        { id: '4', value: 'Donateur zonder motor' }
      ],
      Motormerk: [
        { id: '1', value: 'Harley-Davidson' },
        { id: '2', value: 'Indian' },
        { id: '3', value: 'Buell' },
        { id: '4', value: 'Eigenbouw' }
      ],
      Clubblad: [
        { id: '1', value: 'Papier' },
        { id: '2', value: 'Digitaal' },
        { id: '3', value: 'Geen' }
      ],
      WieWatWaar: [
        { id: '1', value: 'Eerder lid van de H-DCN' },
        { id: '2', value: 'Facebook' },
        { id: '3', value: 'Familie' },
        { id: '4', value: 'Harleydag' },
        { id: '5', value: 'Instagram' },
        { id: '6', value: 'Lid van de H-DCN' },
        { id: '7', value: 'Internet' },
        { id: '8', value: 'Openingsrit' },
        { id: '9', value: 'Vrienden' },
        { id: '10', value: 'Website H-DCN' },
        { id: '11', value: 'The Young Ones' },
        { id: '12', value: 'Bigtwin Bike Expo' }
      ],
      Productgroepen: {
        'Kleding': {
          id: '1',
          value: 'Kleding',
          children: {
            'T-shirts': { id: '2', value: 'T-shirts' },
            'Jassen': { id: '3', value: 'Jassen' },
            'Hoodies': { id: '4', value: 'Hoodies' }
          }
        },
        'Accessoires': {
          id: '5',
          value: 'Accessoires',
          children: {
            'Helmen': { id: '6', value: 'Helmen' },
            'Handschoenen': { id: '7', value: 'Handschoenen' }
          }
        },
        'Onderdelen': {
          id: '8',
          value: 'Onderdelen',
          children: {
            'Uitlaat': { id: '9', value: 'Uitlaat' },
            'Verlichting': { id: '10', value: 'Verlichting' }
          }
        },
        'Merchandise': {
          id: '11',
          value: 'Merchandise',
          children: {}
        },
        'Boeken & Media': {
          id: '12',
          value: 'Boeken & Media',
          children: {}
        }
      },
      // BACKWARD COMPATIBILITY: Include Function_permissions with legacy group patterns
      // This ensures existing permission configurations continue to work without migration
      Function_permissions: [{
        id: 'default',
        value: {
          members: { 
            read: ['System_User_Management', 'hdcnRegio_*', 'Members_Read', 'Members_CRUD'], 
            write: ['System_User_Management', 'Members_CRUD'] 
          },
          events: { 
            read: ['System_User_Management', 'Events_Read', 'Events_CRUD'], 
            write: ['System_User_Management', 'Events_CRUD'] 
          },
          products: { 
            read: ['System_User_Management', 'Products_Read', 'Products_CRUD'], 
            write: ['System_User_Management', 'Products_CRUD'] 
          },
          webshop: { 
            read: ['hdcnLeden', 'System_User_Management'], 
            write: ['hdcnLeden', 'System_User_Management'] 
          },
          parameters: { 
            read: ['System_User_Management', 'System_User_Management', 'National_Chairman', 'National_Secretary'], 
            write: ['System_User_Management', 'System_CRUD'] 
          },
          memberships: { 
            read: ['System_User_Management', 'Members_CRUD'], 
            write: ['System_User_Management', 'Members_CRUD'] 
          }
        }
      }]
    };
  }

  /**
   * BACKWARD COMPATIBILITY: Validate existing parameter structure
   * Ensures that existing parameter configurations are compatible with new role-based system
   * @param data - Parameter data to validate
   * @returns Validation result with compatibility status
   */
  private validateParameterCompatibility(data: Parameters): {
    isCompatible: boolean;
    issues: string[];
    autoFixApplied: boolean;
  } {
    const issues: string[] = [];
    let autoFixApplied = false;

    // Check for required categories
    const requiredCategories = ['Regio', 'Lidmaatschap', 'Motormerk', 'Clubblad'];
    requiredCategories.forEach(category => {
      if (!data[category] || !Array.isArray(data[category]) || data[category].length === 0) {
        issues.push(`Missing or empty required category: ${category}`);
      }
    });

    // Check Function_permissions structure
    if (!data.Function_permissions || !Array.isArray(data.Function_permissions)) {
      issues.push('Function_permissions category missing or invalid structure');
      
      // AUTO-FIX: Add default Function_permissions if missing
      data.Function_permissions = this.getDefaults().Function_permissions;
      autoFixApplied = true;
    } else {
      // Check if we have at least one valid permission item
      const hasValidPermissionItem = data.Function_permissions.some(item => 
        item && 
        typeof item === 'object' && 
        item.value && 
        typeof item.value === 'object' &&
        Object.keys(item.value).length > 0
      );
      
      if (!hasValidPermissionItem) {
        // AUTO-FIX: Add default permission structure
        data.Function_permissions.push(this.getDefaults().Function_permissions[0]);
        autoFixApplied = true;
      }
    }

    // Check membership type data integrity
    if (data.Lidmaatschap && Array.isArray(data.Lidmaatschap)) {
      const expectedMembershipTypes = ['Gewoon lid', 'Gezins lid', 'Gezins donateur zonder motor', 'Donateur zonder motor'];
      const existingTypes = data.Lidmaatschap.map(item => item.value);
      const missingTypes = expectedMembershipTypes.filter(type => !existingTypes.includes(type));
      
      if (missingTypes.length > 0) {
        issues.push(`Missing expected membership types: ${missingTypes.join(', ')}`);
        
        // AUTO-FIX: Add missing membership types
        const defaults = this.getDefaults().Lidmaatschap;
        missingTypes.forEach(missingType => {
          const defaultItem = defaults.find(item => item.value === missingType);
          if (defaultItem) {
            data.Lidmaatschap.push(defaultItem);
            autoFixApplied = true;
          }
        });
        
        if (autoFixApplied) {
          console.log('🔧 Auto-fix applied: Added missing membership types');
        }
      }
    }

    return {
      isCompatible: issues.length === 0,
      issues,
      autoFixApplied
    };
  }

  /**
   * BACKWARD COMPATIBILITY: Migrate legacy parameter structure if needed
   * Handles migration from old parameter formats to new structure without data loss
   * @param data - Parameter data that might need migration
   * @returns Migrated parameter data
   */
  private migrateParameterStructure(data: Parameters): Parameters {
    const migrated = { ...data };
    let migrationApplied = false;

    // Handle legacy Function_permissions format
    if (migrated.function_permissions && !migrated.Function_permissions) {
      migrated.Function_permissions = migrated.function_permissions;
      delete migrated.function_permissions;
      migrationApplied = true;
      console.log('🔄 Migration applied: Renamed function_permissions to Function_permissions');
    }

    // Handle legacy group patterns in permissions
    if (migrated.Function_permissions && Array.isArray(migrated.Function_permissions)) {
      migrated.Function_permissions.forEach(permissionItem => {
        if (permissionItem.value && typeof permissionItem.value === 'object') {
          const permissions = permissionItem.value;
          
          // Ensure legacy group patterns are preserved
          Object.keys(permissions).forEach(functionName => {
            const functionPerms = permissions[functionName];
            if (functionPerms.read && Array.isArray(functionPerms.read)) {
              // Preserve existing legacy groups while adding new role-based ones
              const hasLegacyGroups = functionPerms.read.some(group => group.startsWith('hdcn'));
              if (!hasLegacyGroups && functionName === 'webshop') {
                // Add legacy hdcnLeden for webshop if missing
                functionPerms.read.push('hdcnLeden');
                migrationApplied = true;
              }
            }
          });
        }
      });
    }

    // Handle Productgroepen structure migration
    if (migrated.Productgroepen && Array.isArray(migrated.Productgroepen)) {
      // Convert flat array to nested structure if needed
      const flatItems = migrated.Productgroepen;
      const parents = flatItems.filter(item => !item.parent);
      
      if (parents.length > 0) {
        const nested = {};
        parents.forEach(parent => {
          const children = {};
          flatItems.filter(item => item.parent === parent.id).forEach(child => {
            children[child.value] = { id: child.id, value: child.value };
          });
          nested[parent.value] = {
            id: parent.id,
            value: parent.value,
            children
          };
        });
        
        migrated.Productgroepen = nested;
        migrationApplied = true;
        console.log('🔄 Migration applied: Converted Productgroepen to nested structure');
      }
    }

    if (migrationApplied) {
      console.log('🔄 Parameter structure migration completed');
    }

    return migrated;
  }
}

// Single instance
export const parameterStore = new ParameterStore();

// Shared hook logic for parameter loading
const useParameterLoader = (category: string, dataGetter: (cat: string) => ParameterItem[]) => {
  const [parameters, setParameters] = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  const memoizedDataGetter = React.useCallback(() => dataGetter(category), [category, dataGetter]);

  React.useEffect(() => {
    let mounted = true;

    const loadData = async () => {
      try {
        await parameterStore.getParameters();
        if (mounted) {
          setParameters(memoizedDataGetter());
          setLoading(false);
        }
      } catch (error) {
        if (mounted) {
          setParameters([]);
          setLoading(false);
        }
      }
    };

    loadData();

    const unsubscribe = parameterStore.subscribe(() => {
      if (mounted) {
        setParameters(memoizedDataGetter());
      }
    });

    return () => {
      mounted = false;
      unsubscribe();
    };
  }, [memoizedDataGetter]);

  return { parameters, loading };
};

// React hook for dropdowns (flat array)
export const useParameters = (category: string) => {
  const dataGetter = React.useCallback((cat) => parameterStore.getFlatArray(cat), []);
  return useParameterLoader(category, dataGetter);
};

// React hook for Parameter Management (hierarchical)
export const useHierarchicalParameters = (category: string) => {
  const dataGetter = React.useCallback((cat) => parameterStore.getHierarchical(cat), []);
  return useParameterLoader(category, dataGetter);
};
import React from 'react';
import { ApiService } from './apiService';

interface ParameterItem {
  id: string;
  value: any;
  parent?: string;
  children?: Record<string, ParameterItem>;
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
          console.log('🔧 Parameter compatibility auto-fixes applied');
        }
        
        if (!validation.isCompatible) {
          console.warn('⚠️ Parameter compatibility issues detected:', validation.issues);
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
            console.log('🔧 Parameter compatibility auto-fixes applied to localStorage data');
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

  // Save parameters
  async saveParameters(data: Parameters): Promise<void> {
    // BACKWARD COMPATIBILITY: Apply migration and validation before saving
    const migratedData = this.migrateParameterStructure(data);
    const validation = this.validateParameterCompatibility(migratedData);
    
    if (validation.autoFixApplied) {
      console.log('🔧 Parameter compatibility auto-fixes applied before saving');
    }
    
    if (!validation.isCompatible) {
      console.warn('⚠️ Parameter compatibility issues detected before saving:', validation.issues);
      // Continue with save but log issues for monitoring
    }
    
    this.cache = migratedData;
    try {
      localStorage.setItem('hdcn-form-parameters', JSON.stringify(migratedData));
    } catch (e) {
      console.warn('localStorage write failed:', e.message);
    }
    
    // Save to DynamoDB via API
    try {
      await this.saveToDynamoDB(migratedData);
      console.log('Parameters saved to DynamoDB and localStorage with backward compatibility');
    } catch (error) {
      console.log('DynamoDB save failed, saved to localStorage only:', error.message);
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

  // Load individual categories using GET /parameters/name/{name}
  private async convertApiToFormStructure(): Promise<Parameters> {
    const formStructure: any = {};
    const categoryMetadata: any = {};
    
    const categories = ['regio', 'lidmaatschap', 'motormerk', 'clubblad', 'wiewatwaar', 'function_permissions'];
    
    // Use Promise.all for parallel API calls instead of sequential
    const promises = categories.map(async (categoryName) => {
      try {
        const param = await ApiService.getParameterByName(categoryName);
        const displayName = this.getCategoryName(categoryName);
        
        if (displayName) {
          const items = JSON.parse(param.value);
          return {
            category: displayName,
            data: Array.isArray(items) ? items : [],
            metadata: param
          };
        }
      } catch (error) {
        console.log(`Error loading ${categoryName}:`, error.message);
        return null;
      }
    });
    
    // Process results
    const results = await Promise.all(promises);
    results.filter(Boolean).forEach(({ category, data, metadata }) => {
      if (category === 'Configuratie') {
        if (!formStructure.Configuratie) formStructure.Configuratie = [];
        formStructure.Configuratie.push(...data);
      } else {
        formStructure[category] = data;
      }
      
      categoryMetadata[category] = {
        description: metadata.description,
        created_at: metadata.created_at,
        parameter_id: metadata.parameter_id
      };
    });

    formStructure._metadata = categoryMetadata;
    return formStructure;
  }

  // Save to DynamoDB by updating existing parameter records
  private async saveToDynamoDB(formData: Parameters): Promise<void> {
    // Cache category map to avoid repeated API calls
    if (!this.categoryMapCache) {
      const apiData = await ApiService.getAllParameters();
      this.categoryMapCache = new Map();
      for (const param of apiData) {
        const name = param.name?.toLowerCase();
        if (name) this.categoryMapCache.set(name, param.parameter_id);
      }
    }
    
    const categoryMap = this.categoryMapCache;

    const promises = [];

    // Update each category
    for (const [category, items] of Object.entries(formData)) {
      if (category === '_metadata') continue;
      
      const categoryKey = category.toLowerCase();
      const parameterId = categoryMap.get(categoryKey);
      
      if (parameterId && Array.isArray(items)) {
        let valueToSave;
        
        if (categoryKey === 'productgroepen') {
          // Optimize nested structure conversion
          const nested: any = {};
          const parentMap = new Map<string, any>();
          const childrenMap = new Map<string, any[]>();
          
          // Single pass to separate parents and children
          for (const item of items) {
            if (!item.parent) {
              parentMap.set(item.id, item);
              childrenMap.set(item.id, []);
            }
          }
          
          for (const item of items) {
            if (item.parent) {
              if (!childrenMap.has(item.parent)) childrenMap.set(item.parent, []);
              childrenMap.get(item.parent).push(item);
            }
          }
          
          // Build nested structure
          for (const [parentId, parent] of Array.from(parentMap.entries())) {
            const children: any = {};
            for (const child of childrenMap.get(parentId) || []) {
              children[child.value] = { id: child.id, value: child.value };
            }
            nested[parent.value] = { id: parent.id, value: parent.value, children };
          }
          
          valueToSave = JSON.stringify(nested);
        } else {
          valueToSave = JSON.stringify(items);
        }
        
        promises.push(ApiService.updateParameter(parameterId, {
          name: categoryKey,
          value: valueToSave,
          description: `Configuration data for ${category}`
        }));
      }
    }

    await Promise.all(promises);
  }

  // Helper: Convert nested structure to flat array for dropdowns
  getFlatArray(category: string): ParameterItem[] {
    const data = this.cache?.[category];
    if (!data) return [];
    
    if (Array.isArray(data)) {
      return data; // Already flat
    }
    
    // Convert nested object to flat array
    return Object.entries(data).flatMap(([key, item]: [string, any]) => {
      const parent = { id: item.id, value: item.value };
      const children = item.children ? Object.values(item.children).map((child: any) => ({
        id: child.id, 
        value: child.value, 
        parent: item.id
      })) : [];
      return [parent, ...children];
    });
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
            read: ['hdcnAdmins', 'hdcnRegio_*', 'Members_Read_All', 'Members_CRUD_All'], 
            write: ['hdcnAdmins', 'Members_CRUD_All'] 
          },
          events: { 
            read: ['hdcnAdmins', 'Events_Read_All', 'Events_CRUD_All'], 
            write: ['hdcnAdmins', 'Events_CRUD_All'] 
          },
          products: { 
            read: ['hdcnAdmins', 'Products_Read_All', 'Products_CRUD_All'], 
            write: ['hdcnAdmins', 'Products_CRUD_All'] 
          },
          webshop: { 
            read: ['hdcnLeden', 'hdcnAdmins'], 
            write: ['hdcnLeden', 'hdcnAdmins'] 
          },
          parameters: { 
            read: ['hdcnAdmins', 'System_User_Management', 'National_Chairman', 'National_Secretary'], 
            write: ['hdcnAdmins', 'System_CRUD_All', 'Webmaster'] 
          },
          memberships: { 
            read: ['hdcnAdmins', 'Members_CRUD_All'], 
            write: ['hdcnAdmins', 'Members_CRUD_All'] 
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
      console.log('🔧 Auto-fix applied: Added default Function_permissions structure');
    } else {
      const permissionItem = data.Function_permissions.find(item => item.value && typeof item.value === 'object');
      if (!permissionItem) {
        issues.push('Function_permissions missing valid permission configuration');
        
        // AUTO-FIX: Add default permission structure
        data.Function_permissions.push(this.getDefaults().Function_permissions[0]);
        autoFixApplied = true;
        console.log('🔧 Auto-fix applied: Added default permission configuration');
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
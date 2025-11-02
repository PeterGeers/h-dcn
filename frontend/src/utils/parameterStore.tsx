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
        this.cache = formData;
        try {
          localStorage.setItem('hdcn-form-parameters', JSON.stringify(formData));
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
          this.cache = data;
          this.notifyListeners();
          return this.cache;
        }
      } catch (error) {
        console.log('Invalid localStorage data');
      }
    }

    // Final fallback to defaults
    this.cache = this.getDefaults();
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
    this.cache = data;
    try {
      localStorage.setItem('hdcn-form-parameters', JSON.stringify(data));
    } catch (e) {
      console.warn('localStorage write failed:', e.message);
    }
    
    // Save to DynamoDB via API
    try {
      await this.saveToDynamoDB(data);
      console.log('Parameters saved to DynamoDB and localStorage');
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
      }
    };
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
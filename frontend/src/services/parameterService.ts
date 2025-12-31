/**
 * Parameter Service for H-DCN Application
 * 
 * This service handles parameter-related API calls and data transformations
 */

import { API_CONFIG } from '../config/api';
import { getAuthHeadersForGet } from '../utils/authHeaders';

export interface ParameterItem {
  id?: string;
  value?: string;
  parent?: string | null;
  displayValue?: string;
  children?: ParameterItem[];
  // Leveropties specific fields
  name?: string;
  cost?: string;
}

export interface Parameters {
  [category: string]: ParameterItem[] | any;
  _metadata?: any;
}

export class ParameterService {
  /**
   * Get category name mapping
   */
  static getCategoryName(apiName: string): string | null {
    const mapping: Record<string, string> = {
      'regio': 'Regio',
      'lidmaatschap': 'Lidmaatschap',
      'motormerk': 'Motormerk',
      'clubblad': 'Clubblad',
      'wiewatwaar': 'WieWatWaar',
      'productgroepen': 'Productgroepen',
      'function_permissions': 'function_permissions'
    };
    
    if (mapping[apiName]) {
      return mapping[apiName];
    }
    
    return null;
  }

  /**
   * Convert API parameters to form structure for Parameter Management
   */
  static async convertApiToFormStructure(apiData: any[]): Promise<Parameters> {
    const formStructure: any = {};
    const categoryMetadata: any = {};

    try {
      if (!Array.isArray(apiData)) {
        console.warn('API data is not an array:', apiData);
        return { _metadata: {} };
      }

      apiData.forEach(param => {
        try {
          if (!param || !param.name) {
            console.warn('Invalid parameter object:', param);
            return;
          }

          const name = param.name?.toLowerCase();
          const categoryName = this.getCategoryName(name);
          
          if (name === 'productgroepen') {
            // Special handling for nested Productgroepen
            try {
              const nestedData = JSON.parse(param.value);
              const flatArray: ParameterItem[] = [];
              Object.entries(nestedData).forEach(([key, item]: [string, any]) => {
                if (item && typeof item === 'object') {
                  flatArray.push({
                    id: item.id || key,
                    value: item.value || key,
                    parent: null
                  });
                  if (item.children) {
                    Object.entries(item.children).forEach(([childKey, child]: [string, any]) => {
                      if (child && typeof child === 'object') {
                        flatArray.push({
                          id: child.id || childKey,
                          value: child.value || childKey,
                          parent: item.id || key
                        });
                      }
                    });
                  }
                }
              });
              formStructure.Productgroepen = flatArray;
            } catch (parseError) {
              console.error('Error parsing Productgroepen:', parseError);
              formStructure.Productgroepen = [];
            }
            
            categoryMetadata.Productgroepen = {
              description: param.description || '',
              created_at: param.created_at || '',
              parameter_id: param.parameter_id || ''
            };
          } else if (name === 'api_base_url') {
            // Special handling for API base URL
            if (!formStructure.Configuratie) formStructure.Configuratie = [];
            formStructure.Configuratie.push({
              id: param.parameter_id || 'api_base_url',
              value: param.value || ''
            });
            
            categoryMetadata.Configuratie = {
              description: param.description || '',
              created_at: param.created_at || '',
              parameter_id: param.parameter_id || ''
            };
          } else if (categoryName) {
            // Handle all other categories dynamically
            try {
              const items = JSON.parse(param.value || '[]');
              formStructure[categoryName] = Array.isArray(items) ? items : [];
            } catch {
              // If not JSON, treat as single value
              formStructure[categoryName] = [{ 
                id: param.parameter_id || 'default', 
                value: param.value || '' 
              }];
            }
            
            categoryMetadata[categoryName] = {
              description: param.description || '',
              created_at: param.created_at || '',
              parameter_id: param.parameter_id || ''
            };
          }
        } catch (error) {
          console.error(`Error parsing parameter ${param?.name}:`, error);
        }
      });
    } catch (error) {
      console.error('Error in convertApiToFormStructure:', error);
    }

    formStructure._metadata = categoryMetadata;
    return formStructure;
  }

  /**
   * Get available categories
   */
  static getCategories(parameters: Parameters): string[] {
    try {
      if (parameters && Object.keys(parameters).length > 0) {
        return Object.keys(parameters)
          .filter(key => key !== '_metadata')
          .sort((a, b) => a.localeCompare(b));
      }
      return ['Regio', 'Lidmaatschap', 'Motormerk', 'Clubblad', 'WieWatWaar', 'Productgroepen', 'function_permissions'].sort();
    } catch (error) {
      console.error('Error in getCategories:', error);
      return ['Regio', 'Lidmaatschap', 'Motormerk', 'Clubblad', 'WieWatWaar', 'Productgroepen', 'function_permissions'].sort();
    }
  }

  /**
   * Get current parameters for a category
   */
  static getCurrentParameters(parameters: Parameters, selectedCategory: string): ParameterItem[] {
    try {
      if (!parameters || !selectedCategory) return [];
      
      const params = parameters[selectedCategory];
      if (!params) return [];
      
      // Handle both array and object formats
      if (Array.isArray(params)) {
        return params.map(param => ({
          ...param,
          displayValue: typeof param.value === 'object' 
            ? JSON.stringify(param.value, null, 2)
            : param.value || '',
          parent: param.parent || null,
          children: []
        }));
      }
      
      // Handle nested object format (like the old Productgroepen structure)
      if (typeof params === 'object') {
        const result: ParameterItem[] = [];
        Object.entries(params).forEach(([key, item]: [string, any]) => {
          if (item && typeof item === 'object') {
            result.push({
              id: item.id || key,
              value: item.value || key,
              displayValue: item.value || key,
              parent: null,
              children: []
            });
          }
        });
        return result;
      }
      
      return [];
    } catch (error) {
      console.error('Error in getCurrentParameters:', error);
      return [];
    }
  }
}
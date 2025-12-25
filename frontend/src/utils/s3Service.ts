import { fetchAuthSession } from 'aws-amplify/auth';

interface S3Config {
  bucketName: string;
  fileName: string;
  region: string;
}

interface ParameterData {
  [key: string]: any;
}

// S3 Bucket settings
const S3_CONFIG: S3Config = {
  bucketName: 'hdcn-parameters',
  fileName: 'parameters.json',
  region: 'eu-west-1'
};

// Parameter service with S3 bucket integration
export class S3Service {
  static clearCache(key: string): void {
    localStorage.removeItem(`s3-${key}`);
  }
  
  static convertFlatToHierarchical(data: ParameterData): ParameterData {
    // Convert flat structure to hierarchical for Parameter Management
    const converted = { ...data };
    if (converted.Productgroepen && converted.Productgroepen[0] && typeof converted.Productgroepen[0].value === 'string' && !converted.Productgroepen[0].value.startsWith('{')) {
      // Convert flat structure to hierarchical
      converted.Productgroepen = converted.Productgroepen.map(item => {
        try {
          return {
            ...item,
            value: JSON.stringify({
              value: item.value,
              parent: item.parent,
              children: []
            })
          };
        } catch (error) {
          console.error('JSON stringify error:', error);
          return item; // Return original item if serialization fails
        }
      });
    }
    return converted;
  }
  
  static async getObject(key: string): Promise<ParameterData> {
    try {
      // Try public parameters.json first (GitHub Pages) with version-based caching
      try {
        const version = process.env.REACT_APP_CACHE_VERSION || '1.0';
        const response = await fetch(`/parameters.json?v=${version}`);
        if (response.ok) {
          const data = await response.json();
          localStorage.setItem(`s3-${key}`, JSON.stringify(data));
          return data;
        }
      } catch (publicError) {
        console.log('Public parameters not available');
      }
      
      // Fallback to localStorage
      const stored = localStorage.getItem(`s3-${key}`);
      if (stored) {
        try {
          return JSON.parse(stored);
        } catch (parseError) {
          console.error('JSON parse error:', parseError);
          // Remove corrupted data and continue to defaults
          localStorage.removeItem(`s3-${key}`);
        }
      }
      
      // No data available
      console.warn('No parameter data available');
      return {};
    } catch (error) {
      console.error('Parameter get error:', error);
      return {};
    }
  }
  
  static async putObject(key: string, data: ParameterData): Promise<boolean> {
    try {
      // Try API first (which can write to S3)
      try {
        const { getAuthHeaders } = await import('./authHeaders');
        const headers = await getAuthHeaders();
        const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'}/parameters`, {
          method: 'PUT',
          headers: {
            ...headers,
            'Access-Control-Allow-Origin': '*'
          },
          body: JSON.stringify(data)
        });
        if (response.ok) {
          localStorage.setItem(`s3-${key}`, JSON.stringify(data));
          console.log('Data saved to S3 via API');
          return true;
        }
      } catch (apiError) {
        console.log('API save failed, using localStorage:', apiError.message);
      }
      
      // Fallback to localStorage
      localStorage.setItem(`s3-${key}`, JSON.stringify(data));
      console.log('Data saved to localStorage only');
      return true;
    } catch (error) {
      console.error('Parameter put error:', error);
      throw error;
    }
  }
  

}
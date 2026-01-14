/**
 * Product Categories Configuration
 * 
 * Defines the hierarchical structure of product categories and subcategories
 * for the H-DCN webshop.
 * 
 * Previously managed via Parameter Management system in S3.
 * Now hardcoded for simplicity - can be moved to a database-driven system later.
 * 
 * Source: Extracted from s3://my-hdcn-bucket/parameters.json on 2026-01-14
 */

export interface ProductSubcategory {
  id: string;
  value: string;
}

export interface ProductCategory {
  id: string;
  value: string;
  children: Record<string, ProductSubcategory>;
}

export type ProductCategoryStructure = Record<string, ProductCategory>;

/**
 * Product category hierarchy
 * Structure: Category → Subcategories
 */
export const PRODUCT_CATEGORIES: ProductCategoryStructure = {
  'Heren': {
    id: 'Heren',
    value: 'Heren',
    children: {
      'T-Shirts': {
        id: '1767202096440',
        value: 'T-Shirts'
      },
      'Long Sleeves': {
        id: '1767202140332',
        value: 'Long Sleeves'
      },
      'Hoodies': {
        id: '1767202147742',
        value: 'Hoodies'
      }
    }
  },
  'Dames': {
    id: 'Dames',
    value: 'Dames',
    children: {
      'T-Shirts': {
        id: '1767202161506',
        value: 'T-Shirts'
      },
      'Long Sleeves': {
        id: '1767202176842',
        value: 'Long Sleeves'
      },
      'Hoodies': {
        id: '1767202209428',
        value: 'Hoodies'
      }
    }
  },
  'Diversen': {
    id: 'Diversen',
    value: 'Diversen',
    children: {
      'Badges': {
        id: '1767202234713',
        value: 'Badges'
      },
      'Stickers': {
        id: '1767202243468',
        value: 'Stickers'
      },
      'Bordjes': {
        id: '1767202259782',
        value: 'Bordjes'
      },
      'Pins': {
        id: '1767202284214',
        value: 'Pins'
      }
    }
  },
  'Unisex': {
    id: 'Unisex',
    value: 'Unisex',
    children: {
      'Long Sleeves': {
        id: '1767202221787',
        value: 'Long Sleeves'
      }
    }
  }
};

/**
 * Get all main categories
 */
export const getCategories = (): string[] => {
  return Object.keys(PRODUCT_CATEGORIES);
};

/**
 * Get subcategories for a specific category
 */
export const getSubcategories = (category: string): string[] => {
  const cat = PRODUCT_CATEGORIES[category];
  return cat ? Object.keys(cat.children) : [];
};

/**
 * Get category by ID
 */
export const getCategoryById = (id: string): ProductCategory | undefined => {
  return Object.values(PRODUCT_CATEGORIES).find(cat => cat.id === id);
};

/**
 * Get subcategory by ID within a category
 */
export const getSubcategoryById = (categoryId: string, subcategoryId: string): ProductSubcategory | undefined => {
  const category = getCategoryById(categoryId);
  if (!category) return undefined;
  
  return Object.values(category.children).find(sub => sub.id === subcategoryId);
};

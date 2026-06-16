import { Product } from '../../../types';
import { ApiService } from '../../../services/apiService';

interface Parameter {
  id?: string;
  name: string;
  value: string;
  [key: string]: any;
}

export const scanProducts = async () => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.get('/scan-product');
};

export const getProductById = async (id: string) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.get(`/get-product-byid/${id}`);
};

export const insertProduct = async (data: Product) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.post('/insert-product/', data);
};

export const updateProduct = async (id: string, data: Product) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.put(`/admin/products/${id}`, data);
};

/**
 * Update a product's variant schema (top-down sync).
 * The backend detects the schema change and regenerates variants accordingly.
 */
export const updateVariantSchema = async (id: string, variantSchema: Record<string, string[]>) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.put(`/admin/products/${id}`, { variant_schema: variantSchema });
};

/**
 * Add a variant to a product (bottom-up sync).
 * The backend creates the variant record and updates the parent's variant_schema.
 */
export const addVariantToProduct = async (id: string, variantAttributes: Record<string, string>) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.put(`/admin/products/${id}`, {
    variant_action: 'add_variant',
    variant_attributes: variantAttributes,
  });
};

/**
 * Remove a variant from a product.
 * Sends DELETE request to `/admin/products/{id}/variants` to remove the variant
 * identified by the given attributes.
 */
export const removeVariantFromProduct = async (id: string, variantAttributes: Record<string, string>) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  // Encode variant attributes as query params for the DELETE endpoint
  const params = new URLSearchParams(variantAttributes).toString();
  return ApiService.delete(`/admin/products/${id}/variants?${params}`);
};

export const deleteProduct = async (id: string) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.delete(`/delete-product/${id}`);
};

/**
 * Soft-delete a product (sets active=false on product and all child variants).
 * Calls DELETE /admin/products/{id} without ?hard=true.
 */
export const softDeleteProduct = async (id: string) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.delete(`/admin/products/${id}`);
};

/**
 * Hard-delete a product (permanently removes from DynamoDB).
 * Calls DELETE /admin/products/{id}?hard=true.
 * API returns error ProductHasOrderHistory if non-cancelled orders reference this product.
 */
export const hardDeleteProduct = async (id: string) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.delete(`/admin/products/${id}?hard=true`);
};

export const getParameterByName = async (name: string) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.get(`/parameters/name/${name}`);
};

export const getAllParameters = async () => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.get('/parameters');
};

export const createParameter = async (data: Parameter) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.post('/parameters', data);
};

export const updateParameter = async (id: string, data: Parameter) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.put(`/parameters/${id}`, data);
};

export const deleteParameter = async (id: string) => {
  if (!(await ApiService.isAuthenticated())) {
    throw new Error('Authentication required');
  }
  return ApiService.delete(`/parameters/${id}`);
};

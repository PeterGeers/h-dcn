import { Product } from '../../../types';
import { ApiService } from '../../../services/apiService';

interface Parameter {
  id?: string;
  name: string;
  value: string;
  [key: string]: any;
}

import { API_CONFIG } from '../../../config/api';

const BASE: string = API_CONFIG.BASE_URL;

export const scanProducts = async () => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  return ApiService.get('/scan-product');
};

export const getProductById = async (id: string) => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  return ApiService.get(`/get-product-byid/${id}`);
};

export const insertProduct = async (data: Product) => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  return ApiService.post('/insert-product/', data);
};

export const updateProduct = async (id: string, data: Product) => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  return ApiService.put(`/update-product/${id}`, data);
};

export const deleteProduct = async (id: string) => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  return ApiService.delete(`/delete-product/${id}`);
};

export const getParameterByName = async (name: string) => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  return ApiService.get(`/parameters/name/${name}`);
};

export const getAllParameters = async () => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  return ApiService.get('/parameters');
};

export const createParameter = async (data: Parameter) => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  return ApiService.post('/parameters', data);
};

export const updateParameter = async (id: string, data: Parameter) => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  return ApiService.put(`/parameters/${id}`, data);
};

export const deleteParameter = async (id: string) => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  return ApiService.delete(`/parameters/${id}`);
};
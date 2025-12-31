import axios, { AxiosResponse } from 'axios';
import { Product } from '../../../types';
import { getAuthHeaders, getAuthHeadersForGet } from '../../../utils/authHeaders';

interface Parameter {
  id?: string;
  name: string;
  value: string;
  [key: string]: any;
}

import { API_CONFIG } from '../../../config/api';

const BASE: string = API_CONFIG.BASE_URL;

// Helper function to create axios config with auth headers
const createAuthConfig = async (method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET') => {
  const headers = method === 'GET' ? await getAuthHeadersForGet() : await getAuthHeaders();
  return { headers };
};

export const scanProducts = async (): Promise<AxiosResponse<any>> => {
  const config = await createAuthConfig('GET');
  return axios.get(`${BASE}/scan-product`, config);
};

export const getProductById = async (id: string): Promise<AxiosResponse<any>> => {
  const config = await createAuthConfig('GET');
  return axios.get(`${BASE}/get-product-byid/${id}`, config);
};

export const insertProduct = async (data: Product): Promise<AxiosResponse<any>> => {
  const config = await createAuthConfig('POST');
  return axios.post(`${BASE}/insert-product/`, data, config);
};

export const updateProduct = async (id: string, data: Product): Promise<AxiosResponse<any>> => {
  const config = await createAuthConfig('PUT');
  return axios.put(`${BASE}/update-product/${id}`, data, config);
};

export const deleteProduct = async (id: string): Promise<AxiosResponse<any>> => {
  const config = await createAuthConfig('DELETE');
  return axios.delete(`${BASE}/delete-product/${id}`, config);
};

export const getParameterByName = async (name: string): Promise<AxiosResponse<any>> => {
  const config = await createAuthConfig('GET');
  return axios.get(`${BASE}/parameters/name/${name}`, config);
};

export const getAllParameters = async (): Promise<AxiosResponse<any>> => {
  const config = await createAuthConfig('GET');
  return axios.get(`${BASE}/parameters`, config);
};

export const createParameter = async (data: Parameter): Promise<AxiosResponse<any>> => {
  const config = await createAuthConfig('POST');
  return axios.post(`${BASE}/parameters`, data, config);
};

export const updateParameter = async (id: string, data: Parameter): Promise<AxiosResponse<any>> => {
  const config = await createAuthConfig('PUT');
  return axios.put(`${BASE}/parameters/${id}`, data, config);
};

export const deleteParameter = async (id: string): Promise<AxiosResponse<any>> => {
  const config = await createAuthConfig('DELETE');
  return axios.delete(`${BASE}/parameters/${id}`, config);
};
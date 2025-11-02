import axios, { AxiosResponse } from 'axios';
import { Product } from '../../../types';

interface Parameter {
  id?: string;
  name: string;
  value: string;
  [key: string]: any;
}

import { API_CONFIG } from '../../../config/api';

const BASE: string = API_CONFIG.BASE_URL;

export const scanProducts = (): Promise<AxiosResponse<any>> => axios.get(`${BASE}/scan-product`);
export const getProductById = (id: string): Promise<AxiosResponse<any>> => axios.get(`${BASE}/get-product-byid/${id}`);
export const insertProduct = (data: Product): Promise<AxiosResponse<any>> => axios.post(`${BASE}/insert-product/`, data);
export const updateProduct = (id: string, data: Product): Promise<AxiosResponse<any>> => axios.put(`${BASE}/update-product/${id}`, data);
export const deleteProduct = (id: string): Promise<AxiosResponse<any>> => axios.delete(`${BASE}/delete-product/${id}`);
export const getParameterByName = (name: string): Promise<AxiosResponse<any>> => axios.get(`${BASE}/parameters/name/${name}`);
export const getAllParameters = (): Promise<AxiosResponse<any>> => axios.get(`${BASE}/parameters`);
export const createParameter = (data: Parameter): Promise<AxiosResponse<any>> => axios.post(`${BASE}/parameters`, data);
export const updateParameter = (id: string, data: Parameter): Promise<AxiosResponse<any>> => axios.put(`${BASE}/parameters/${id}`, data);
export const deleteParameter = (id: string): Promise<AxiosResponse<any>> => axios.delete(`${BASE}/parameters/${id}`);

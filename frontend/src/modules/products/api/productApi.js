import axios from 'axios';

const BASE = process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

export const scanProducts = () => axios.get(`${BASE}/scan-product`);
export const getProductById = (id) => axios.get(`${BASE}/get-product-byid/${id}`);
export const insertProduct = (data) => axios.post(`${BASE}/insert-product/`, data);
export const updateProduct = (id, data) => axios.put(`${BASE}/update-product/${id}`, data);
export const deleteProduct = (id) => axios.delete(`${BASE}/delete-product/${id}`);
export const getParameterByName = (name) => axios.get(`${BASE}/parameters/name/${name}`);
export const getAllParameters = () => axios.get(`${BASE}/parameters`);
export const createParameter = (data) => axios.post(`${BASE}/parameters`, data);
export const updateParameter = (id, data) => axios.put(`${BASE}/parameters/${id}`, data);
export const deleteParameter = (id) => axios.delete(`${BASE}/parameters/${id}`);

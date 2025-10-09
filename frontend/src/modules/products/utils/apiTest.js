import { scanProducts, getProductById, getAllParameters, getParameterByName } from '../api/productApi';

export const testAllAPIs = async () => {
  console.log('=== API Test Results ===');
  
  // Test 1: Get all products
  try {
    const products = await scanProducts();
    console.log('✅ scanProducts:', products.data?.length || 0, 'products found');
  } catch (error) {
    console.log('❌ scanProducts failed:', error.response?.status, error.message);
  }

  // Test 2: Get all parameters
  try {
    const params = await getAllParameters();
    console.log('✅ getAllParameters:', params.data);
    if (Array.isArray(params.data)) {
      params.data.forEach(param => {
        console.log('  Parameter:', param.name, '=', param.value);
      });
    }
  } catch (error) {
    console.log('❌ getAllParameters failed:', error.response?.status, error.message);
  }

  // Test 3: Test specific parameter names
  const paramNames = ['groep', 'subgroep', 'Productgroepen', 'Productsubgroepen', 'productgroep', 'productsubgroep'];
  
  for (const name of paramNames) {
    try {
      const param = await getParameterByName(name);
      console.log(`✅ getParameterByName('${name}'):`, param.data);
    } catch (error) {
      console.log(`❌ getParameterByName('${name}') failed:`, error.response?.status);
    }
  }

  // Test 4: Get first product by ID (if products exist)
  try {
    const products = await scanProducts();
    if (products.data?.length > 0) {
      const firstProduct = products.data[0];
      const product = await getProductById(firstProduct.id);
      console.log('✅ getProductById:', product.data);
    }
  } catch (error) {
    console.log('❌ getProductById failed:', error.response?.status, error.message);
  }

  console.log('=== Test Complete ===');
};
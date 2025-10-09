import { createParameter, scanProducts } from '../api/productApi';

export const createProductParameters = async () => {
  try {
    // Get existing products to extract unique values
    const products = await scanProducts();
    const productData = products.data || [];
    
    // Extract unique groep values
    const uniqueGroepen = [...new Set(productData.map(p => p.groep).filter(Boolean))].sort();
    const groepValues = uniqueGroepen.map((groep, index) => ({
      id: (index + 1).toString(),
      value: groep
    }));
    
    // Extract unique subgroep values
    const uniqueSubgroepen = [...new Set(productData.map(p => p.subgroep).filter(Boolean))].sort();
    const subgroepValues = uniqueSubgroepen.map((subgroep, index) => ({
      id: (index + 1).toString(),
      value: subgroep
    }));
    
    // Create Productgroepen parameter
    const productgroepenParam = {
      name: 'Productgroepen',
      value: JSON.stringify(groepValues),
      description: 'Allowed product groups'
    };
    
    // Create Productsubgroepen parameter
    const productsubgroepenParam = {
      name: 'Productsubgroepen', 
      value: JSON.stringify(subgroepValues),
      description: 'Allowed product subgroups'
    };
    
    console.log('Creating Productgroepen parameter:', productgroepenParam);
    await createParameter(productgroepenParam);
    
    console.log('Creating Productsubgroepen parameter:', productsubgroepenParam);
    await createParameter(productsubgroepenParam);
    
    console.log('✅ Parameters created successfully!');
    return true;
    
  } catch (error) {
    console.error('❌ Error creating parameters:', error);
    return false;
  }
};
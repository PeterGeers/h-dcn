import { createParameter, scanProducts } from '../api/productApi';

interface ParameterValue {
  id: string;
  value: string;
}

interface Parameter {
  name: string;
  value: string;
  description: string;
}

export const createProductParameters = async (): Promise<boolean> => {
  try {
    const products = await scanProducts();
    const productData = products.data || [];
    
    const uniqueGroepen = Array.from(new Set(productData.map((p: any) => p.groep).filter(Boolean))) as string[];
    uniqueGroepen.sort();
    const groepValues: ParameterValue[] = uniqueGroepen.map((groep, index) => ({
      id: (index + 1).toString(),
      value: groep
    }));
    
    const uniqueSubgroepen = Array.from(new Set(productData.map((p: any) => p.subgroep).filter(Boolean))) as string[];
    uniqueSubgroepen.sort();
    const subgroepValues: ParameterValue[] = uniqueSubgroepen.map((subgroep, index) => ({
      id: (index + 1).toString(),
      value: subgroep
    }));
    
    const productgroepenParam: Parameter = {
      name: 'Productgroepen',
      value: JSON.stringify(groepValues),
      description: 'Allowed product groups'
    };
    
    const productsubgroepenParam: Parameter = {
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
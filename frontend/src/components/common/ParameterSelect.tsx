import React, { ChangeEvent } from 'react';
import { Select, SelectProps } from '@chakra-ui/react';
import { useParameters } from '../../utils/parameterStore';

interface ParameterSelectProps extends Omit<SelectProps, 'onChange'> {
  category: string;
  placeholder?: string;
  value?: string;
  onChange?: (event: ChangeEvent<HTMLSelectElement>) => void;
}

function ParameterSelect({ 
  category, 
  placeholder, 
  value, 
  onChange, 
  ...props 
}: ParameterSelectProps) {
  const { parameters, loading } = useParameters(category);
  
  // Debug logging
  React.useEffect(() => {
    if (category === 'WieWatWaar' && !loading && parameters.length === 0) {
      console.warn(`⚠️ No parameters found for category "${category}"`);
    }
  }, [category, parameters, loading]);
  
  if (loading) {
    return (
      <Select placeholder="Laden..." isDisabled {...props}>
      </Select>
    );
  }
  
  if (!parameters || parameters.length === 0) {
    console.warn(`⚠️ No parameters found for category "${category}"`);
    return (
      <Select placeholder={`Geen opties voor ${category}`} isDisabled {...props}>
      </Select>
    );
  }
  
  return (
    <Select 
      placeholder={placeholder} 
      value={value} 
      onChange={onChange}
      {...props}
    >
      {parameters.map((param, index) => (
        <option key={param.id || param.value || index} value={param.value}>
          {param.value}
        </option>
      ))}
    </Select>
  );
}

export default ParameterSelect;
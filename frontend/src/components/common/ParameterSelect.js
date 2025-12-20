import React from 'react';
import { Select } from '@chakra-ui/react';
import { useParameters } from '../utils/parameterStore';

function ParameterSelect({ category, placeholder, value, onChange, ...props }) {
  const { parameters, loading } = useParameters(category);
  
  if (loading) {
    return (
      <Select placeholder="Laden..." isDisabled {...props}>
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
      {parameters.map(param => (
        <option key={param.id} value={param.value}>
          {param.value}
        </option>
      ))}
    </Select>
  );
}

export default ParameterSelect;
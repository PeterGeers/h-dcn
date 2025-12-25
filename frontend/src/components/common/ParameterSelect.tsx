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
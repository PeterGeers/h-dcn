import React, { ChangeEvent } from 'react';
import { Field, FieldProps } from 'formik';
import { FormControl, FormLabel, Text } from '@chakra-ui/react';
import ParameterSelect from './common/ParameterSelect';

interface FormErrors {
  regio?: string;
  lidmaatschap?: string;
  motormerk?: string;
}

interface FormTouched {
  regio?: boolean;
  lidmaatschap?: boolean;
  motormerk?: boolean;
}

interface FieldComponentProps {
  errors: FormErrors;
  touched: FormTouched;
}

// Example of how to use ParameterSelect in forms
export const RegioField: React.FC<FieldComponentProps> = ({ errors, touched }) => (
  <Field name="regio">
    {({ field }: FieldProps) => (
      <FormControl isInvalid={errors.regio && touched.regio}>
        <FormLabel color="orange.300">Regio *</FormLabel>
        <ParameterSelect
          category="Regio"
          placeholder="Selecteer regio"
          value={field.value}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => field.onChange(e)}
          name={field.name}
          bg="gray.200"
          color="black"
          focusBorderColor="orange.400"
        />
        {errors.regio && touched.regio && (
          <Text color="red.400" fontSize="sm">{errors.regio}</Text>
        )}
      </FormControl>
    )}
  </Field>
);

export const LidmaatschapField: React.FC<FieldComponentProps> = ({ errors, touched }) => (
  <Field name="lidmaatschap">
    {({ field }: FieldProps) => (
      <FormControl isInvalid={errors.lidmaatschap && touched.lidmaatschap}>
        <FormLabel color="orange.300">Soort lidmaatschap *</FormLabel>
        <ParameterSelect
          category="Lidmaatschap"
          placeholder="Selecteer lidmaatschap"
          value={field.value}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => field.onChange(e)}
          name={field.name}
          bg="gray.200"
          color="black"
          focusBorderColor="orange.400"
        />
        {errors.lidmaatschap && touched.lidmaatschap && (
          <Text color="red.400" fontSize="sm">{errors.lidmaatschap}</Text>
        )}
      </FormControl>
    )}
  </Field>
);

export const MotormerkField: React.FC<FieldComponentProps> = ({ errors, touched }) => (
  <Field name="motormerk">
    {({ field }: FieldProps) => (
      <FormControl isInvalid={errors.motormerk && touched.motormerk}>
        <FormLabel color="orange.300">Motormerk *</FormLabel>
        <ParameterSelect
          category="Motormerk"
          placeholder="Selecteer motormerk"
          value={field.value}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => field.onChange(e)}
          name={field.name}
          bg="gray.200"
          color="black"
          focusBorderColor="orange.400"
        />
        {errors.motormerk && touched.motormerk && (
          <Text color="red.400" fontSize="sm">{errors.motormerk}</Text>
        )}
      </FormControl>
    )}
  </Field>
);
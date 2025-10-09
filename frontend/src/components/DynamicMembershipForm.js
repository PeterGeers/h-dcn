import React from 'react';
import { Field } from 'formik';
import { FormControl, FormLabel, Text } from '@chakra-ui/react';
import ParameterSelect from './ParameterSelect';

// Example of how to use ParameterSelect in forms
export const RegioField = ({ errors, touched }) => (
  <Field name="regio">
    {({ field }) => (
      <FormControl isInvalid={errors.regio && touched.regio}>
        <FormLabel color="orange.300">Regio *</FormLabel>
        <ParameterSelect
          category="Regio"
          placeholder="Selecteer regio"
          value={field.value}
          onChange={field.onChange}
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

export const LidmaatschapField = ({ errors, touched }) => (
  <Field name="lidmaatschap">
    {({ field }) => (
      <FormControl isInvalid={errors.lidmaatschap && touched.lidmaatschap}>
        <FormLabel color="orange.300">Soort lidmaatschap *</FormLabel>
        <ParameterSelect
          category="Lidmaatschap"
          placeholder="Selecteer lidmaatschap"
          value={field.value}
          onChange={field.onChange}
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

export const MotormerkField = ({ errors, touched }) => (
  <Field name="motormerk">
    {({ field }) => (
      <FormControl isInvalid={errors.motormerk && touched.motormerk}>
        <FormLabel color="orange.300">Motormerk *</FormLabel>
        <ParameterSelect
          category="Motormerk"
          placeholder="Selecteer motormerk"
          value={field.value}
          onChange={field.onChange}
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
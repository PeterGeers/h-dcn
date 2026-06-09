/**
 * PersonCard — Card for a single person (delegate or guest) with their products.
 *
 * Allows editing name, role, adding/removing products, and configuring
 * product fields for each person in the booking.
 *
 * Validates: Requirement 11.1 (person-centric wizard)
 */

import React from 'react';
import {
  Box,
  FormControl,
  FormErrorMessage,
  FormLabel,
  HStack,
  IconButton,
  Input,
  Select,
  VStack,
} from '@chakra-ui/react';
import { CloseIcon } from '@chakra-ui/icons';
import { Product } from '../types/presmeet.types';
import { PersonFormEntry, PersonProduct } from '../utils/orderTransformer';
import { formatCurrency } from '../utils/priceCalculator';
import ProductConfigurator from './ProductConfigurator';

export interface PersonCardProps {
  person: PersonFormEntry;
  personIndex: number;
  products: Product[];
  onUpdate: (index: number, person: PersonFormEntry) => void;
  onRemove: (index: number) => void;
  isDisabled?: boolean;
  /** Validation errors for this person's fields, keyed by product index then field id */
  fieldErrors?: Record<number, Record<string, string>>;
  /** Validation errors for person-level fields (name, role) */
  personErrors?: Record<string, string>;
}

const PersonCard: React.FC<PersonCardProps> = ({
  person,
  personIndex,
  products,
  onUpdate,
  onRemove,
  isDisabled = false,
  fieldErrors = {},
  personErrors = {},
}) => {
  const handleNameChange = (name: string) => {
    onUpdate(personIndex, { ...person, name });
  };

  const handleRoleChange = (role: string) => {
    onUpdate(personIndex, { ...person, role });
  };

  const handleProductFieldsChange = (
    productIndex: number,
    fields: Record<string, any>,
    variantId: string | null
  ) => {
    const updatedProducts = [...person.products];
    updatedProducts[productIndex] = {
      ...updatedProducts[productIndex],
      fields,
      variant_id: variantId,
    };
    onUpdate(personIndex, { ...person, products: updatedProducts });
  };

  const handleAddProduct = (productId: string) => {
    const newProduct: PersonProduct = {
      product_id: productId,
      variant_id: null,
      fields: {},
    };
    onUpdate(personIndex, {
      ...person,
      products: [...person.products, newProduct],
    });
  };

  const handleRemoveProduct = (productIndex: number) => {
    const updatedProducts = person.products.filter((_, i) => i !== productIndex);
    onUpdate(personIndex, { ...person, products: updatedProducts });
  };

  const productMap = new Map(products.map((p) => [p.product_id, p]));

  // Products not yet assigned to this person
  const availableProducts = products.filter(
    (p) => !person.products.some((pp) => pp.product_id === p.product_id)
  );

  return (
    <Box borderWidth={1} borderRadius="lg" p={4} position="relative">
      {!isDisabled && (
        <IconButton
          aria-label="Remove person"
          icon={<CloseIcon />}
          size="xs"
          position="absolute"
          top={2}
          right={2}
          variant="ghost"
          colorScheme="red"
          onClick={() => onRemove(personIndex)}
        />
      )}

      <VStack spacing={3} align="stretch">
        {/* Person identity */}
        <HStack spacing={3}>
          <FormControl flex={2} isInvalid={!!personErrors.name}>
            <FormLabel fontSize="xs">Name</FormLabel>
            <Input
              size="sm"
              value={person.name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="Full name"
              isDisabled={isDisabled}
            />
            {personErrors.name && (
              <FormErrorMessage fontSize="xs">{personErrors.name}</FormErrorMessage>
            )}
          </FormControl>
          <FormControl flex={1} isInvalid={!!personErrors.role}>
            <FormLabel fontSize="xs">Role</FormLabel>
            <Input
              size="sm"
              value={person.role}
              onChange={(e) => handleRoleChange(e.target.value)}
              placeholder="e.g. President"
              isDisabled={isDisabled}
            />
            {personErrors.role && (
              <FormErrorMessage fontSize="xs">{personErrors.role}</FormErrorMessage>
            )}
          </FormControl>
        </HStack>

        {/* Assigned products */}
        {person.products.map((pp, pIdx) => {
          const productDef = productMap.get(pp.product_id);
          if (!productDef) return null;
          return (
            <Box key={pIdx} position="relative">
              {!isDisabled && (
                <IconButton
                  aria-label={`Remove ${productDef.name}`}
                  icon={<CloseIcon />}
                  size="xs"
                  position="absolute"
                  top={0}
                  right={0}
                  variant="ghost"
                  colorScheme="red"
                  onClick={() => handleRemoveProduct(pIdx)}
                />
              )}
              <ProductConfigurator
                product={productDef}
                fields={pp.fields}
                variantId={pp.variant_id}
                onChange={(fields, variantId) =>
                  handleProductFieldsChange(pIdx, fields, variantId)
                }
                isDisabled={isDisabled}
                fieldErrors={fieldErrors[pIdx]}
              />
            </Box>
          );
        })}

        {/* Add product button */}
        {!isDisabled && availableProducts.length > 0 && (
          <Select
            size="sm"
            placeholder="+ Add product"
            onChange={(e) => {
              if (e.target.value) {
                handleAddProduct(e.target.value);
                e.target.value = '';
              }
            }}
          >
            {availableProducts.map((p) => (
              <option key={p.product_id} value={p.product_id}>
                {p.name} ({formatCurrency(p.price)})
              </option>
            ))}
          </Select>
        )}
      </VStack>
    </Box>
  );
};

export default PersonCard;

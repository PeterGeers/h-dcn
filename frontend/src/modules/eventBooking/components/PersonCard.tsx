/**
 * PersonCard — Card for a single person (delegate or guest) with their products.
 *
 * Allows editing name, role, adding/removing products, and configuring
 * product fields for each person in the booking.
 *
 * When a product has variant_schema defined, the variant selection dropdowns
 * are rendered via ProductConfigurator and the variant_id must map to a valid
 * variant before the product line is considered complete.
 *
 * When a product has order_item_fields defined, the dynamic fields are rendered
 * via ProductConfigurator.
 *
 * Validates: Requirements 7.6, 7.7
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
  Text,
  VStack,
} from '@chakra-ui/react';
import { CloseIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { Product } from '../types/eventBooking.types';
import { PersonFormEntry, PersonProduct } from '../utils/orderTransformer';
import { formatCurrency } from '../utils/priceCalculator';
import ProductConfigurator, { isVariantSelectionIncomplete } from './ProductConfigurator';
import { ProductEffectiveLimit } from '../hooks/useEffectiveLimits';

export interface PersonCardProps {
  person: PersonFormEntry;
  personIndex: number;
  products: Product[];
  onUpdate: (index: number, person: PersonFormEntry) => void;
  onRemove: (index: number) => void;
  isDisabled?: boolean;
  /** Whether removal of this person is prevented (e.g. first person = delegate) */
  preventRemoval?: boolean;
  /** Validation errors for this person's fields, keyed by product index then field id */
  fieldErrors?: Record<number, Record<string, string>>;
  /** Validation errors for person-level fields (name, role) */
  personErrors?: Record<string, string>;
  /** Effective limits per product (for displaying "X of Y remaining") */
  effectiveLimits?: ProductEffectiveLimit[];
}

const PersonCard: React.FC<PersonCardProps> = ({
  person,
  personIndex,
  products,
  onUpdate,
  onRemove,
  isDisabled = false,
  preventRemoval = false,
  fieldErrors = {},
  personErrors = {},
  effectiveLimits = [],
}) => {
  const { t } = useTranslation('eventBooking');

  const handleNameChange = (name: string) => {
    onUpdate(personIndex, { ...person, name });
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
    const productDef = products.find((p) => p.product_id === productId);
    if (!productDef) return;

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

  // Show role field only if a product assigned to this person requires it
  // NOTE: role is actually handled by ProductConfigurator via order_item_fields.
  // The person-level role field is kept for backward compatibility with existing orders
  // that stored role at person level. New orders should use order_item_fields.

  // Products not yet assigned to this person
  const availableProducts = products.filter(
    (p) => !person.products.some((pp) => pp.product_id === p.product_id)
  );

  return (
    <Box borderWidth={1} borderColor="gray.600" borderRadius="lg" p={4} position="relative" bg="gray.800">
      {!isDisabled && !preventRemoval && (
        <IconButton
          aria-label={t('person_card.remove_person')}
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
          <FormControl isInvalid={!!personErrors.name}>
            <FormLabel fontSize="xs">{t('person_card.name')}</FormLabel>
            <Input
              size="sm"
              value={person.name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder={t('person_card.name_placeholder')}
              isDisabled={isDisabled}
            />
            {personErrors.name && (
              <FormErrorMessage fontSize="xs">{personErrors.name}</FormErrorMessage>
            )}
          </FormControl>
        </HStack>

        {/* Assigned products with variant + dynamic field configuration */}
        {person.products.map((pp, pIdx) => {
          const productDef = productMap.get(pp.product_id);
          if (!productDef) return null;

          // Check if variant selection is incomplete for this product line
          const variantIncomplete = isVariantSelectionIncomplete(
            productDef,
            pp.fields,
            pp.variant_id
          );

          return (
            <Box key={pIdx} position="relative">
              {!isDisabled && (
                <IconButton
                  aria-label={t('person_card.remove_product', { product: productDef.naam })}
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
              {/* Variant incomplete indicator */}
              {variantIncomplete && !isDisabled && (
                <Text fontSize="xs" color="orange.600" mt={1} pl={4}>
                  {t('person_card.variant_required')}
                </Text>
              )}
            </Box>
          );
        })}

        {/* Add product button */}
        {!isDisabled && availableProducts.length > 0 && (
          <Select
            size="sm"
            placeholder={t('person_card.add_product')}
            bg="gray.700"
            borderColor="gray.600"
            color="white"
            _placeholder={{ color: 'gray.400' }}
            onChange={(e) => {
              if (e.target.value) {
                handleAddProduct(e.target.value);
                e.target.value = '';
              }
            }}
          >
            {availableProducts.map((p) => (
              <option key={p.product_id} value={p.product_id} style={{ backgroundColor: '#2D3748', color: 'white' }}>
                {p.naam} ({formatCurrency(p.prijs)})
              </option>
            ))}
          </Select>
        )}
      </VStack>
    </Box>
  );
};

export default PersonCard;

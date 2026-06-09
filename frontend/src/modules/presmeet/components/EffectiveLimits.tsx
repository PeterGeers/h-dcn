/**
 * EffectiveLimits — Shows effective capacity limits per product.
 *
 * Displays min(max_per_club, event_remaining) for each product so the
 * delegate sees realistic limits before submitting.
 *
 * Validates: Requirement 6.4
 */

import React from 'react';
import { Box, HStack, Text, VStack } from '@chakra-ui/react';
import { Constraint, Product } from '../types/presmeet.types';

export interface EffectiveLimitsProps {
  products: Product[];
  constraints: Constraint[];
  currentPersonCount: number;
}

const EffectiveLimits: React.FC<EffectiveLimitsProps> = ({
  products,
  constraints,
}) => {
  return (
    <Box p={3} borderWidth={1} borderRadius="md" bg="blue.50">
      <Text fontSize="sm" fontWeight="medium" mb={2}>
        Available capacity
      </Text>
      <VStack spacing={1} align="stretch">
        {products.map((product) => {
          const maxPerClub = product.purchase_rules.max_per_club ?? Infinity;
          // Find event constraint for this product
          const constraint = constraints.find((c) => c.product_id === product.product_id);
          const eventRemaining = constraint ? constraint.max : Infinity;
          const effectiveLimit = Math.min(maxPerClub, eventRemaining);

          return (
            <HStack key={product.product_id} justify="space-between" fontSize="xs">
              <Text>{product.name}</Text>
              <Text color="gray.600">
                max {effectiveLimit === Infinity ? '∞' : effectiveLimit} per club
              </Text>
            </HStack>
          );
        })}
      </VStack>
    </Box>
  );
};

export default EffectiveLimits;

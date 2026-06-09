/**
 * ReadOnlyView — Displays order data in read-only mode when event is not open.
 *
 * Shows persons, their products, and the order total/status without any
 * editing capability. Used when event status is 'closed', 'draft', or 'archived'.
 *
 * Validates: Requirement 11.4
 */

import React from 'react';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  HStack,
  Text,
  VStack,
} from '@chakra-ui/react';
import { Event, Order, Product } from '../types/presmeet.types';
import { orderItemsToFormState } from '../utils/orderTransformer';
import { formatCurrency } from '../utils/priceCalculator';

export interface ReadOnlyViewProps {
  order: Order;
  event: Event;
  products: Product[];
}

const ReadOnlyView: React.FC<ReadOnlyViewProps> = ({ order, event, products }) => {
  const productMap = new Map(products.map((p) => [p.product_id, p]));
  const formState = orderItemsToFormState(order.items);

  return (
    <Box>
      <Alert status="info" borderRadius="md" mb={6}>
        <AlertIcon />
        <AlertDescription>
          {event.status === 'closed'
            ? 'Registration is closed. Your booking is shown below in read-only mode.'
            : event.status === 'draft'
              ? 'Registration is not yet open. Check back after the registration open date.'
              : 'This event is archived. Your booking is shown below for reference.'}
        </AlertDescription>
      </Alert>

      {formState.persons.length === 0 ? (
        <Text color="gray.500">No persons registered for this event.</Text>
      ) : (
        <VStack spacing={4} align="stretch">
          {formState.persons.map((person, idx) => (
            <Box key={idx} borderWidth={1} borderRadius="md" p={4}>
              <HStack mb={2}>
                <Text fontWeight="bold">{person.name || `Person ${idx + 1}`}</Text>
                {person.role && (
                  <Badge colorScheme="blue">{person.role}</Badge>
                )}
              </HStack>
              {person.products.map((pp, pIdx) => {
                const productDef = productMap.get(pp.product_id);
                return (
                  <Box key={pIdx} ml={4} mt={2}>
                    <Text fontSize="sm" fontWeight="medium">
                      {productDef?.name || pp.product_id}
                    </Text>
                    {Object.entries(pp.fields).length > 0 && (
                      <Box ml={2} mt={1}>
                        {Object.entries(pp.fields).map(([key, value]) => (
                          <Text key={key} fontSize="xs" color="gray.600">
                            {key}: {String(value)}
                          </Text>
                        ))}
                      </Box>
                    )}
                  </Box>
                );
              })}
            </Box>
          ))}
        </VStack>
      )}

      <Box mt={6} p={4} borderWidth={1} borderRadius="md" bg="gray.50">
        <HStack justify="space-between">
          <Text fontWeight="bold">Total</Text>
          <Text fontWeight="bold" fontSize="lg">
            {formatCurrency(order.total_amount)}
          </Text>
        </HStack>
        <HStack mt={2} spacing={4}>
          <Badge colorScheme={order.status === 'submitted' ? 'green' : 'gray'}>
            {order.status}
          </Badge>
          <Badge
            colorScheme={
              order.payment_status === 'paid'
                ? 'green'
                : order.payment_status === 'partial'
                  ? 'yellow'
                  : 'red'
            }
          >
            {order.payment_status}
          </Badge>
        </HStack>
      </Box>
    </Box>
  );
};

export default ReadOnlyView;

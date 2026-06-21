/**
 * ReadOnlyView — Displays order data in read-only mode.
 *
 * Shows persons, their products, and the order total/status without any
 * editing capability. Used in two scenarios:
 * 1. Event-level: event status is 'closed', 'draft', or 'archived'
 * 2. Order-level: order status is 'submitted' or 'locked' (Requirement 10.2)
 *
 * All form fields are disabled, add/remove person actions are hidden,
 * and no save or submit actions are available.
 *
 * Validates: Requirements 10.2, 11.4
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
import { useTranslation } from 'react-i18next';
import { Event, Order, Product } from '../types/presmeet.types';
import { orderItemsToFormState } from '../utils/orderTransformer';
import { formatCurrency } from '../utils/priceCalculator';

export type ReadOnlyReason = 'event_closed' | 'event_draft' | 'event_archived' | 'order_submitted' | 'order_locked';

export interface ReadOnlyViewProps {
  order: Order;
  event: Event;
  products: Product[];
  /** Reason for rendering in read-only mode. Defaults to event-level detection. */
  reason?: ReadOnlyReason;
}

/**
 * Determine the read-only reason from event/order state when not explicitly provided.
 */
function detectReason(event: Event, order: Order): ReadOnlyReason {
  if (order.status === 'submitted') return 'order_submitted';
  if (order.status === 'locked') return 'order_locked';
  if (event.status === 'closed') return 'event_closed';
  if (event.status === 'draft') return 'event_draft';
  return 'event_archived';
}

const ReadOnlyView: React.FC<ReadOnlyViewProps> = ({ order, event, products, reason }) => {
  const { t } = useTranslation('eventBooking');
  const productMap = new Map(products.map((p) => [p.product_id, p]));
  const formState = orderItemsToFormState(order.items);
  const effectiveReason = reason ?? detectReason(event, order);

  const getAlertStatus = (): 'info' | 'warning' => {
    if (effectiveReason === 'order_submitted' || effectiveReason === 'order_locked') {
      return 'info';
    }
    return 'info';
  };

  const getBannerMessage = (): string => {
    switch (effectiveReason) {
      case 'order_submitted':
        return t('read_only.order_submitted');
      case 'order_locked':
        return t('read_only.order_locked');
      case 'event_closed':
        return t('read_only.event_closed');
      case 'event_draft':
        return t('read_only.event_draft');
      case 'event_archived':
      default:
        return t('read_only.event_archived');
    }
  };

  return (
    <Box>
      <Alert status={getAlertStatus()} borderRadius="md" mb={6}>
        <AlertIcon />
        <AlertDescription>{getBannerMessage()}</AlertDescription>
      </Alert>

      {formState.persons.length === 0 ? (
        <Text color="gray.500">{t('read_only.no_persons')}</Text>
      ) : (
        <VStack spacing={4} align="stretch">
          {formState.persons.map((person, idx) => (
            <Box key={idx} borderWidth={1} borderRadius="md" p={4}>
              <HStack mb={2}>
                <Text fontWeight="bold">{person.name || `${t('read_only.person')} ${idx + 1}`}</Text>
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
                        {Object.entries(pp.fields)
                          .filter(([key]) => key !== 'name' && key !== 'role')
                          .map(([key, value]) => (
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
          <Text fontWeight="bold">{t('read_only.total')}</Text>
          <Text fontWeight="bold" fontSize="lg">
            {formatCurrency(order.total_amount)}
          </Text>
        </HStack>
        <HStack mt={2} spacing={4}>
          <Badge colorScheme={order.status === 'submitted' ? 'green' : order.status === 'locked' ? 'purple' : 'gray'}>
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

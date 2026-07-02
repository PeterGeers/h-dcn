/**
 * EventPickList Component
 *
 * Shows all paid orders for a specific event in a pick-list format.
 * Designed for event fulfilment workflow:
 *   - View all paid orders that need to be prepared for pickup
 *   - Bulk action: mark selected as "ready_for_pickup"
 *   - Handout check: mark individual orders as "picked_up"
 *
 * Validates: Requirements 9.4, 9.5, 9.6, 9.7, 10.4
 */

import React, { useState, useMemo, useCallback } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  Checkbox,
  Button,
  HStack,
  VStack,
  Badge,
  Spinner,
  Alert,
  AlertIcon,
  useToast,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { useAdminOrders } from '../hooks/useAdminOrders';
import { useAdminPermissions } from '../hooks/useAdminPermissions';
import { updateOrderStatus } from '../services/adminApi';
import { StatusBadge } from './StatusBadge';
import { AdminOrder, OrderStatus } from '../types/admin.types';

export interface EventPickListProps {
  /** Event ID to filter orders for */
  eventId: string;
}

type PickListStatus = 'paid' | 'ready_for_pickup' | 'picked_up';

const PICK_LIST_STATUSES: PickListStatus[] = ['paid', 'ready_for_pickup', 'picked_up'];

function formatVariantLine(item: { name: string; quantity: number; variant_attributes?: Record<string, string> }): string {
  const variant = item.variant_attributes
    ? Object.values(item.variant_attributes).join(', ')
    : '';
  return `${item.name}${variant ? ` (${variant})` : ''} × ${item.quantity}`;
}

export const EventPickList: React.FC<EventPickListProps> = ({ eventId }) => {
  const { t } = useTranslation('webshop');
  const toast = useToast();
  const { canMutate } = useAdminPermissions();
  const { orders, loading, error, refetch } = useAdminOrders(eventId);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkLoading, setBulkLoading] = useState(false);

  // Filter to only show orders relevant to the pick-list (paid, ready_for_pickup, picked_up)
  const pickListOrders = useMemo(() => {
    return orders.filter((o) => PICK_LIST_STATUSES.includes(o.status as PickListStatus));
  }, [orders]);

  // Group by status for visual clarity
  const paidOrders = useMemo(() => pickListOrders.filter((o) => o.status === 'paid'), [pickListOrders]);
  const readyOrders = useMemo(() => pickListOrders.filter((o) => o.status === 'ready_for_pickup'), [pickListOrders]);
  const pickedUpOrders = useMemo(() => pickListOrders.filter((o) => o.status === 'picked_up'), [pickListOrders]);

  const toggleSelect = useCallback((orderId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(orderId)) {
        next.delete(orderId);
      } else {
        next.add(orderId);
      }
      return next;
    });
  }, []);

  const selectAllPaid = useCallback(() => {
    setSelectedIds(new Set(paidOrders.map((o) => o.order_id)));
  }, [paidOrders]);

  const deselectAll = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const handleBulkTransition = async (targetStatus: OrderStatus) => {
    if (selectedIds.size === 0) return;
    setBulkLoading(true);
    let successCount = 0;
    let failCount = 0;

    for (const orderId of selectedIds) {
      try {
        await updateOrderStatus(orderId, targetStatus);
        successCount++;
      } catch {
        failCount++;
      }
    }

    setBulkLoading(false);
    setSelectedIds(new Set());

    toast({
      title: `${successCount} bestelling(en) bijgewerkt`,
      description: failCount > 0 ? `${failCount} mislukt` : undefined,
      status: failCount > 0 ? 'warning' : 'success',
      duration: 4000,
      isClosable: true,
    });

    refetch();
  };

  const handleSinglePickup = async (orderId: string) => {
    try {
      await updateOrderStatus(orderId, 'picked_up');
      toast({
        title: 'Uitgereikt',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
      refetch();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Fout bij uitreiken';
      toast({
        title: 'Fout',
        description: message,
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
    }
  };

  if (loading) {
    return (
      <Box p={8} textAlign="center">
        <Spinner size="lg" color="orange.400" />
        <Text mt={2} color="gray.400">Pick-list laden...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert status="error" borderRadius="md">
        <AlertIcon />
        {error}
      </Alert>
    );
  }

  if (pickListOrders.length === 0) {
    return (
      <Box p={8} textAlign="center">
        <Text color="gray.400">Geen betaalde bestellingen voor dit event.</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
      {/* Bulk action toolbar */}
      <HStack spacing={3} p={3} bg="gray.800" borderRadius="md" border="1px" borderColor="gray.600">
        <Button size="sm" variant="outline" onClick={selectAllPaid} isDisabled={paidOrders.length === 0}>
          Selecteer alle betaalde ({paidOrders.length})
        </Button>
        <Button size="sm" variant="outline" onClick={deselectAll} isDisabled={selectedIds.size === 0}>
          Deselecteer
        </Button>
        <Button
          size="sm"
          colorScheme="orange"
          isLoading={bulkLoading}
          isDisabled={!canMutate || selectedIds.size === 0}
          onClick={() => handleBulkTransition('ready_for_pickup')}
        >
          Klaarzetten ({selectedIds.size})
        </Button>
        <Text fontSize="xs" color="gray.400" ml="auto">
          {paidOrders.length} betaald · {readyOrders.length} klaar · {pickedUpOrders.length} uitgereikt
        </Text>
      </HStack>

      {/* Pick-list table */}
      <Box overflowX="auto">
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              <Th w="40px" />
              <Th>Klant / Club</Th>
              <Th>Producten</Th>
              <Th>Status</Th>
              <Th>Actie</Th>
            </Tr>
          </Thead>
          <Tbody>
            {pickListOrders.map((order) => (
              <Tr
                key={order.order_id}
                bg={order.status === 'picked_up' ? 'green.900' : undefined}
                opacity={order.status === 'picked_up' ? 0.7 : 1}
              >
                <Td>
                  {order.status !== 'picked_up' && (
                    <Checkbox
                      isChecked={selectedIds.has(order.order_id)}
                      onChange={() => toggleSelect(order.order_id)}
                      colorScheme="orange"
                    />
                  )}
                </Td>
                <Td>
                  <Text fontSize="sm" fontWeight="bold">
                    {order.customer_name}
                  </Text>
                  {order.club_name && (
                    <Text fontSize="xs" color="gray.400">{order.club_name}</Text>
                  )}
                </Td>
                <Td>
                  {order.items.map((item, idx) => (
                    <Text key={idx} fontSize="xs">
                      {formatVariantLine(item)}
                    </Text>
                  ))}
                </Td>
                <Td>
                  <StatusBadge status={order.status} />
                </Td>
                <Td>
                  {order.status === 'ready_for_pickup' && (
                    <Button
                      size="xs"
                      colorScheme="green"
                      isDisabled={!canMutate}
                      onClick={() => handleSinglePickup(order.order_id)}
                    >
                      Uitreiken
                    </Button>
                  )}
                  {order.status === 'picked_up' && (
                    <Badge colorScheme="green" fontSize="xs">✓</Badge>
                  )}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>
    </VStack>
  );
};

export default EventPickList;

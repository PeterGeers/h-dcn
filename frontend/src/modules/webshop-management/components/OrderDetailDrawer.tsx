/**
 * OrderDetailDrawer Component
 *
 * Chakra Drawer showing full order details including:
 * - Line items table (product_type, name, variant_attributes, quantity, unit_price)
 * - Payment history (amount, date, description, recorded_by)
 * - Status transition history (from → to, timestamp, triggered_by)
 * - State transition controls (Next Status, Lock, Unlock, Lock ALL)
 * - Role-based action gating for Products_Read-only users
 *
 * Validates: Requirements 4.6, 4.7, 4.8, 4.9, 4.10, 4.13, 4.14, 4.17, 7.2, 12.6
 */

import React, { useState } from 'react';
import {
  Drawer,
  DrawerOverlay,
  DrawerContent,
  DrawerHeader,
  DrawerBody,
  DrawerCloseButton,
  Box,
  Button,
  HStack,
  VStack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  Heading,
  Badge,
  Divider,
  Tooltip,
  useToast,
} from '@chakra-ui/react';
import { useAdminPermissions } from '../hooks/useAdminPermissions';
import { StatusBadge } from './StatusBadge';
import {
  updateOrderStatus,
  lockOrders,
  unlockOrder,
} from '../services/adminApi';
import {
  AdminOrder,
  OrderStatus,
  OrderLineItem,
  StatusHistoryEntry,
  PaymentRecord,
} from '../types/admin.types';

export interface OrderDetailDrawerProps {
  order: AdminOrder;
  isOpen: boolean;
  onClose: () => void;
  onOrderUpdated: () => void;
  eventFilter: string;
}

/**
 * Ordered states for determining "next status" in the linear flow.
 */
const ORDERED_STATES: OrderStatus[] = [
  'draft',
  'submitted',
  'locked',
  'order_received',
  'payment_pending',
  'paid',
  'picked',
  'packed',
  'shipped',
  'delivered',
  'return_requested',
  'return_received',
  'completed',
];

/**
 * Get the next logical status in the ordered sequence.
 * Returns null if there's no simple "next" status.
 */
function getNextStatus(current: OrderStatus): OrderStatus | null {
  const idx = ORDERED_STATES.indexOf(current);
  if (idx === -1 || idx >= ORDERED_STATES.length - 1) return null;
  // Skip payment_failed (terminal state)
  if (current === 'payment_failed') return null;
  return ORDERED_STATES[idx + 1];
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleString('nl-NL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

function formatCurrency(amount: number): string {
  return `€ ${(Number(amount) || 0).toFixed(2)}`;
}

/**
 * Format variant_attributes as a readable string (e.g., "Maat: M, Kleur: Zwart")
 */
function formatVariantAttributes(attrs?: Record<string, string>): string {
  if (!attrs || Object.keys(attrs).length === 0) return '—';
  return Object.entries(attrs)
    .map(([key, value]) => `${key}: ${value}`)
    .join(', ');
}

export const OrderDetailDrawer: React.FC<OrderDetailDrawerProps> = ({
  order,
  isOpen,
  onClose,
  onOrderUpdated,
  eventFilter,
}) => {
  const { canMutate } = useAdminPermissions();
  const toast = useToast();
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  const disabledTooltip = 'Je hebt geen rechten om deze actie uit te voeren (Products_CRUD vereist)';

  const nextStatus = getNextStatus(order.status);

  const handleNextStatus = async () => {
    if (!nextStatus) return;
    setLoadingAction('next');
    try {
      await updateOrderStatus(order.order_id, nextStatus);
      toast({
        title: 'Status bijgewerkt',
        description: `Bestelling naar "${nextStatus}" gezet.`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onOrderUpdated();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Status wijzigen mislukt';
      toast({
        title: 'Fout',
        description: message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoadingAction(null);
    }
  };

  const handleLock = async () => {
    setLoadingAction('lock');
    try {
      await updateOrderStatus(order.order_id, 'locked');
      toast({
        title: 'Bestelling vergrendeld',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onOrderUpdated();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Vergrendelen mislukt';
      toast({
        title: 'Fout',
        description: message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoadingAction(null);
    }
  };

  const handleUnlock = async () => {
    setLoadingAction('unlock');
    try {
      await unlockOrder(order.order_id);
      toast({
        title: 'Bestelling ontgrendeld',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onOrderUpdated();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Ontgrendelen mislukt';
      toast({
        title: 'Fout',
        description: message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoadingAction(null);
    }
  };

  const handleLockAll = async () => {
    setLoadingAction('lockAll');
    try {
      await lockOrders(eventFilter || undefined);
      toast({
        title: 'Alle bestellingen vergrendeld',
        description: 'Alle ingediende bestellingen zijn vergrendeld.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onOrderUpdated();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Bulk vergrendelen mislukt';
      toast({
        title: 'Fout',
        description: message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <Drawer isOpen={isOpen} onClose={onClose} size="lg" placement="right">
      <DrawerOverlay />
      <DrawerContent bg="gray.800">
        <DrawerCloseButton />
        <DrawerHeader borderBottomWidth="1px" borderColor="gray.600">
          <HStack spacing={3}>
            <Text>Bestelling</Text>
            <Text fontFamily="mono" fontSize="sm" color="gray.400">
              {order.order_id}
            </Text>
          </HStack>
        </DrawerHeader>

        <DrawerBody py={4}>
          <VStack spacing={6} align="stretch">
            {/* Order Summary */}
            <Box>
              <HStack spacing={4} mb={2}>
                <StatusBadge status={order.status} />
                <Badge
                  colorScheme={order.event_id ? 'purple' : 'blue'}
                >
                  {order.event_id || 'Webshop'}
                </Badge>
              </HStack>
              <Text fontSize="sm">
                <strong>Klant:</strong> {order.customer_name}
              </Text>
              {order.club_name && (
                <Text fontSize="sm">
                  <strong>Club:</strong> {order.club_name}
                </Text>
              )}
              <HStack spacing={6} mt={2}>
                <Text fontSize="sm">
                  <strong>Totaal:</strong> {formatCurrency(order.total_amount)}
                </Text>
                <Text fontSize="sm">
                  <strong>Betaald:</strong> {formatCurrency(order.amount_paid)}
                </Text>
                <Text fontSize="sm">
                  <strong>Openstaand:</strong> {formatCurrency(order.outstanding)}
                </Text>
              </HStack>
            </Box>

            {/* Action Buttons */}
            <Box>
              <Heading size="xs" mb={2}>Acties</Heading>
              <HStack spacing={2} flexWrap="wrap">
                {/* Next Status button */}
                {nextStatus && (
                  <Tooltip
                    label={canMutate ? `Naar "${nextStatus}"` : disabledTooltip}
                    hasArrow
                  >
                    <Button
                      size="sm"
                      colorScheme="orange"
                      isLoading={loadingAction === 'next'}
                      isDisabled={!canMutate || loadingAction !== null}
                      onClick={handleNextStatus}
                    >
                      Volgende status
                    </Button>
                  </Tooltip>
                )}

                {/* Lock button — only for submitted orders */}
                {order.status === 'submitted' && (
                  <Tooltip
                    label={canMutate ? 'Vergrendel bestelling' : disabledTooltip}
                    hasArrow
                  >
                    <Button
                      size="sm"
                      colorScheme="green"
                      isLoading={loadingAction === 'lock'}
                      isDisabled={!canMutate || loadingAction !== null}
                      onClick={handleLock}
                    >
                      Lock
                    </Button>
                  </Tooltip>
                )}

                {/* Unlock button — only for locked orders */}
                {order.status === 'locked' && (
                  <Tooltip
                    label={canMutate ? 'Ontgrendel bestelling' : disabledTooltip}
                    hasArrow
                  >
                    <Button
                      size="sm"
                      colorScheme="yellow"
                      isLoading={loadingAction === 'unlock'}
                      isDisabled={!canMutate || loadingAction !== null}
                      onClick={handleUnlock}
                    >
                      Unlock
                    </Button>
                  </Tooltip>
                )}

                {/* Lock ALL button */}
                <Tooltip
                  label={
                    canMutate
                      ? 'Vergrendel alle ingediende bestellingen'
                      : disabledTooltip
                  }
                  hasArrow
                >
                  <Button
                    size="sm"
                    colorScheme="teal"
                    variant="outline"
                    isLoading={loadingAction === 'lockAll'}
                    isDisabled={!canMutate || loadingAction !== null}
                    onClick={handleLockAll}
                  >
                    Lock ALL
                  </Button>
                </Tooltip>
              </HStack>
            </Box>

            <Divider borderColor="gray.600" />

            {/* Line Items */}
            <Box>
              <Heading size="xs" mb={2}>Artikelen</Heading>
              <Box overflowX="auto">
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Type</Th>
                      <Th>Naam</Th>
                      <Th>Varianten</Th>
                      <Th isNumeric>Aantal</Th>
                      <Th isNumeric>Prijs</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {order.items.map((item: OrderLineItem, idx: number) => (
                      <Tr key={idx}>
                        <Td>
                          <Badge fontSize="xs" colorScheme="gray">
                            {item.product_type || '—'}
                          </Badge>
                        </Td>
                        <Td fontSize="sm">{item.name}</Td>
                        <Td fontSize="xs">
                          {formatVariantAttributes(item.variant_attributes)}
                        </Td>
                        <Td isNumeric fontSize="sm">{item.quantity}</Td>
                        <Td isNumeric fontSize="sm">
                          {formatCurrency(item.unit_price)}
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            </Box>

            <Divider borderColor="gray.600" />

            {/* Payment History */}
            <Box>
              <Heading size="xs" mb={2}>Betalingsgeschiedenis</Heading>
              {order.payments && order.payments.length > 0 ? (
                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Bedrag</Th>
                        <Th>Datum</Th>
                        <Th>Omschrijving</Th>
                        <Th>Door</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {order.payments.map((payment: PaymentRecord) => (
                        <Tr key={payment.payment_id}>
                          <Td fontSize="sm">
                            {formatCurrency(payment.amount)}
                          </Td>
                          <Td fontSize="xs">{formatDate(payment.date)}</Td>
                          <Td fontSize="xs">{payment.description || '—'}</Td>
                          <Td fontSize="xs">{payment.recorded_by}</Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              ) : (
                <Text fontSize="sm" color="gray.400">
                  Geen betalingen geregistreerd.
                </Text>
              )}
            </Box>

            <Divider borderColor="gray.600" />

            {/* Status History */}
            <Box>
              <Heading size="xs" mb={2}>Statusgeschiedenis</Heading>
              {order.status_history && order.status_history.length > 0 ? (
                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Van</Th>
                        <Th>Naar</Th>
                        <Th>Wanneer</Th>
                        <Th>Door</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {order.status_history.map(
                        (entry: StatusHistoryEntry, idx: number) => (
                          <Tr key={idx}>
                            <Td>
                              <StatusBadge status={entry.from_status} />
                            </Td>
                            <Td>
                              <StatusBadge status={entry.to_status} />
                            </Td>
                            <Td fontSize="xs">{formatDate(entry.timestamp)}</Td>
                            <Td fontSize="xs">{entry.triggered_by}</Td>
                          </Tr>
                        )
                      )}
                    </Tbody>
                  </Table>
                </Box>
              ) : (
                <Text fontSize="sm" color="gray.400">
                  Geen statuswijzigingen geregistreerd.
                </Text>
              )}
            </Box>
          </VStack>
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
};

export default OrderDetailDrawer;

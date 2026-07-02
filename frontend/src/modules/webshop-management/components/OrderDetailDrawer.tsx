/**
 * OrderDetailDrawer Component
 *
 * Chakra Drawer showing full order details including:
 * - Customer & Shipping info (name, email, phone, address)
 * - Line items table (product_type, name, variant_attributes, quantity, unit_price)
 * - Shipping info (tracking_number, carrier, shipped_at) — webshop orders
 * - Pickup info (pickup_location, picked_up_at, picked_up_by) — event orders
 * - Payment history (amount, date, description, recorded_by)
 * - Status transition history (from → to, timestamp, triggered_by)
 * - Context-aware action buttons (valid transitions only)
 * - Shipping modal for tracking input when transitioning to "shipped"
 *
 * Validates: Requirements 4.6, 4.7, 4.8, 4.9, 4.10, 4.13, 4.14, 4.17, 5.3, 5.4, 5.5, 7.2, 12.6
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
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  Input,
  Select,
  FormControl,
  FormLabel,
  SimpleGrid,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { useAdminPermissions } from '../hooks/useAdminPermissions';
import { StatusBadge } from './StatusBadge';
import {
  updateOrderStatus,
  lockOrders,
} from '../services/adminApi';
import {
  downloadOrderPdf,
  downloadPackingSlipPdf,
  downloadShippingLabelPdf,
} from '../../webshop/services/pdfDownloadService';
import {
  AdminOrder,
  OrderStatus,
  OrderLineItem,
  StatusHistoryEntry,
  PaymentRecord,
} from '../types/admin.types';
import { getAdminTransitions, AvailableTransition } from '../utils/orderTransitions';

export interface OrderDetailDrawerProps {
  order: AdminOrder;
  isOpen: boolean;
  onClose: () => void;
  onOrderUpdated: () => void;
  eventFilter?: string;
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
  const { t } = useTranslation('webshop');
  const toast = useToast();
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  // Shipping modal state
  const shippingModal = useDisclosure();
  const [trackingNumber, setTrackingNumber] = useState('');
  const [shippingCarrier, setShippingCarrier] = useState('PostNL');

  const disabledTooltip = 'Je hebt geen rechten om deze actie uit te voeren (Products_CRUD vereist)';

  const isEventOrder = order.source_id ? order.source_id !== 'webshop' : !!order.event_id;
  const availableTransitions = getAdminTransitions(order.status, order.source_id || (order.event_id ? order.event_id : 'webshop'));

  const handleTransition = async (transition: AvailableTransition) => {
    // If transition requires tracking, show the modal
    if (transition.requiresTrackingNumber) {
      setTrackingNumber(order.tracking_number || '');
      setShippingCarrier(order.shipping_carrier || 'PostNL');
      shippingModal.onOpen();
      return;
    }

    await executeTransition(transition.target);
  };

  const executeTransition = async (
    targetStatus: OrderStatus,
    options?: { tracking_number?: string; shipping_carrier?: string }
  ) => {
    setLoadingAction(targetStatus);
    try {
      await updateOrderStatus(order.order_id, targetStatus, options);
      toast({
        title: t('toast.status_updated'),
        description: t('toast.status_updated_desc', { status: targetStatus }),
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onOrderUpdated();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : t('toast.status_update_error');
      toast({
        title: t('toast.error_title'),
        description: message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoadingAction(null);
    }
  };

  const handleShippingConfirm = async () => {
    if (!trackingNumber.trim()) {
      toast({
        title: 'Track & Trace nummer verplicht',
        description: 'Vul een tracking nummer in voordat je de bestelling als verzonden markeert.',
        status: 'warning',
        duration: 4000,
        isClosable: true,
      });
      return;
    }
    shippingModal.onClose();
    await executeTransition('shipped', {
      tracking_number: trackingNumber.trim(),
      shipping_carrier: shippingCarrier,
    });
  };

  const handleLockAll = async () => {
    setLoadingAction('lockAll');
    try {
      await lockOrders(eventFilter || undefined);
      toast({
        title: t('toast.all_orders_locked'),
        description: t('toast.all_orders_locked_desc'),
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onOrderUpdated();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : t('toast.bulk_lock_error');
      toast({
        title: t('toast.error_title'),
        description: message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoadingAction(null);
    }
  };

  const handlePdfDownload = async (docType: 'confirmation' | 'packing_slip' | 'shipping_label') => {
    const actionKey = `pdf_${docType}`;
    setLoadingAction(actionKey);
    try {
      let result;
      if (docType === 'confirmation') {
        result = await downloadOrderPdf(order.order_id);
      } else if (docType === 'packing_slip') {
        result = await downloadPackingSlipPdf(order.order_id);
      } else {
        result = await downloadShippingLabelPdf(order.order_id);
      }

      if (!result.success && result.error) {
        toast({
          title: 'PDF download mislukt',
          description: result.error.message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    } catch {
      toast({
        title: 'PDF download mislukt',
        description: 'Er is een onverwachte fout opgetreden.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <>
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
                  <Badge colorScheme={isEventOrder ? 'purple' : 'blue'}>
                    {isEventOrder ? (order.event_id || 'Event') : 'Webshop'}
                  </Badge>
                </HStack>
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
                {order.delivery_option && (
                  <Text fontSize="sm" mt={1}>
                    <strong>Leveroptie:</strong> {order.delivery_option}
                    {order.delivery_cost ? ` (${formatCurrency(order.delivery_cost)})` : ''}
                  </Text>
                )}
              </Box>

              <Divider borderColor="gray.600" />

              {/* Customer & Shipping Section */}
              <Box>
                <Heading size="xs" mb={3}>Klant & Verzending</Heading>
                <SimpleGrid columns={2} spacing={3}>
                  <Box>
                    <Text fontSize="xs" color="gray.400">Naam</Text>
                    <Text fontSize="sm">{order.customer_name || '—'}</Text>
                  </Box>
                  <Box>
                    <Text fontSize="xs" color="gray.400">E-mail</Text>
                    <Text fontSize="sm">{order.customer_email || '—'}</Text>
                  </Box>
                  {order.customer_phone && (
                    <Box>
                      <Text fontSize="xs" color="gray.400">Telefoon</Text>
                      <Text fontSize="sm">{order.customer_phone}</Text>
                    </Box>
                  )}
                  {order.club_name && (
                    <Box>
                      <Text fontSize="xs" color="gray.400">Club</Text>
                      <Text fontSize="sm">{order.club_name}</Text>
                    </Box>
                  )}
                </SimpleGrid>

                {/* Address — webshop: shipping_address, event: pickup_location */}
                {!isEventOrder && order.shipping_address && (
                  <Box mt={3} p={3} bg="gray.700" borderRadius="md">
                    <Text fontSize="xs" color="orange.300" mb={1}>Afleveradres</Text>
                    {order.shipping_address.naam && (
                      <Text fontSize="sm">{order.shipping_address.naam}</Text>
                    )}
                    <Text fontSize="sm">{order.shipping_address.straat || ''}</Text>
                    <Text fontSize="sm">
                      {order.shipping_address.postcode || ''} {order.shipping_address.woonplaats || ''}
                    </Text>
                    <Text fontSize="sm">{order.shipping_address.land || ''}</Text>
                  </Box>
                )}
                {isEventOrder && order.pickup_location && (
                  <Box mt={3} p={3} bg="gray.700" borderRadius="md">
                    <Text fontSize="xs" color="orange.300" mb={1}>Afhaallocatie</Text>
                    <Text fontSize="sm">{order.pickup_location}</Text>
                  </Box>
                )}
              </Box>

              <Divider borderColor="gray.600" />

              {/* Shipping Info — webshop orders */}
              {!isEventOrder && (order.tracking_number || order.shipping_carrier || order.shipped_at) && (
                <>
                  <Box>
                    <Heading size="xs" mb={3}>Verzendinfo</Heading>
                    <SimpleGrid columns={2} spacing={3}>
                      {order.tracking_number && (
                        <Box>
                          <Text fontSize="xs" color="gray.400">Track & Trace</Text>
                          <Text fontSize="sm" fontFamily="mono">{order.tracking_number}</Text>
                        </Box>
                      )}
                      {order.shipping_carrier && (
                        <Box>
                          <Text fontSize="xs" color="gray.400">Vervoerder</Text>
                          <Text fontSize="sm">{order.shipping_carrier}</Text>
                        </Box>
                      )}
                      {order.shipped_at && (
                        <Box>
                          <Text fontSize="xs" color="gray.400">Verzonden op</Text>
                          <Text fontSize="sm">{formatDate(order.shipped_at)}</Text>
                        </Box>
                      )}
                    </SimpleGrid>
                  </Box>
                  <Divider borderColor="gray.600" />
                </>
              )}

              {/* Pickup Info — event orders */}
              {isEventOrder && (order.picked_up_at || order.picked_up_by) && (
                <>
                  <Box>
                    <Heading size="xs" mb={3}>Afhaalinfo</Heading>
                    <SimpleGrid columns={2} spacing={3}>
                      {order.picked_up_at && (
                        <Box>
                          <Text fontSize="xs" color="gray.400">Afgehaald op</Text>
                          <Text fontSize="sm">{formatDate(order.picked_up_at)}</Text>
                        </Box>
                      )}
                      {order.picked_up_by && (
                        <Box>
                          <Text fontSize="xs" color="gray.400">Uitgereikt door</Text>
                          <Text fontSize="sm">{order.picked_up_by}</Text>
                        </Box>
                      )}
                    </SimpleGrid>
                  </Box>
                  <Divider borderColor="gray.600" />
                </>
              )}

              {/* Action Buttons — Context-aware transitions */}
              <Box>
                <Heading size="xs" mb={2}>Acties</Heading>
                <HStack spacing={2} flexWrap="wrap">
                  {availableTransitions.map((transition) => (
                    <Tooltip
                      key={transition.target}
                      label={canMutate ? `Naar "${transition.label}"` : disabledTooltip}
                      hasArrow
                    >
                      <Button
                        size="sm"
                        colorScheme="orange"
                        variant={availableTransitions.length === 1 ? 'solid' : 'outline'}
                        isLoading={loadingAction === transition.target}
                        isDisabled={!canMutate || loadingAction !== null}
                        onClick={() => handleTransition(transition)}
                      >
                        {transition.label}
                      </Button>
                    </Tooltip>
                  ))}

                  {/* Lock ALL button (always available) */}
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

              {/* Documents placeholder */}
              <Divider borderColor="gray.600" />
              <Box>
                <Heading size="xs" mb={2}>Documenten</Heading>
                <HStack spacing={2} flexWrap="wrap">
                  <Button
                    size="xs"
                    variant="outline"
                    colorScheme="orange"
                    isLoading={loadingAction === 'pdf_confirmation'}
                    onClick={() => handlePdfDownload('confirmation')}
                  >
                    Orderbevestiging
                  </Button>
                  <Button
                    size="xs"
                    variant="outline"
                    colorScheme="orange"
                    isLoading={loadingAction === 'pdf_packing_slip'}
                    onClick={() => handlePdfDownload('packing_slip')}
                  >
                    Pakbon
                  </Button>
                  <Button
                    size="xs"
                    variant="outline"
                    colorScheme="orange"
                    isLoading={loadingAction === 'pdf_shipping_label'}
                    onClick={() => handlePdfDownload('shipping_label')}
                  >
                    Verzendlabel
                  </Button>
                </HStack>
              </Box>
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      {/* Shipping Modal — shown when transitioning to "shipped" */}
      <Modal isOpen={shippingModal.isOpen} onClose={shippingModal.onClose} isCentered>
        <ModalOverlay />
        <ModalContent bg="gray.800">
          <ModalHeader>Verzendgegevens invullen</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel fontSize="sm">Track & Trace nummer</FormLabel>
                <Input
                  value={trackingNumber}
                  onChange={(e) => setTrackingNumber(e.target.value)}
                  placeholder="bijv. 3SHDCN123456789"
                  bg="gray.700"
                  borderColor="gray.600"
                />
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm">Vervoerder</FormLabel>
                <Select
                  value={shippingCarrier}
                  onChange={(e) => setShippingCarrier(e.target.value)}
                  bg="gray.700"
                  borderColor="gray.600"
                >
                  <option value="PostNL">PostNL</option>
                  <option value="DHL">DHL</option>
                  <option value="DPD">DPD</option>
                  <option value="Anders">Anders</option>
                </Select>
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={shippingModal.onClose}>
              Annuleren
            </Button>
            <Button
              colorScheme="orange"
              onClick={handleShippingConfirm}
              isLoading={loadingAction === 'shipped'}
            >
              Markeer als verzonden
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
};

export default OrderDetailDrawer;

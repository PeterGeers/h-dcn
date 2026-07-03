/**
 * MyOrders Component
 *
 * Customer-facing "Mijn bestellingen" view showing all orders
 * belonging to the authenticated user with:
 * - StatusBadge (colored status indicator)
 * - Tracking number display for shipped/delivered orders
 * - Order confirmation PDF download button
 *
 * Requirements: 4.4 (Klant "Mijn bestellingen" verbeteren)
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  VStack,
  Text,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Alert,
  AlertIcon,
  IconButton,
  Tooltip,
  Link,
} from '@chakra-ui/react';
import { DownloadIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { orderService } from '../services/api';
import { StatusBadge } from '../../webshop-management/components/StatusBadge';
import { OrderStatus } from '../../webshop-management/types/admin.types';
import { downloadOrderPdf } from '../services/pdfDownloadService';

interface CustomerOrder {
  order_id: string;
  order_number?: string;
  event_id?: string;
  status: OrderStatus;
  payment_status: string;
  items: Array<{
    name?: string;
    product_id: string;
    quantity: number;
    unit_price: number;
    variant_attributes?: Record<string, string>;
  }>;
  total_amount: number;
  total_paid: number;
  delivery_option?: string;
  delivery_cost?: number;
  tracking_number?: string;
  shipping_carrier?: string;
  shipped_at?: string;
  created_at: string;
  updated_at?: string;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('nl-NL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

function formatCurrency(amount: number): string {
  return `€ ${(Number(amount) || 0).toFixed(2)}`;
}

const MyOrders: React.FC = () => {
  const { t } = useTranslation('webshop');
  const [orders, setOrders] = useState<CustomerOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const loadOrders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await orderService.getMyOrders();
      const data = response?.data || response;
      setOrders(data?.orders || []);
    } catch (err) {
      setError(
        t('my_orders.load_error', {
          defaultValue: 'Fout bij het ophalen van je bestellingen.',
        })
      );
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  const handleDownloadPdf = async (orderId: string) => {
    setDownloadingId(orderId);
    try {
      await downloadOrderPdf(orderId);
    } finally {
      setDownloadingId(null);
    }
  };

  if (loading) {
    return (
      <Box p={6} textAlign="center">
        <Spinner size="lg" color="orange.400" />
        <Text mt={2} color="gray.600">
          {t('my_orders.loading', { defaultValue: 'Bestellingen laden...' })}
        </Text>
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

  if (orders.length === 0) {
    return (
      <Box p={6} textAlign="center">
        <Text color="gray.500">
          {t('my_orders.empty', { defaultValue: 'Je hebt nog geen bestellingen.' })}
        </Text>
      </Box>
    );
  }

  return (
    <Box p={6} bg="white" borderRadius="md" color="black">
      <VStack spacing={4} align="stretch">
        <Text fontSize="xl" fontWeight="bold">
          {t('my_orders.title', { defaultValue: 'Mijn bestellingen' })}
        </Text>

        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th>{t('my_orders.col_order', { defaultValue: 'Bestelling' })}</Th>
                <Th>{t('my_orders.col_date', { defaultValue: 'Datum' })}</Th>
                <Th>{t('my_orders.col_status', { defaultValue: 'Status' })}</Th>
                <Th>{t('my_orders.col_tracking', { defaultValue: 'Tracking' })}</Th>
                <Th isNumeric>{t('my_orders.col_total', { defaultValue: 'Totaal' })}</Th>
                <Th>{t('my_orders.col_actions', { defaultValue: 'Acties' })}</Th>
              </Tr>
            </Thead>
            <Tbody>
              {orders.map((order) => (
                <Tr key={order.order_id}>
                  <Td>
                    <Text fontSize="sm" fontWeight="medium">
                      {order.order_number || order.order_id.slice(0, 12) + '…'}
                    </Text>
                    {order.items.length > 0 && (
                      <Text fontSize="xs" color="gray.500">
                        {order.items.length} {order.items.length === 1 ? 'artikel' : 'artikelen'}
                      </Text>
                    )}
                  </Td>
                  <Td fontSize="xs">{formatDate(order.created_at)}</Td>
                  <Td>
                    <StatusBadge status={order.status} />
                  </Td>
                  <Td>
                    <TrackingInfo order={order} />
                  </Td>
                  <Td isNumeric fontSize="sm">
                    {formatCurrency(order.total_amount)}
                  </Td>
                  <Td>
                    <Tooltip
                      label={t('my_orders.download_pdf', { defaultValue: 'Download orderbevestiging' })}
                    >
                      <IconButton
                        aria-label="Download PDF"
                        icon={<DownloadIcon />}
                        size="sm"
                        variant="ghost"
                        colorScheme="orange"
                        isLoading={downloadingId === order.order_id}
                        onClick={() => handleDownloadPdf(order.order_id)}
                      />
                    </Tooltip>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </VStack>
    </Box>
  );
};

/** Tracking info sub-component — shows tracking number for shipped/delivered orders */
const TrackingInfo: React.FC<{ order: CustomerOrder }> = ({ order }) => {
  const showTracking =
    order.tracking_number &&
    ['shipped', 'delivered', 'completed'].includes(order.status);

  if (!showTracking) {
    return <Text fontSize="xs" color="gray.400">—</Text>;
  }

  const carrier = order.shipping_carrier || '';
  const trackingUrl = getTrackingUrl(carrier, order.tracking_number!);

  return (
    <VStack align="start" spacing={0}>
      {carrier && (
        <Text fontSize="xs" color="gray.500">{carrier}</Text>
      )}
      {trackingUrl ? (
        <Link href={trackingUrl} isExternal fontSize="xs" color="blue.500">
          {order.tracking_number} <ExternalLinkIcon mx="2px" />
        </Link>
      ) : (
        <Text fontSize="xs">{order.tracking_number}</Text>
      )}
    </VStack>
  );
};

/** Generate tracking URL based on carrier */
function getTrackingUrl(carrier: string, trackingNumber: string): string | null {
  const c = carrier.toLowerCase();
  if (c.includes('postnl')) {
    return `https://postnl.nl/tracktrace/?B=${encodeURIComponent(trackingNumber)}`;
  }
  if (c.includes('dhl')) {
    return `https://www.dhl.com/nl-nl/home/tracking.html?tracking-id=${encodeURIComponent(trackingNumber)}`;
  }
  if (c.includes('dpd')) {
    return `https://tracking.dpd.de/status/nl_NL/parcel/${encodeURIComponent(trackingNumber)}`;
  }
  return null;
}

export default MyOrders;

/**
 * OrdersTab Component
 *
 * Displays all orders in a filterable, sortable table using the Table Filter Framework.
 * Uses useFilterableTable hook with FilterPanel + GenericFilter dropdowns for:
 *   - Order status (all fulfilment statuses)
 *   - Payment status (unpaid, partial, paid)
 *   - Source (Webshop / per event)
 * FilterableHeader on all columns for inline text filtering + sort.
 *
 * Clickable rows open the OrderDetailDrawer for full order details
 * and state transition controls.
 *
 * Validates: Requirements 4.3, 4.4, 4.5, 4.6, 4.11, 4.12, 5.1, 7.1, 12.6
 */

import React, { useState, useMemo } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Td,
  Badge,
  Text,
  Spinner,
  Alert,
  AlertIcon,
  useDisclosure,
  Button,
} from '@chakra-ui/react';
import { useAdminOrders } from '../hooks/useAdminOrders';
import { StatusBadge } from './StatusBadge';
import { OrderDetailDrawer } from './OrderDetailDrawer';
import { EventPickList } from './EventPickList';
import { AdminOrder } from '../types/admin.types';
import { FilterPanel, FilterableHeader } from '../../../components/filters';
import { useFilterableTable } from '../../../hooks/useFilterableTable';

export interface OrdersTabProps {
  /** Active event filter value (empty string = all, "webshop" = no event) */
  eventFilter?: string;
}

const PAYMENT_STATUS_COLOR: Record<string, string> = {
  paid: 'green',
  partial: 'yellow',
  unpaid: 'red',
  pending: 'orange',
  awaiting_payment: 'orange',
};

/** Column filter keys for text-based filtering */
interface ColumnFilters {
  [key: string]: string;
  order_id: string;
  customer_name: string;
  status: string;
  payment_status: string;
  source: string;
  total_amount: string;
  created_at: string;
}

const INITIAL_COLUMN_FILTERS: ColumnFilters = {
  order_id: '',
  customer_name: '',
  status: '',
  payment_status: '',
  source: '',
  total_amount: '',
  created_at: '',
};

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

export const OrdersTab: React.FC<OrdersTabProps> = ({ eventFilter = '' }) => {
  const { orders, loading, error, refetch } = useAdminOrders(eventFilter);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedOrder, setSelectedOrder] = useState<AdminOrder | null>(null);

  // Pick-list mode state
  const [showPickList, setShowPickList] = useState(false);

  // Add a source display field to each order for column filtering
  const ordersWithSource = useMemo(() => {
    return orders.map(o => ({
      ...o,
      source: o.event_id || 'webshop',
    }));
  }, [orders]);

  // Table filter framework: column text filters + sort
  const {
    filters,
    setFilter,
    resetFilters,
    hasActiveFilters,
    sortField,
    sortDirection,
    handleSort,
    processedData,
    filteredCount,
  } = useFilterableTable(ordersWithSource as unknown as Record<string, unknown>[], {
    initialFilters: INITIAL_COLUMN_FILTERS,
    defaultSort: { field: 'created_at', direction: 'desc' },
  });

  // Determine if current source filter selects a specific event (for pick-list)
  const selectedEventId = useMemo(() => {
    const sourceFilter = filters.source.trim();
    if (!sourceFilter || sourceFilter === 'webshop') return null;
    // Check if the filter value matches an event_id exactly
    const matchingEvent = orders.find(o => o.event_id === sourceFilter);
    return matchingEvent ? sourceFilter : null;
  }, [filters.source, orders]);

  const handleResetAll = () => {
    resetFilters();
    setShowPickList(false);
  };

  const handleRowClick = (order: AdminOrder) => {
    setSelectedOrder(order);
    onOpen();
  };

  const handleDrawerClose = () => {
    setSelectedOrder(null);
    onClose();
  };

  const handleOrderUpdated = () => {
    refetch();
  };

  if (loading) {
    return (
      <Box p={8} textAlign="center">
        <Spinner size="lg" color="orange.400" />
        <Text mt={2} color="gray.400">Bestellingen laden...</Text>
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
      <Box p={8} textAlign="center">
        <Text color="gray.400">Geen bestellingen gevonden.</Text>
      </Box>
    );
  }

  return (
    <Box>
      {/* Filter panel with reset + pick-list button */}
      <FilterPanel
        hasActiveFilters={hasActiveFilters}
        onReset={handleResetAll}
        filteredCount={filteredCount}
        totalCount={orders.length}
      >
        {selectedEventId && (
          <Button
            size="sm"
            colorScheme={showPickList ? 'orange' : 'gray'}
            variant={showPickList ? 'solid' : 'outline'}
            onClick={() => setShowPickList(!showPickList)}
            alignSelf="flex-end"
          >
            Pick-list
          </Button>
        )}
      </FilterPanel>

      {/* Pick-list mode OR regular table */}
      {showPickList && selectedEventId ? (
        <EventPickList eventId={selectedEventId} />
      ) : (
      <Box overflowX="auto">
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              <FilterableHeader
                label="Order ID"
                filterValue={filters.order_id}
                onFilterChange={(v) => setFilter('order_id', v)}
                sortable
                sortDirection={sortField === 'order_id' ? sortDirection : null}
                onSort={() => handleSort('order_id')}
                minW="120px"
              />
              <FilterableHeader
                label="Klant / Club"
                filterValue={filters.customer_name}
                onFilterChange={(v) => setFilter('customer_name', v)}
                sortable
                sortDirection={sortField === 'customer_name' ? sortDirection : null}
                onSort={() => handleSort('customer_name')}
                minW="150px"
              />
              <FilterableHeader
                label="Status"
                filterValue={filters.status}
                onFilterChange={(v) => setFilter('status', v)}
                sortable
                sortDirection={sortField === 'status' ? sortDirection : null}
                onSort={() => handleSort('status')}
                minW="120px"
              />
              <FilterableHeader
                label="Betaling"
                filterValue={filters.payment_status}
                onFilterChange={(v) => setFilter('payment_status', v)}
                sortable
                sortDirection={sortField === 'payment_status' ? sortDirection : null}
                onSort={() => handleSort('payment_status')}
                minW="100px"
              />
              <FilterableHeader
                label="Bron"
                filterValue={filters.source}
                onFilterChange={(v) => setFilter('source', v)}
                sortable
                sortDirection={sortField === 'source' ? sortDirection : null}
                onSort={() => handleSort('source')}
                minW="100px"
              />
              <FilterableHeader
                label="Totaal"
                filterValue={filters.total_amount}
                onFilterChange={(v) => setFilter('total_amount', v)}
                sortable
                sortDirection={sortField === 'total_amount' ? sortDirection : null}
                onSort={() => handleSort('total_amount')}
                minW="90px"
              />
              <FilterableHeader
                label="Aangemaakt"
                filterValue={filters.created_at}
                onFilterChange={(v) => setFilter('created_at', v)}
                sortable
                sortDirection={sortField === 'created_at' ? sortDirection : null}
                onSort={() => handleSort('created_at')}
                minW="100px"
              />
            </Tr>
          </Thead>
          <Tbody>
            {(processedData as unknown as AdminOrder[]).map((order) => (
              <Tr
                key={order.order_id}
                cursor="pointer"
                _hover={{ bg: 'gray.700' }}
                onClick={() => handleRowClick(order)}
              >
                <Td>
                  <Text fontSize="xs" fontFamily="mono">
                    {order.order_id.slice(0, 12)}…
                  </Text>
                </Td>
                <Td>
                  <Text fontSize="sm">{order.customer_name}</Text>
                  {order.club_name && (
                    <Text fontSize="xs" color="gray.400">
                      {order.club_name}
                    </Text>
                  )}
                </Td>
                <Td>
                  <StatusBadge status={order.status} />
                </Td>
                <Td>
                  <Badge
                    colorScheme={PAYMENT_STATUS_COLOR[order.payment_status] || 'gray'}
                    fontSize="xs"
                  >
                    {order.payment_status}
                  </Badge>
                </Td>
                <Td>
                  <Text fontSize="xs" color="gray.400">
                    {order.event_id ? order.event_id.slice(0, 8) : 'webshop'}
                  </Text>
                </Td>
                <Td fontSize="sm">{formatCurrency(order.total_amount)}</Td>
                <Td fontSize="xs">{formatDate(order.created_at)}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>
      )}

      {selectedOrder && (
        <OrderDetailDrawer
          order={selectedOrder}
          isOpen={isOpen}
          onClose={handleDrawerClose}
          onOrderUpdated={handleOrderUpdated}
          eventFilter={eventFilter}
        />
      )}
    </Box>
  );
};

export default OrdersTab;

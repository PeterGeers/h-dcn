import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Button,
  HStack,
  VStack,
  Text,
  Heading,
  Spinner,
  Select,
  AlertDialog,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogBody,
  AlertDialogFooter,
  useDisclosure,
  useToast,
  Alert,
  AlertIcon,
  IconButton,
  Tooltip,
} from '@chakra-ui/react';
import { LockIcon, UnlockIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { getAuthHeaders } from '../../../utils/authHeaders';
import { OrderStatus } from '../types/presmeet.types';

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

// --- Types ---

interface OrderSummary {
  order_id: string;
  club_id: string;
  club_name?: string;
  status: OrderStatus;
  payment_status?: string;
  total_amount?: number;
  delegate_email?: string;
  updated_at?: string;
}

interface LockUnlockResult {
  locked_count?: number;
  locked_order_ids?: string[];
  unlocked_count?: number;
  unlocked_order_ids?: string[];
  skipped_count?: number;
  failed_order_ids?: string[];
  failed_count?: number;
  message: string;
}

interface AdminOrderLockUnlockProps {
  eventId: string;
}

// --- API helpers ---

async function fetchOrdersForEvent(eventId: string): Promise<OrderSummary[]> {
  const headers = await getAuthHeaders();
  const response = await axios.get<{ data: Record<string, any>[] }>(
    `${BASE_URL}/admin/reports/overview`,
    {
      params: { source_id: eventId },
      headers,
    }
  );
  // Map report rows to OrderSummary
  const data = response.data?.data || response.data || [];
  const rows = Array.isArray(data) ? data : [];
  return rows.map((row: Record<string, any>) => ({
    order_id: row.order_id || '',
    club_id: row.club_id || '',
    club_name: row.club || row.club_name || row.club_id || '',
    status: row.status || 'draft',
    payment_status: row.payment_status || 'unpaid',
    total_amount: row.total_amount ?? 0,
    delegate_email: row.delegate_email || row.email || '',
    updated_at: row.updated_at || '',
  }));
}

async function batchLockOrders(sourceId: string): Promise<LockUnlockResult> {
  const headers = await getAuthHeaders();
  const response = await axios.post<LockUnlockResult>(
    `${BASE_URL}/admin/booking/lock`,
    { source_id: sourceId },
    { headers }
  );
  return response.data;
}

async function batchUnlockOrders(sourceId: string): Promise<LockUnlockResult> {
  const headers = await getAuthHeaders();
  const response = await axios.post<LockUnlockResult>(
    `${BASE_URL}/admin/booking/unlock`,
    { source_id: sourceId },
    { headers }
  );
  return response.data;
}

async function unlockSingleOrder(orderId: string): Promise<LockUnlockResult> {
  const headers = await getAuthHeaders();
  const response = await axios.post<LockUnlockResult>(
    `${BASE_URL}/admin/booking/${encodeURIComponent(orderId)}/unlock`,
    {},
    { headers }
  );
  return response.data;
}

// --- Status Badge ---

function OrderStatusBadge({ status }: { status: string }) {
  const colorScheme =
    status === 'locked'
      ? 'green'
      : status === 'submitted'
      ? 'blue'
      : status === 'draft'
      ? 'orange'
      : 'gray';
  return <Badge colorScheme={colorScheme}>{status}</Badge>;
}

// --- Main Component ---

/**
 * Admin Order Lock/Unlock UI — allows admins to lock/unlock individual orders
 * and perform batch lock/unlock operations.
 *
 * Requirements: 10.1, 10.3, 10.4, 10.5
 */
const AdminOrderLockUnlock: React.FC<AdminOrderLockUnlockProps> = ({ eventId }) => {
  const { t } = useTranslation('eventBooking');
  const toast = useToast();

  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Confirmation dialog state
  const { isOpen: isLockOpen, onOpen: onLockOpen, onClose: onLockClose } = useDisclosure();
  const { isOpen: isUnlockOpen, onOpen: onUnlockOpen, onClose: onUnlockClose } = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Load orders
  const loadOrders = useCallback(async () => {
    if (!eventId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchOrdersForEvent(eventId);
      setOrders(result);
    } catch (err) {
      setError(t('admin.lock_unlock.load_failed'));
    } finally {
      setLoading(false);
    }
  }, [eventId, t]);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  // Filter orders by status
  const filteredOrders = statusFilter === 'all'
    ? orders
    : orders.filter((o) => o.status === statusFilter);

  // Counts for UI
  const submittedCount = orders.filter((o) => o.status === 'submitted').length;
  const unlockableCount = orders.filter((o) => o.status === 'submitted' || o.status === 'locked').length;

  // --- Batch Lock ---
  const handleBatchLock = async () => {
    onLockClose();
    setActionLoading(true);
    try {
      const result = await batchLockOrders(eventId);
      toast({
        title: t('admin.lock_unlock.lock_success'),
        description: t('admin.lock_unlock.lock_success_desc', {
          count: result.locked_count ?? 0,
        }),
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      await loadOrders();
    } catch (err: any) {
      const message = err?.response?.data?.error || err?.response?.data?.message || t('admin.lock_unlock.lock_failed');
      toast({
        title: t('admin.lock_unlock.lock_failed'),
        description: message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setActionLoading(false);
    }
  };

  // --- Batch Unlock ---
  const handleBatchUnlock = async () => {
    onUnlockClose();
    setActionLoading(true);
    try {
      const result = await batchUnlockOrders(eventId);
      toast({
        title: t('admin.lock_unlock.unlock_success'),
        description: t('admin.lock_unlock.unlock_success_desc', {
          count: result.unlocked_count ?? 0,
        }),
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      await loadOrders();
    } catch (err: any) {
      const message = err?.response?.data?.error || err?.response?.data?.message || t('admin.lock_unlock.unlock_failed');
      toast({
        title: t('admin.lock_unlock.unlock_failed'),
        description: message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setActionLoading(false);
    }
  };

  // --- Single Order Unlock ---
  const handleSingleUnlock = async (orderId: string) => {
    setActionLoading(true);
    try {
      await unlockSingleOrder(orderId);
      toast({
        title: t('admin.lock_unlock.unlock_success'),
        description: t('admin.lock_unlock.single_unlock_desc'),
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      await loadOrders();
    } catch (err: any) {
      const status = err?.response?.status;
      const message = err?.response?.data?.error || err?.response?.data?.message || '';

      if (status === 400) {
        // Req 10.4: reject lock/unlock on non-qualifying status
        toast({
          title: t('admin.lock_unlock.cannot_unlock'),
          description: message || t('admin.lock_unlock.invalid_status'),
          status: 'warning',
          duration: 5000,
          isClosable: true,
        });
      } else {
        toast({
          title: t('admin.lock_unlock.unlock_failed'),
          description: message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <Box textAlign="center" py={8}>
        <Spinner size="lg" />
        <Text mt={2}>{t('admin.lock_unlock.loading')}</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={5} align="stretch">
      <Heading size="md">{t('admin.lock_unlock.title')}</Heading>

      {error && (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          {error}
        </Alert>
      )}

      {/* Batch Actions */}
      <Box bg="white" p={4} borderRadius="md" borderWidth={1}>
        <HStack spacing={4} flexWrap="wrap" justify="space-between">
          <HStack spacing={4}>
            <Button
              leftIcon={<LockIcon />}
              colorScheme="red"
              size="sm"
              onClick={onLockOpen}
              isDisabled={submittedCount === 0 || actionLoading}
              isLoading={actionLoading}
            >
              {t('admin.lock_unlock.lock_all')} ({submittedCount})
            </Button>
            <Button
              leftIcon={<UnlockIcon />}
              colorScheme="blue"
              size="sm"
              onClick={onUnlockOpen}
              isDisabled={unlockableCount === 0 || actionLoading}
              isLoading={actionLoading}
            >
              {t('admin.lock_unlock.unlock_all')} ({unlockableCount})
            </Button>
          </HStack>

          <HStack spacing={3}>
            <Text fontSize="sm" fontWeight="medium">
              {t('reports.order_status')}:
            </Text>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              size="sm"
              maxW="160px"
            >
              <option value="all">{t('reports.filter_all_statuses')}</option>
              <option value="draft">{t('reports.filter_draft')}</option>
              <option value="submitted">{t('reports.filter_submitted')}</option>
              <option value="locked">{t('reports.filter_locked')}</option>
            </Select>
            <Button size="sm" variant="ghost" onClick={loadOrders}>
              {t('admin.claims.refresh')}
            </Button>
          </HStack>
        </HStack>
      </Box>

      {/* Orders Table */}
      <Box bg="white" p={4} borderRadius="md" borderWidth={1} overflowX="auto">
        {filteredOrders.length === 0 ? (
          <Text color="gray.500" textAlign="center" py={6}>
            {t('admin.lock_unlock.no_orders')}
          </Text>
        ) : (
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th>{t('admin.lock_unlock.col_club')}</Th>
                <Th>{t('admin.lock_unlock.col_delegate')}</Th>
                <Th>{t('admin.lock_unlock.col_status')}</Th>
                <Th>{t('admin.lock_unlock.col_payment')}</Th>
                <Th>{t('admin.lock_unlock.col_actions')}</Th>
              </Tr>
            </Thead>
            <Tbody>
              {filteredOrders.map((order) => (
                <Tr key={order.order_id}>
                  <Td>
                    <Text fontSize="sm" fontWeight="medium">
                      {order.club_name || order.club_id}
                    </Text>
                  </Td>
                  <Td>
                    <Text fontSize="sm">{order.delegate_email || '—'}</Text>
                  </Td>
                  <Td>
                    <OrderStatusBadge status={order.status} />
                  </Td>
                  <Td>
                    <Badge
                      colorScheme={
                        order.payment_status === 'paid'
                          ? 'green'
                          : order.payment_status === 'partial'
                          ? 'yellow'
                          : 'gray'
                      }
                    >
                      {order.payment_status || 'unpaid'}
                    </Badge>
                  </Td>
                  <Td>
                    {(order.status === 'submitted' || order.status === 'locked') && (
                      <Tooltip label={t('admin.lock_unlock.unlock_order')}>
                        <IconButton
                          aria-label={t('admin.lock_unlock.unlock_order')}
                          icon={<UnlockIcon />}
                          size="xs"
                          colorScheme="blue"
                          variant="ghost"
                          onClick={() => handleSingleUnlock(order.order_id)}
                          isDisabled={actionLoading}
                        />
                      </Tooltip>
                    )}
                    {order.status === 'draft' && (
                      <Tooltip label={t('admin.lock_unlock.cannot_lock_draft')}>
                        <IconButton
                          aria-label={t('admin.lock_unlock.cannot_lock_draft')}
                          icon={<LockIcon />}
                          size="xs"
                          variant="ghost"
                          isDisabled
                          opacity={0.4}
                        />
                      </Tooltip>
                    )}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}

        {filteredOrders.length > 0 && (
          <Text fontSize="xs" color="gray.500" mt={3}>
            {filteredOrders.length} {filteredOrders.length === 1 ? 'order' : 'orders'}
          </Text>
        )}
      </Box>

      {/* Lock All Confirmation Dialog */}
      <AlertDialog
        isOpen={isLockOpen}
        leastDestructiveRef={cancelRef as React.RefObject<HTMLButtonElement>}
        onClose={onLockClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              {t('admin.lock_unlock.lock_confirm_title')}
            </AlertDialogHeader>
            <AlertDialogBody>
              {t('admin.lock_unlock.lock_confirm_body', { count: submittedCount })}
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onLockClose}>
                {t('admin.claims.cancel')}
              </Button>
              <Button colorScheme="red" onClick={handleBatchLock} ml={3}>
                {t('admin.lock_unlock.lock_confirm')}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>

      {/* Unlock All Confirmation Dialog */}
      <AlertDialog
        isOpen={isUnlockOpen}
        leastDestructiveRef={cancelRef as React.RefObject<HTMLButtonElement>}
        onClose={onUnlockClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              {t('admin.lock_unlock.unlock_confirm_title')}
            </AlertDialogHeader>
            <AlertDialogBody>
              {t('admin.lock_unlock.unlock_confirm_body', { count: unlockableCount })}
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onUnlockClose}>
                {t('admin.claims.cancel')}
              </Button>
              <Button colorScheme="blue" onClick={handleBatchUnlock} ml={3}>
                {t('admin.lock_unlock.unlock_confirm')}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </VStack>
  );
};

export default AdminOrderLockUnlock;

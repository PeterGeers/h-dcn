import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  VStack,
  HStack,
  Text,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Stat,
  StatLabel,
  StatNumber,
  StatGroup,
  useToast,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Heading,
  Tooltip,
} from '@chakra-ui/react';
import { presmeetService } from '../services/presmeetApi';
import {
  ReportOverview,
  ReportOrderEntry,
  OrderStatus,
  ProductType,
} from '../types/presmeet';

interface AdminDashboardProps {
  isAdmin: boolean;
}

const STATUS_COLORS: Record<OrderStatus, string> = {
  draft: 'gray',
  submitted: 'blue',
  locked: 'green',
};

const PRODUCT_TYPE_LABELS: Record<ProductType, string> = {
  meeting_ticket: 'Meeting Ticket',
  party_ticket: 'Party Ticket',
  tshirt: 'T-Shirt',
  airport_transfer: 'Airport Transfer',
};

const AdminDashboard: React.FC<AdminDashboardProps> = ({ isAdmin }) => {
  const [overview, setOverview] = useState<ReportOverview | null>(null);
  const [orders, setOrders] = useState<ReportOrderEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [lockingAll, setLockingAll] = useState(false);
  const [lockingOrderId, setLockingOrderId] = useState<string | null>(null);
  const [downloadingCsv, setDownloadingCsv] = useState<string | null>(null);
  const toast = useToast();

  // Manual payment modal
  const { isOpen: isPaymentOpen, onOpen: onPaymentOpen, onClose: onPaymentClose } = useDisclosure();
  const [paymentOrderId, setPaymentOrderId] = useState('');
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentDate, setPaymentDate] = useState('');
  const [paymentDescription, setPaymentDescription] = useState('');
  const [submittingPayment, setSubmittingPayment] = useState(false);

  // Access control: return 403 for non-admin users
  if (!isAdmin) {
    return (
      <Alert status="error" variant="subtle" borderRadius="md">
        <AlertIcon />
        <Box>
          <AlertTitle>Access Denied</AlertTitle>
          <AlertDescription>
            Admin access required. You do not have permission to view this page.
          </AlertDescription>
        </Box>
      </Alert>
    );
  }

  const loadReportData = useCallback(async () => {
    setLoading(true);
    try {
      const [overviewRes, ordersRes] = await Promise.all([
        presmeetService.getReport('overview'),
        presmeetService.getReport('orders'),
      ]);

      if (overviewRes.success && overviewRes.data) {
        setOverview(overviewRes.data as ReportOverview);
      }

      if (ordersRes.success && ordersRes.data) {
        const ordersData = ordersRes.data as { generated_at: string; orders: ReportOrderEntry[] };
        // Sort by club name ascending
        const sorted = [...ordersData.orders].sort((a, b) =>
          a.club_name.localeCompare(b.club_name)
        );
        setOrders(sorted);
      }
    } catch (error) {
      toast({
        title: 'Failed to load report data',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadReportData();
  }, [loadReportData]);

  const handleRefreshData = async () => {
    setRefreshing(true);
    try {
      const result = await presmeetService.generateReport();
      if (result.success) {
        toast({
          title: 'Report generated successfully',
          status: 'success',
          duration: 3000,
        });
        await loadReportData();
      } else {
        toast({
          title: 'Failed to generate report',
          description: result.error,
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error) {
      toast({
        title: 'Failed to generate report',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setRefreshing(false);
    }
  };

  const handleLockAll = async () => {
    setLockingAll(true);
    try {
      const result = await presmeetService.lockOrders();
      if (result.success) {
        toast({
          title: 'All submitted orders locked',
          status: 'success',
          duration: 3000,
        });
        await loadReportData();
      } else {
        toast({
          title: 'Failed to lock orders',
          description: result.error,
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error) {
      toast({
        title: 'Failed to lock orders',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLockingAll(false);
    }
  };

  const handleLockOrder = async (orderId: string) => {
    setLockingOrderId(orderId);
    try {
      const result = await presmeetService.lockOrders([orderId]);
      if (result.success) {
        toast({ title: 'Order locked', status: 'success', duration: 2000 });
        await loadReportData();
      } else {
        toast({
          title: 'Failed to lock order',
          description: result.error,
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error) {
      toast({ title: 'Failed to lock order', status: 'error', duration: 5000 });
    } finally {
      setLockingOrderId(null);
    }
  };

  const handleUnlockOrder = async (orderId: string) => {
    setLockingOrderId(orderId);
    try {
      const result = await presmeetService.unlockOrder(orderId);
      if (result.success) {
        toast({ title: 'Order unlocked', status: 'success', duration: 2000 });
        await loadReportData();
      } else {
        toast({
          title: 'Failed to unlock order',
          description: result.error,
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error) {
      toast({ title: 'Failed to unlock order', status: 'error', duration: 5000 });
    } finally {
      setLockingOrderId(null);
    }
  };

  const handleCsvDownload = async (type: 'export_submitted' | 'export_all') => {
    setDownloadingCsv(type);
    try {
      const result = await presmeetService.getReportCsv(type);
      if (result.success && result.data) {
        const blob = new Blob([result.data], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = type === 'export_submitted'
          ? 'presmeet_submitted_orders.csv'
          : 'presmeet_all_orders.csv';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } else {
        toast({
          title: 'Failed to download CSV',
          description: result.error,
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error) {
      toast({ title: 'Failed to download CSV', status: 'error', duration: 5000 });
    } finally {
      setDownloadingCsv(null);
    }
  };

  const handleRecordPayment = async () => {
    if (!paymentOrderId || !paymentAmount || !paymentDate) {
      toast({ title: 'Please fill in all required fields', status: 'warning', duration: 3000 });
      return;
    }

    const amount = parseFloat(paymentAmount);
    if (isNaN(amount) || amount <= 0) {
      toast({ title: 'Invalid amount', status: 'warning', duration: 3000 });
      return;
    }

    setSubmittingPayment(true);
    try {
      const result = await presmeetService.recordPayment({
        order_id: paymentOrderId,
        amount,
        date: paymentDate,
        description: paymentDescription,
      });
      if (result.success) {
        toast({ title: 'Payment recorded', status: 'success', duration: 3000 });
        onPaymentClose();
        resetPaymentForm();
        await loadReportData();
      } else {
        toast({
          title: 'Failed to record payment',
          description: result.error,
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error) {
      toast({ title: 'Failed to record payment', status: 'error', duration: 5000 });
    } finally {
      setSubmittingPayment(false);
    }
  };

  const resetPaymentForm = () => {
    setPaymentOrderId('');
    setPaymentAmount('');
    setPaymentDate('');
    setPaymentDescription('');
  };

  const openPaymentModal = (orderId?: string) => {
    if (orderId) setPaymentOrderId(orderId);
    onPaymentOpen();
  };

  if (loading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
        <Text mt={4}>Loading report data...</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      {/* Header with actions */}
      <HStack justify="space-between" wrap="wrap" gap={2}>
        <Heading size="lg">PresMeet Admin Dashboard</Heading>
        <HStack spacing={3}>
          <Button
            colorScheme="blue"
            onClick={handleRefreshData}
            isLoading={refreshing}
            loadingText="Generating..."
          >
            Refresh Data
          </Button>
          <Button
            colorScheme="red"
            onClick={handleLockAll}
            isLoading={lockingAll}
            loadingText="Locking..."
          >
            Lock ALL
          </Button>
        </HStack>
      </HStack>

      {/* Payment Statistics */}
      {overview && (
        <Box bg="white" p={5} borderRadius="md" borderWidth={1}>
          <Heading size="md" mb={4}>Payment Statistics</Heading>
          <StatGroup>
            <Stat>
              <StatLabel>Total Charged</StatLabel>
              <StatNumber>€{overview.payments.total_charged.toFixed(2)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Total Paid</StatLabel>
              <StatNumber color="green.600">
                €{overview.payments.total_paid.toFixed(2)}
              </StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Outstanding</StatLabel>
              <StatNumber color="red.600">
                €{overview.payments.total_outstanding.toFixed(2)}
              </StatNumber>
            </Stat>
          </StatGroup>
        </Box>
      )}

      {/* Aggregated Stats per Product Type */}
      {overview && (
        <Box bg="white" p={5} borderRadius="md" borderWidth={1}>
          <Heading size="md" mb={4}>
            Product Overview (Total Orders: {overview.summary.total_orders})
          </Heading>
          <Table size="sm" variant="simple">
            <Thead>
              <Tr>
                <Th>Product Type</Th>
                <Th isNumeric>Draft</Th>
                <Th isNumeric>Submitted</Th>
                <Th isNumeric>Locked</Th>
                <Th isNumeric>Total</Th>
              </Tr>
            </Thead>
            <Tbody>
              {(Object.entries(overview.summary.by_product_type) as [ProductType, Record<OrderStatus, number>][]).map(
                ([type, counts]) => (
                  <Tr key={type}>
                    <Td>{PRODUCT_TYPE_LABELS[type] || type}</Td>
                    <Td isNumeric>{counts.draft || 0}</Td>
                    <Td isNumeric>{counts.submitted || 0}</Td>
                    <Td isNumeric>{counts.locked || 0}</Td>
                    <Td isNumeric fontWeight="bold">
                      {(counts.draft || 0) + (counts.submitted || 0) + (counts.locked || 0)}
                    </Td>
                  </Tr>
                )
              )}
            </Tbody>
          </Table>
        </Box>
      )}

      {/* CSV Export Buttons */}
      <Box bg="white" p={5} borderRadius="md" borderWidth={1}>
        <Heading size="md" mb={4}>Export</Heading>
        <HStack spacing={3}>
          <Button
            colorScheme="teal"
            variant="outline"
            onClick={() => handleCsvDownload('export_submitted')}
            isLoading={downloadingCsv === 'export_submitted'}
            loadingText="Downloading..."
          >
            Download CSV (Submitted Only)
          </Button>
          <Button
            colorScheme="teal"
            variant="outline"
            onClick={() => handleCsvDownload('export_all')}
            isLoading={downloadingCsv === 'export_all'}
            loadingText="Downloading..."
          >
            Download CSV (All Orders)
          </Button>
        </HStack>
      </Box>

      {/* Manual Payment Button */}
      <Box bg="white" p={5} borderRadius="md" borderWidth={1}>
        <HStack justify="space-between">
          <Heading size="md">Manual Payment</Heading>
          <Button colorScheme="purple" onClick={() => openPaymentModal()}>
            Record Payment
          </Button>
        </HStack>
      </Box>

      {/* Order List */}
      <Box bg="white" p={5} borderRadius="md" borderWidth={1} overflowX="auto">
        <Heading size="md" mb={4}>Orders ({orders.length})</Heading>
        {orders.length === 0 ? (
          <Text color="gray.500">No orders found. Click "Refresh Data" to generate report.</Text>
        ) : (
          <Table size="sm" variant="simple">
            <Thead>
              <Tr>
                <Th>Club</Th>
                <Th>Status</Th>
                <Th>Payment</Th>
                <Th isNumeric>Total</Th>
                <Th isNumeric>Paid</Th>
                <Th isNumeric>Outstanding</Th>
                <Th>Created</Th>
                <Th>Submitted</Th>
                <Th>Actions</Th>
              </Tr>
            </Thead>
            <Tbody>
              {orders.map((order) => (
                <Tr key={order.order_id}>
                  <Td fontWeight="medium">{order.club_name}</Td>
                  <Td>
                    <Badge colorScheme={STATUS_COLORS[order.status]}>
                      {order.status}
                    </Badge>
                  </Td>
                  <Td>
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
                  </Td>
                  <Td isNumeric>€{order.total_amount.toFixed(2)}</Td>
                  <Td isNumeric>€{order.total_paid.toFixed(2)}</Td>
                  <Td isNumeric>€{order.outstanding.toFixed(2)}</Td>
                  <Td>{new Date(order.created_at).toLocaleDateString()}</Td>
                  <Td>
                    {order.submitted_at
                      ? new Date(order.submitted_at).toLocaleDateString()
                      : '-'}
                  </Td>
                  <Td>
                    <HStack spacing={1}>
                      {order.status === 'submitted' && (
                        <Tooltip label="Lock order">
                          <Button
                            size="xs"
                            colorScheme="orange"
                            onClick={() => handleLockOrder(order.order_id)}
                            isLoading={lockingOrderId === order.order_id}
                          >
                            Lock
                          </Button>
                        </Tooltip>
                      )}
                      {order.status === 'locked' && (
                        <Tooltip label="Unlock order">
                          <Button
                            size="xs"
                            colorScheme="gray"
                            onClick={() => handleUnlockOrder(order.order_id)}
                            isLoading={lockingOrderId === order.order_id}
                          >
                            Unlock
                          </Button>
                        </Tooltip>
                      )}
                      <Tooltip label="Record payment">
                        <Button
                          size="xs"
                          colorScheme="purple"
                          variant="outline"
                          onClick={() => openPaymentModal(order.order_id)}
                        >
                          Pay
                        </Button>
                      </Tooltip>
                    </HStack>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Box>

      {/* Report metadata */}
      {overview && (
        <Text fontSize="sm" color="gray.500" textAlign="right">
          Report generated: {new Date(overview.generated_at).toLocaleString()} by{' '}
          {overview.generated_by}
        </Text>
      )}

      {/* Manual Payment Modal */}
      <Modal isOpen={isPaymentOpen} onClose={onPaymentClose} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Record Manual Payment</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Order ID</FormLabel>
                <Input
                  value={paymentOrderId}
                  onChange={(e) => setPaymentOrderId(e.target.value)}
                  placeholder="Enter order ID"
                />
              </FormControl>
              <FormControl isRequired>
                <FormLabel>Amount (€)</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={paymentAmount}
                  onChange={(e) => setPaymentAmount(e.target.value)}
                  placeholder="0.00"
                />
              </FormControl>
              <FormControl isRequired>
                <FormLabel>Date</FormLabel>
                <Input
                  type="date"
                  value={paymentDate}
                  onChange={(e) => setPaymentDate(e.target.value)}
                />
              </FormControl>
              <FormControl>
                <FormLabel>Description</FormLabel>
                <Textarea
                  value={paymentDescription}
                  onChange={(e) => setPaymentDescription(e.target.value)}
                  placeholder="Payment description (optional)"
                  maxLength={255}
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onPaymentClose}>
              Cancel
            </Button>
            <Button
              colorScheme="purple"
              onClick={handleRecordPayment}
              isLoading={submittingPayment}
              loadingText="Recording..."
            >
              Record Payment
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </VStack>
  );
};

export default AdminDashboard;

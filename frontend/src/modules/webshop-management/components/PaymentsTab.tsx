/**
 * PaymentsTab — Displays payment aggregates and filterable order payment list.
 *
 * Top section: Aggregate stats cards (Total Charged, Total Paid, Total Outstanding)
 * Bottom section: Filterable/sortable table using Table Filter Framework.
 * Click on row → opens PaymentDetailModal for viewing/recording payments.
 *
 * Validates: Requirements 5.1, 5.2
 */

import React, { useState, useMemo } from 'react';
import {
  Box,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
  Table,
  Thead,
  Tbody,
  Tr,
  Td,
  Badge,
  Spinner,
  Alert,
  AlertIcon,
  Text,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  Divider,
  VStack,
} from '@chakra-ui/react';
import { useAdminPayments, OrderPaymentSummary } from '../hooks/useAdminPayments';
import { PaymentRecordForm } from './PaymentRecordForm';
import { useAdminPermissions } from '../hooks/useAdminPermissions';
import { FilterPanel, FilterableHeader } from '../../../components/filters';
import { useFilterableTable } from '../../../hooks/useFilterableTable';

interface PaymentsTabProps {
  eventFilter?: string;
}

function getPaymentStatusBadge(status: 'paid' | 'partial' | 'unpaid') {
  switch (status) {
    case 'paid':
      return <Badge colorScheme="green">Betaald</Badge>;
    case 'partial':
      return <Badge colorScheme="yellow">Deels betaald</Badge>;
    case 'unpaid':
      return <Badge colorScheme="red">Onbetaald</Badge>;
    default:
      return <Badge>{status}</Badge>;
  }
}

function formatCurrency(amount: number): string {
  return `€ ${(Number(amount) || 0).toFixed(2)}`;
}

interface ColumnFilters {
  [key: string]: string;
  customer: string;
  total: string;
  paid: string;
  outstanding: string;
  payment_status: string;
}

const INITIAL_FILTERS: ColumnFilters = {
  customer: '',
  total: '',
  paid: '',
  outstanding: '',
  payment_status: '',
};

export const PaymentsTab: React.FC<PaymentsTabProps> = ({ eventFilter = '' }) => {
  const { aggregates, orderPayments, loading, error, recordPayment, refetch } =
    useAdminPayments(eventFilter);
  const { canMutate } = useAdminPermissions();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedPayment, setSelectedPayment] = useState<OrderPaymentSummary | null>(null);

  // useFilterableTable for column text filters + sort
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
  } = useFilterableTable(orderPayments as unknown as Record<string, unknown>[], {
    initialFilters: INITIAL_FILTERS,
    defaultSort: { field: 'customer', direction: 'asc' },
  });

  const handleRowClick = (payment: OrderPaymentSummary) => {
    setSelectedPayment(payment);
    onOpen();
  };

  const handleModalClose = () => {
    setSelectedPayment(null);
    onClose();
  };

  const handlePaymentRecorded = async (data: any) => {
    await recordPayment(data);
    handleModalClose();
  };

  if (loading) {
    return (
      <Box p={4} textAlign="center">
        <Spinner size="lg" color="orange.400" />
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

  return (
    <Box>
      {/* Aggregate Stats */}
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={6}>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal Gefactureerd</StatLabel>
          <StatNumber color="white">{formatCurrency(aggregates.totalCharged)}</StatNumber>
          <StatHelpText color="gray.400">Alle bestellingen</StatHelpText>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal Betaald</StatLabel>
          <StatNumber color="green.300">{formatCurrency(aggregates.totalPaid)}</StatNumber>
          <StatHelpText color="gray.400">Ontvangen betalingen</StatHelpText>
        </Stat>
        <Stat bg="gray.700" p={4} borderRadius="md">
          <StatLabel color="gray.300">Totaal Openstaand</StatLabel>
          <StatNumber color="red.300">{formatCurrency(aggregates.totalOutstanding)}</StatNumber>
          <StatHelpText color="gray.400">Nog te ontvangen</StatHelpText>
        </Stat>
      </SimpleGrid>

      {/* Filter panel */}
      <FilterPanel
        hasActiveFilters={hasActiveFilters}
        onReset={resetFilters}
        filteredCount={filteredCount}
        totalCount={orderPayments.length}
      >
        <></>
      </FilterPanel>

      {/* Filterable Payment List */}
      <Box bg="gray.800" borderRadius="md" overflowX="auto">
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              <FilterableHeader
                label="Klant"
                filterValue={filters.customer}
                onFilterChange={(v) => setFilter('customer', v)}
                sortable
                sortDirection={sortField === 'customer' ? sortDirection : null}
                onSort={() => handleSort('customer')}
                minW="150px"
              />
              <FilterableHeader
                label="Totaal"
                filterValue={filters.total}
                onFilterChange={(v) => setFilter('total', v)}
                sortable
                sortDirection={sortField === 'total' ? sortDirection : null}
                onSort={() => handleSort('total')}
                minW="90px"
              />
              <FilterableHeader
                label="Betaald"
                filterValue={filters.paid}
                onFilterChange={(v) => setFilter('paid', v)}
                sortable
                sortDirection={sortField === 'paid' ? sortDirection : null}
                onSort={() => handleSort('paid')}
                minW="90px"
              />
              <FilterableHeader
                label="Openstaand"
                filterValue={filters.outstanding}
                onFilterChange={(v) => setFilter('outstanding', v)}
                sortable
                sortDirection={sortField === 'outstanding' ? sortDirection : null}
                onSort={() => handleSort('outstanding')}
                minW="90px"
              />
              <FilterableHeader
                label="Status"
                filterValue={filters.payment_status}
                onFilterChange={(v) => setFilter('payment_status', v)}
                sortable
                sortDirection={sortField === 'payment_status' ? sortDirection : null}
                onSort={() => handleSort('payment_status')}
                minW="100px"
              />
            </Tr>
          </Thead>
          <Tbody>
            {(processedData as unknown as OrderPaymentSummary[]).length === 0 ? (
              <Tr>
                <Td colSpan={5} textAlign="center" color="gray.500">
                  Geen betalingsgegevens gevonden
                </Td>
              </Tr>
            ) : (
              (processedData as unknown as OrderPaymentSummary[]).map((order) => (
                <Tr
                  key={order.order_id}
                  cursor="pointer"
                  _hover={{ bg: 'gray.700' }}
                  onClick={() => handleRowClick(order)}
                >
                  <Td color="white">{order.customer}</Td>
                  <Td color="white" isNumeric>{formatCurrency(order.total)}</Td>
                  <Td color="green.300" isNumeric>{formatCurrency(order.paid)}</Td>
                  <Td color="red.300" isNumeric>{formatCurrency(order.outstanding)}</Td>
                  <Td>{getPaymentStatusBadge(order.payment_status)}</Td>
                </Tr>
              ))
            )}
          </Tbody>
        </Table>
      </Box>

      {/* Payment Detail Modal */}
      {selectedPayment && (
        <Modal isOpen={isOpen} onClose={handleModalClose} size="lg" isCentered>
          <ModalOverlay />
          <ModalContent bg="gray.800">
            <ModalHeader color="white">
              Betaling — {selectedPayment.customer}
            </ModalHeader>
            <ModalCloseButton color="white" />
            <ModalBody pb={6}>
              <VStack spacing={4} align="stretch">
                {/* Payment summary */}
                <SimpleGrid columns={2} spacing={3}>
                  <Box>
                    <Text fontSize="xs" color="gray.400">Totaal gefactureerd</Text>
                    <Text color="white" fontWeight="bold">{formatCurrency(selectedPayment.total)}</Text>
                  </Box>
                  <Box>
                    <Text fontSize="xs" color="gray.400">Reeds betaald</Text>
                    <Text color="green.300" fontWeight="bold">{formatCurrency(selectedPayment.paid)}</Text>
                  </Box>
                  <Box>
                    <Text fontSize="xs" color="gray.400">Openstaand</Text>
                    <Text color="red.300" fontWeight="bold">{formatCurrency(selectedPayment.outstanding)}</Text>
                  </Box>
                  <Box>
                    <Text fontSize="xs" color="gray.400">Status</Text>
                    {getPaymentStatusBadge(selectedPayment.payment_status)}
                  </Box>
                </SimpleGrid>

                <Text fontSize="xs" color="gray.500" fontFamily="mono">
                  Order: {selectedPayment.order_id}
                </Text>

                {/* Record payment form (inside modal) */}
                {canMutate && selectedPayment.payment_status !== 'paid' && (
                  <>
                    <Divider borderColor="gray.600" />
                    <PaymentRecordForm
                      onSubmit={handlePaymentRecorded}
                      orderId={selectedPayment.order_id}
                    />
                  </>
                )}
              </VStack>
            </ModalBody>
          </ModalContent>
        </Modal>
      )}
    </Box>
  );
};

export default PaymentsTab;

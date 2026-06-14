import React, { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Alert,
  AlertIcon,
  Heading,
  useToast,
} from '@chakra-ui/react';
import { DownloadIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import {
  CartItem,
  OrderStatus,
  PaymentStatus,
  ProductType,
} from '../types/presmeet';
import { generateBookingPdf } from '../utils/pdfGenerator';

// --- Helpers ---

const STATUS_COLOR: Record<OrderStatus, string> = {
  draft: 'yellow',
  submitted: 'blue',
  locked: 'red',
};

function formatEur(amount: number): string {
  return `€${amount.toFixed(2)}`;
}

function getItemLabel(item: CartItem): string {
  const attrs = item.attributes;
  switch (item.product_type) {
    case 'meeting_ticket':
      return attrs.name ?? '—';
    case 'party_ticket':
      return attrs.name ?? '—';
    case 'tshirt':
      return `${attrs.name ?? '—'} (${attrs.size ?? '?'})`;
    case 'airport_transfer':
      return `${attrs.direction ?? '?'} – ${attrs.airport ?? '?'}`;
    default:
      return '—';
  }
}

/** Compute line total for a single cart item */
function getItemLineTotal(item: CartItem): number {
  if (item.product_type === 'airport_transfer') {
    const persons = Number(item.attributes.persons) || 1;
    return persons * item.unit_price;
  }
  return item.unit_price;
}

function formatDate(isoString: string): string {
  try {
    return new Date(isoString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return isoString;
  }
}

// --- Types ---

interface ProductGroup {
  productType: ProductType;
  items: CartItem[];
  lineTotal: number;
}

export interface BookingOverviewProps {
  items: CartItem[];
  status: OrderStatus;
  paymentStatus: PaymentStatus;
  totalPaid?: number;
  clubName: string;
  clubId: string;
  submittedAt: string | null;
}

// --- Component ---

const BookingOverview: React.FC<BookingOverviewProps> = ({
  items,
  status,
  paymentStatus,
  totalPaid = 0,
  clubName,
  clubId,
  submittedAt,
}) => {
  const { t } = useTranslation('eventBooking');
  const toast = useToast();
  const [isDownloading, setIsDownloading] = useState(false);

  // Group items by product_type
  const groups: ProductGroup[] = React.useMemo(() => {
    const groupMap = new Map<ProductType, CartItem[]>();

    for (const item of items) {
      const existing = groupMap.get(item.product_type) ?? [];
      existing.push(item);
      groupMap.set(item.product_type, existing);
    }

    const result: ProductGroup[] = [];
    for (const [productType, groupItems] of groupMap.entries()) {
      const lineTotal = groupItems.reduce(
        (sum, item) => sum + getItemLineTotal(item),
        0
      );

      result.push({
        productType,
        items: groupItems,
        lineTotal,
      });
    }

    return result;
  }, [items]);

  const grandTotal = groups.reduce((sum, g) => sum + g.lineTotal, 0);
  const remainingBalance = Math.max(0, grandTotal - totalPaid);

  const PRODUCT_TYPE_LABELS: Record<ProductType, string> = {
    meeting_ticket: t('product_types.meeting_ticket'),
    party_ticket: t('product_types.party_ticket'),
    tshirt: t('product_types.tshirt'),
    airport_transfer: t('product_types.airport_transfer'),
  };

  const handleDownloadPdf = () => {
    setIsDownloading(true);
    try {
      generateBookingPdf({
        clubName,
        items,
        status,
        paymentStatus,
        totalAmount: grandTotal,
        totalPaid,
        submittedAt,
      });
    } catch {
      toast({
        title: t('overview.pdf_error_title'),
        description: t('overview.pdf_error_description'),
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsDownloading(false);
    }
  };

  // Empty state
  if (items.length === 0) {
    return (
      <Box>
        <HStack mb={4} justify="space-between">
          <Heading size="md">{t('overview.title')}</Heading>
          <Badge colorScheme={STATUS_COLOR[status]}>{status}</Badge>
        </HStack>
        <Alert status="info" borderRadius="md">
          <AlertIcon />
          {t('overview.no_items')}
        </Alert>
        <HStack mt={4} justify="space-between">
          <Text fontWeight="bold">{t('overview.grand_total')}:</Text>
          <Text fontWeight="bold">{formatEur(0)}</Text>
        </HStack>
      </Box>
    );
  }

  return (
    <Box>
      <HStack mb={4} justify="space-between">
        <Heading size="md">{t('overview.title')}</Heading>
        <HStack spacing={2}>
          <Button
            leftIcon={<DownloadIcon />}
            colorScheme="blue"
            size="sm"
            onClick={handleDownloadPdf}
            isLoading={isDownloading}
            loadingText={t('overview.downloading')}
          >
            {t('overview.download_pdf')}
          </Button>
          <Badge colorScheme={STATUS_COLOR[status]} fontSize="sm" px={2} py={1}>
            {status}
          </Badge>
        </HStack>
      </HStack>

      {/* Club name header */}
      <Text fontSize="lg" fontWeight="semibold" mb={2}>
        {clubName}
      </Text>

      {/* Submission date for submitted/locked orders */}
      {(status === 'submitted' || status === 'locked') && submittedAt && (
        <Text fontSize="sm" color="gray.600" mb={4}>
          {t('overview.submitted_at')}: {formatDate(submittedAt)}
        </Text>
      )}

      <VStack spacing={6} align="stretch">
        {groups.map((group) => (
          <Box key={group.productType} borderWidth="1px" borderRadius="md" p={4}>
            <HStack justify="space-between" mb={2}>
              <Text fontWeight="bold" fontSize="md">
                {PRODUCT_TYPE_LABELS[group.productType]}
              </Text>
              <Text fontSize="sm" color="gray.600">
                {formatEur(group.lineTotal)}
              </Text>
            </HStack>

            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>{t('overview.item')}</Th>
                  <Th isNumeric>{t('overview.price')}</Th>
                </Tr>
              </Thead>
              <Tbody>
                {group.items.map((item) => {
                  const persons = Number(item.attributes.persons) || 1;
                  const lineTotal = getItemLineTotal(item);

                  return (
                    <Tr key={item.item_id}>
                      <Td>
                        {getItemLabel(item)}
                        {item.product_type === 'airport_transfer' && persons > 1 && (
                          <Text as="span" fontSize="xs" color="gray.500" ml={2}>
                            ({persons} {t('transfers.persons').toLowerCase()})
                          </Text>
                        )}
                        {item.product_type === 'party_ticket' && item.attributes.person_type === 'delegate' && (
                          <Text as="span" fontSize="xs" color="gray.500" ml={2}>
                            ({t('overview.delegate')})
                          </Text>
                        )}
                      </Td>
                      <Td isNumeric>
                        {item.product_type === 'airport_transfer' && persons > 1
                          ? `${persons} × ${formatEur(item.unit_price)} = ${formatEur(lineTotal)}`
                          : formatEur(lineTotal)}
                      </Td>
                    </Tr>
                  );
                })}
              </Tbody>
            </Table>
          </Box>
        ))}

        {/* Summary section */}
        <Box borderWidth="1px" borderRadius="md" p={4}>
          <Table size="sm" variant="simple">
            <Tbody>
              <Tr>
                <Td fontWeight="bold">{t('overview.grand_total')}</Td>
                <Td isNumeric fontWeight="bold" fontSize="md">{formatEur(grandTotal)}</Td>
              </Tr>
              <Tr>
                <Td>{t('overview.total_paid')}</Td>
                <Td isNumeric>{formatEur(totalPaid)}</Td>
              </Tr>
              <Tr>
                <Td fontWeight="bold">{t('overview.remaining_balance')}</Td>
                <Td isNumeric fontWeight="bold">{formatEur(remainingBalance)}</Td>
              </Tr>
            </Tbody>
          </Table>
        </Box>
      </VStack>
    </Box>
  );
};

export default BookingOverview;

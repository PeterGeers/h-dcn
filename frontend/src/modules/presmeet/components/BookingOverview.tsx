import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Table,
  Thead,
  Tbody,
  Tfoot,
  Tr,
  Th,
  Td,
  Alert,
  AlertIcon,
  Heading,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import {
  CartItem,
  OrderStatus,
  ProductType,
} from '../types/presmeet';

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

// --- Types ---

interface ProductGroup {
  productType: ProductType;
  items: CartItem[];
  unitPrice: number;
  quantity: number;
  lineTotal: number;
}

export interface BookingOverviewProps {
  items: CartItem[];
  status: OrderStatus;
  totalPaid?: number;
}

// --- Component ---

const BookingOverview: React.FC<BookingOverviewProps> = ({
  items,
  status,
  totalPaid = 0,
}) => {
  const { t } = useTranslation('presmeet');

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
      const unitPrice = groupItems[0]?.unit_price ?? 0;
      let lineTotal: number;

      if (productType === 'airport_transfer') {
        lineTotal = groupItems.reduce(
          (sum, i) => sum + (Number(i.attributes.persons) || 0) * (i.unit_price || 5),
          0
        );
      } else {
        lineTotal = groupItems.length * unitPrice;
      }

      result.push({
        productType,
        items: groupItems,
        unitPrice,
        quantity: groupItems.length,
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
        <Badge colorScheme={STATUS_COLOR[status]} fontSize="sm" px={2} py={1}>
          {status}
        </Badge>
      </HStack>

      <VStack spacing={6} align="stretch">
        {groups.map((group) => (
          <Box key={group.productType} borderWidth="1px" borderRadius="md" p={4}>
            <HStack justify="space-between" mb={2}>
              <Text fontWeight="bold" fontSize="md">
                {PRODUCT_TYPE_LABELS[group.productType]}
              </Text>
              <Text fontSize="sm" color="gray.600">
                {t('overview.items_count', { count: group.quantity })} × {formatEur(group.unitPrice)} = {formatEur(group.lineTotal)}
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
                {group.items.map((item) => (
                  <Tr key={item.item_id}>
                    <Td>{getItemLabel(item)}</Td>
                    <Td isNumeric>
                      {group.productType === 'airport_transfer'
                        ? formatEur((Number(item.attributes.persons) || 0) * (item.unit_price || 5))
                        : formatEur(item.unit_price || 0)}
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        ))}

        {/* Totals */}
        <Table size="sm" variant="simple">
          <Tfoot>
            <Tr>
              <Th>{t('overview.grand_total')}</Th>
              <Th isNumeric fontSize="md">{formatEur(grandTotal)}</Th>
            </Tr>
            <Tr>
              <Td>{t('overview.total_paid')}</Td>
              <Td isNumeric>{formatEur(totalPaid)}</Td>
            </Tr>
            <Tr>
              <Td fontWeight="bold">{t('overview.remaining_balance')}</Td>
              <Td isNumeric fontWeight="bold">{formatEur(remainingBalance)}</Td>
            </Tr>
          </Tfoot>
        </Table>
      </VStack>
    </Box>
  );
};

export default BookingOverview;

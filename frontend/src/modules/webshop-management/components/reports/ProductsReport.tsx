/**
 * ProductsReport — Select product → show definition, variants, sold items, totals.
 *
 * Validates: Requirements 11.5, 11.6, 11.7
 */

import React, { useState } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  Select,
  Badge,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Divider,
} from '@chakra-ui/react';
import { ReportResponse } from '../../types/admin.types';
import { formatCurrency } from '../ReportsTab';

interface ProductsReportProps {
  report: ReportResponse;
}

export const ProductsReport: React.FC<ProductsReportProps> = ({ report }) => {
  const { products = [], orders = [], summary } = report;
  const [selectedProductId, setSelectedProductId] = useState<string>('');

  const selectedProduct = products.find((p) => p.product_id === selectedProductId);

  // Gather sold items for the selected product from orders
  const soldItems = selectedProduct
    ? orders.flatMap((order) =>
        order.items
          .filter((item) => item.product_id === selectedProductId)
          .map((item) => ({
            ...item,
            order_id: order.order_id,
            club_name: order.club_name,
            order_status: order.status,
            payment_status: order.payment_status,
          }))
      )
    : [];

  const totalItemsSold = soldItems.reduce((sum, item) => sum + item.quantity, 0);
  const totalRevenue = soldItems.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);

  return (
    <Box>
      {/* Product Selector */}
      <Box mb={6}>
        <Text fontSize="sm" fontWeight="medium" color="gray.300" mb={2}>
          Selecteer product
        </Text>
        <Select
          value={selectedProductId}
          onChange={(e) => setSelectedProductId(e.target.value)}
          placeholder="Kies een product..."
          maxW="400px"
          size="sm"
        >
          {products.map((product) => (
            <option key={product.product_id} value={product.product_id}>
              {product.name} — {formatCurrency(product.price)}
            </option>
          ))}
        </Select>
      </Box>

      {/* Overall product summary from report */}
      {summary.by_product && summary.by_product.length > 0 && !selectedProductId && (
        <Box bg="gray.800" borderRadius="md" p={4} mb={6}>
          <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
            Overzicht alle producten
          </Text>
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th color="gray.400">Product</Th>
                <Th color="gray.400" isNumeric>Items verkocht</Th>
                <Th color="gray.400" isNumeric>Omzet</Th>
              </Tr>
            </Thead>
            <Tbody>
              {summary.by_product.map((p, idx) => (
                <Tr key={idx}>
                  <Td color="white">{p.product_name}</Td>
                  <Td color="white" isNumeric>{p.items_sold}</Td>
                  <Td color="white" isNumeric>{formatCurrency(p.revenue)}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}

      {/* Selected Product Detail */}
      {selectedProduct && (
        <Box>
          {/* Product Definition */}
          <Box bg="gray.800" borderRadius="md" p={4} mb={4}>
            <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
              Productdefinitie: {selectedProduct.name}
            </Text>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3} mb={3}>
              <Box>
                <Text fontSize="xs" color="gray.400">Prijs</Text>
                <Text color="white">{formatCurrency(selectedProduct.price)}</Text>
              </Box>
              <Box>
                <Text fontSize="xs" color="gray.400">Status</Text>
                <Badge colorScheme={selectedProduct.active ? 'green' : 'red'}>
                  {selectedProduct.active ? 'Actief' : 'Inactief'}
                </Badge>
              </Box>
              {selectedProduct.product_type && (
                <Box>
                  <Text fontSize="xs" color="gray.400">Producttype</Text>
                  <Text color="white">{selectedProduct.product_type}</Text>
                </Box>
              )}
            </SimpleGrid>
          </Box>

          {/* Variants */}
          {selectedProduct.variants && selectedProduct.variants.length > 0 && (
            <Box bg="gray.800" borderRadius="md" p={4} mb={4}>
              <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
                Varianten ({selectedProduct.variants.length})
              </Text>
              <Box overflowX="auto">
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th color="gray.400">Attributen</Th>
                      <Th color="gray.400" isNumeric>Prijs</Th>
                      <Th color="gray.400" isNumeric>Voorraad</Th>
                      <Th color="gray.400" isNumeric>Verkocht</Th>
                      <Th color="gray.400">Oversell</Th>
                      <Th color="gray.400">Status</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {selectedProduct.variants.map((variant) => (
                      <Tr key={variant.product_id}>
                        <Td color="white">
                          {Object.entries(variant.variant_attributes)
                            .map(([k, v]) => `${k}: ${v}`)
                            .join(', ') || 'Standaard'}
                        </Td>
                        <Td color="white" isNumeric>
                          {variant.price != null ? formatCurrency(variant.price) : '—'}
                        </Td>
                        <Td color="white" isNumeric>{variant.stock}</Td>
                        <Td color="white" isNumeric>{variant.sold_count}</Td>
                        <Td>
                          <Badge colorScheme={variant.allow_oversell ? 'yellow' : 'gray'} fontSize="xs">
                            {variant.allow_oversell ? 'Ja' : 'Nee'}
                          </Badge>
                        </Td>
                        <Td>
                          <Badge colorScheme={variant.active ? 'green' : 'red'} fontSize="xs">
                            {variant.active ? 'Actief' : 'Inactief'}
                          </Badge>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            </Box>
          )}

          <Divider borderColor="gray.600" mb={4} />

          {/* Sold Items */}
          <Box bg="gray.800" borderRadius="md" p={4} mb={4}>
            <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
              Verkochte items ({soldItems.length})
            </Text>
            {soldItems.length === 0 ? (
              <Text color="gray.400">Geen items verkocht voor dit product.</Text>
            ) : (
              <Box overflowX="auto">
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th color="gray.400">Order</Th>
                      <Th color="gray.400">Variant</Th>
                      <Th color="gray.400">Club</Th>
                      <Th color="gray.400" isNumeric>Aantal</Th>
                      <Th color="gray.400" isNumeric>Stuksprijs</Th>
                      <Th color="gray.400">Order status</Th>
                      <Th color="gray.400">Betaling</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {soldItems.map((item, idx) => (
                      <Tr key={idx}>
                        <Td>
                          <Text fontSize="xs" fontFamily="mono" color="white">
                            {item.order_id.slice(0, 12)}…
                          </Text>
                        </Td>
                        <Td color="white" fontSize="sm">
                          {item.variant_attributes
                            ? Object.values(item.variant_attributes).join(', ')
                            : '—'}
                        </Td>
                        <Td color="white" fontSize="sm">{item.club_name || '—'}</Td>
                        <Td color="white" isNumeric>{item.quantity}</Td>
                        <Td color="white" isNumeric>{formatCurrency(item.unit_price)}</Td>
                        <Td>
                          <Badge fontSize="xs" colorScheme="blue">{item.order_status}</Badge>
                        </Td>
                        <Td>
                          <Badge fontSize="xs" colorScheme={
                            item.payment_status === 'paid' ? 'green' :
                            item.payment_status === 'partial' ? 'yellow' : 'red'
                          }>
                            {item.payment_status}
                          </Badge>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            )}
          </Box>

          {/* Totals */}
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Stat bg="gray.700" p={4} borderRadius="md">
              <StatLabel color="gray.300">Totaal items verkocht</StatLabel>
              <StatNumber color="white">{totalItemsSold}</StatNumber>
            </Stat>
            <Stat bg="gray.700" p={4} borderRadius="md">
              <StatLabel color="gray.300">Totaal regels</StatLabel>
              <StatNumber color="white">{soldItems.length}</StatNumber>
            </Stat>
            <Stat bg="gray.700" p={4} borderRadius="md">
              <StatLabel color="gray.300">Totale omzet</StatLabel>
              <StatNumber color="white">{formatCurrency(totalRevenue)}</StatNumber>
            </Stat>
          </SimpleGrid>
        </Box>
      )}
    </Box>
  );
};

export default ProductsReport;

import React from 'react';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  Box
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { VariantSchema } from '../types/unifiedProduct.types';

interface Product {
  product_id: string;
  id?: string;
  name?: string;
  naam?: string;
  groep?: string;
  subgroep?: string;
  price?: number;
  prijs?: number | string;
  variant_schema?: VariantSchema;
}

interface ProductTableProps {
  products: Product[];
  onProductSelect: (product: Product) => void;
}

/** Format variant schema for display in the table */
function formatVariantSummary(schema?: VariantSchema): string {
  if (!schema || Object.keys(schema).length === 0) {
    return 'Standaard';
  }
  return Object.entries(schema)
    .map(([axis, values]) => {
      const valuesArray = Array.isArray(values) ? values : [String(values)];
      return `${axis}: ${valuesArray.join(', ')}`;
    })
    .join(' | ');
}

const ProductTable: React.FC<ProductTableProps> = ({ products, onProductSelect }) => {
  const { t } = useTranslation('products');
  return (
    <Box 
      bg="gray.800" 
      borderRadius="md" 
      border="1px" 
      borderColor="orange.400" 
      overflow="auto"
      maxW="100%"
    >
      <Table variant="simple" size={{ base: 'sm', md: 'md' }}>
        <Thead bg="gray.700">
          <Tr>
            <Th color="orange.300" w="40%">{t('table.name')}</Th>
            <Th color="orange.300" minW="100px" display={{ base: 'none', md: 'table-cell' }}>{t('table.group')}</Th>
            <Th color="orange.300" minW="100px" display={{ base: 'none', lg: 'table-cell' }}>{t('table.subgroup')}</Th>
            <Th color="orange.300" minW="80px" isNumeric>{t('table.price')}</Th>
            <Th color="orange.300" w="30%" display={{ base: 'none', md: 'table-cell' }}>{t('table.options')}</Th>
          </Tr>
        </Thead>
        <Tbody>
          {products.map((product) => {
            const displayName = product.name || product.naam || '';
            const displayPrice = product.price ?? product.prijs;
            return (
              <Tr
                key={product.product_id || product.id}
                cursor="pointer"
                _hover={{ bg: 'orange.500', color: 'white' }}
                onClick={() => onProductSelect(product)}
                color="white"
              >
                <Td fontWeight="medium" fontSize={{ base: 'xs', md: 'sm' }}>
                  {displayName}
                </Td>
                <Td fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                  <Text isTruncated maxW="100px">{product.groep}</Text>
                </Td>
                <Td fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', lg: 'table-cell' }}>
                  <Text isTruncated maxW="100px">{product.subgroep}</Text>
                </Td>
                <Td fontSize={{ base: 'xs', md: 'sm' }} isNumeric>
                  €{displayPrice ? Number(displayPrice).toFixed(2) : '0.00'}
                </Td>
                <Td fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                  <Box maxW="150px">
                    <Text noOfLines={2}>{formatVariantSummary(product.variant_schema)}</Text>
                  </Box>
                </Td>
              </Tr>
            );
          })}
        </Tbody>
      </Table>
    </Box>
  );
};

export default ProductTable;
import React from 'react';
import { Table, Tbody, Td, Th, Thead, Tr, Box, Text, Badge } from '@chakra-ui/react';
import { Product } from '../../../types';
import { useTranslation } from 'react-i18next';
import { isDeactivated } from '../../../utils/productHelpers';

interface ProductTableProps {
  products: Product[];
  onSelect: (product: Product) => void;
  renderActions?: (product: Product) => React.ReactNode;
  showStatusColumn?: boolean;
}

export default function ProductTable({ products, onSelect, renderActions, showStatusColumn }: ProductTableProps): React.ReactElement {
  const { t } = useTranslation('products');

  return (
    <Box overflow="auto" maxW="100%" bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400">
      <Table variant="simple" colorScheme="orange" size={{ base: 'sm', md: 'md' }}>
        <Thead bg="gray.700">
          <Tr>
            <Th color="orange.300" minW="60px">Artikelcode</Th>
            <Th color="orange.300" minW="120px" display={{ base: 'none', md: 'table-cell' }}>Categorie</Th>
            <Th color="orange.300" w="50%">Naam</Th>
            <Th color="orange.300" minW="80px">Prijs</Th>
            {showStatusColumn && <Th color="orange.300" minW="80px">Status</Th>}
            {renderActions && <Th color="orange.300" minW="120px">{t('table.actions')}</Th>}
          </Tr>
        </Thead>
        <Tbody>
          {products.map((p) => (
            <Tr
              key={p.product_id || p.id}
              _hover={{ bg: 'orange.500', cursor: 'pointer', color: 'white' }}
              onClick={() => onSelect(p)}
              color="white"
              opacity={isDeactivated(p) ? 0.6 : 1}
            >
              <Td fontSize={{ base: 'xs', md: 'sm' }}>{p.artikelcode || '-'}</Td>
              <Td fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                <Text isTruncated maxW="120px">{p.groep} - {p.subgroep}</Text>
              </Td>
              <Td fontSize={{ base: 'xs', md: 'sm' }}>
                {p.naam}
              </Td>
              <Td fontSize={{ base: 'xs', md: 'sm' }}>€{p.prijs}</Td>
              {showStatusColumn && (
                <Td fontSize={{ base: 'xs', md: 'sm' }}>
                  {isDeactivated(p) ? (
                    <Badge colorScheme="red" variant="subtle">{t('management.inactive_badge')}</Badge>
                  ) : (
                    <Badge colorScheme="green" variant="subtle">Actief</Badge>
                  )}
                </Td>
              )}
              {renderActions && (
                <Td onClick={(e) => e.stopPropagation()}>
                  {renderActions(p)}
                </Td>
              )}
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
}

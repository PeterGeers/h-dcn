import React from 'react';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Text,
  Box
} from '@chakra-ui/react';

const ProductTable = ({ products, onProductSelect }) => {
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
            <Th color="orange.300" w="40%">Naam</Th>
            <Th color="orange.300" minW="100px" display={{ base: 'none', md: 'table-cell' }}>Groep</Th>
            <Th color="orange.300" minW="100px" display={{ base: 'none', lg: 'table-cell' }}>Subgroep</Th>
            <Th color="orange.300" minW="80px" isNumeric>Prijs</Th>
            <Th color="orange.300" w="30%" display={{ base: 'none', md: 'table-cell' }}>Beschrijving</Th>
          </Tr>
        </Thead>
        <Tbody>
          {products.map((product, index) => (
            <Tr
              key={product.id}
              cursor="pointer"
              _hover={{ bg: 'orange.500', color: 'white' }}
              onClick={() => onProductSelect(product)}
              color="white"
            >
              <Td fontWeight="medium" fontSize={{ base: 'xs', md: 'sm' }}>
                {product.naam}
              </Td>
              <Td fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                <Text isTruncated maxW="100px">{product.groep}</Text>
              </Td>
              <Td fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', lg: 'table-cell' }}>
                <Text isTruncated maxW="100px">{product.subgroep}</Text>
              </Td>
              <Td fontSize={{ base: 'xs', md: 'sm' }} isNumeric>
                €{product.prijs ? Number(product.prijs).toFixed(2) : '0.00'}
              </Td>
              <Td fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                <Box maxW="150px">
                  <Text noOfLines={2}>{product.beschrijving}</Text>
                </Box>
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
};

export default ProductTable;
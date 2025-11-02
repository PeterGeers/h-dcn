import React from 'react';
import { Table, Tbody, Td, Th, Thead, Tr, Box, Button, HStack, useDisclosure, Text } from '@chakra-ui/react';
import { Modal, ModalOverlay, ModalContent, ModalHeader, ModalCloseButton, ModalBody } from '@chakra-ui/react';
import ImageEditor from './ImageEditor';
import { Product } from '../../../types';

interface ProductTableProps {
  products: Product[];
  onSelect: (product: Product) => void;
}

export default function ProductTable({ products, onSelect }: ProductTableProps): React.ReactElement {
  const { isOpen, onOpen, onClose } = useDisclosure();

  return (
    <>
      <Box>
        <HStack mb={4} justify="flex-end">
          <Button colorScheme="orange" onClick={onOpen} size={{ base: 'sm', md: 'md' }}>
            Image Editor
          </Button>
        </HStack>
        
        <Box overflow="auto" maxW="100%" bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400">
          <Table variant="simple" colorScheme="orange" size={{ base: 'sm', md: 'md' }}>
            <Thead bg="gray.700">
              <Tr>
                <Th color="orange.300" minW="60px">ID</Th>
                <Th color="orange.300" minW="120px" display={{ base: 'none', md: 'table-cell' }}>Categorie</Th>
                <Th color="orange.300" w="50%">Naam</Th>
                <Th color="orange.300" minW="80px">Prijs</Th>
              </Tr>
            </Thead>
            <Tbody>
              {products.map((p) => (
                <Tr
                  key={p.id}
                  _hover={{ bg: 'orange.500', cursor: 'pointer', color: 'white' }}
                  onClick={() => onSelect(p)}
                  color="white"
                >
                  <Td fontSize={{ base: 'xs', md: 'sm' }}>{p.id}</Td>
                  <Td fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                    <Text isTruncated maxW="120px">{p.groep} - {p.subgroep}</Text>
                  </Td>
                  <Td fontSize={{ base: 'xs', md: 'sm' }}>
                    {p.naam}
                  </Td>
                  <Td fontSize={{ base: 'xs', md: 'sm' }}>€{p.prijs}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </Box>
      
      <Modal isOpen={isOpen} onClose={onClose} size="6xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Image Editor</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <ImageEditor />
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
}

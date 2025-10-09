import React, { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  Text,
  VStack,
  HStack,
  Select,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  useToast
} from '@chakra-ui/react';

const ProductCardModal = ({ product, isOpen, onClose, onAddToCart }) => {
  const [selectedOption, setSelectedOption] = useState('');
  const [quantity, setQuantity] = useState(1);
  const toast = useToast();

  if (!product) return null;

  const options = product.opties && typeof product.opties === 'string' ? product.opties.split(',').map(opt => opt.trim()) : [];

  const handleAddToCart = () => {
    if (options.length > 0 && !selectedOption) {
      toast({
        title: 'Selecteer een optie',
        description: 'Kies een maat/optie voor dit product',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    const cartItem = {
      product_id: product.id,
      naam: product.naam,
      price: product.prijs,
      quantity: quantity,
      selectedOption: selectedOption || 'Standaard'
    };

    if (onAddToCart) {
      onAddToCart(cartItem);
    }

    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{product.naam}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack align="stretch" spacing={4}>
            <Text fontSize="xl" fontWeight="bold" color="orange.500">
              €{Number(product.prijs).toFixed(2)}
            </Text>
            
            <Text>{product.beschrijving}</Text>
            
            <Text><strong>Groep:</strong> {product.groep}</Text>
            <Text><strong>Subgroep:</strong> {product.subgroep}</Text>
            
            {options.length > 0 && (
              <VStack align="stretch">
                <Text fontWeight="bold">Kies een optie:</Text>
                <Select
                  placeholder="Selecteer optie"
                  value={selectedOption}
                  onChange={(e) => setSelectedOption(e.target.value)}
                >
                  {options.map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </Select>
              </VStack>
            )}
            
            <HStack>
              <Text fontWeight="bold">Aantal:</Text>
              <NumberInput
                value={quantity}
                onChange={(value) => setQuantity(parseInt(value) || 1)}
                min={1}
                max={10}
                maxW="100px"
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </HStack>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Sluiten
          </Button>
          <Button colorScheme="orange" onClick={handleAddToCart}>
            Toevoegen aan winkelwagen
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ProductCardModal;
import React from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  HStack,
  Text,
  Button,
  IconButton,
  Divider,
  Box,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper
} from '@chakra-ui/react';
import { DeleteIcon, CheckIcon } from '@chakra-ui/icons';

interface CartItem {
  product_id: string;
  name?: string;
  naam?: string;
  price?: number;
  quantity: number;
  selectedOption?: string;
}

interface CartModalProps {
  isOpen: boolean;
  onClose: () => void;
  cartItems: CartItem[];
  onRemoveItem: (productId: string) => void;
  onCheckout: () => void;
  onClearCart: () => void;
  onUpdateQuantity: (productId: string, quantity: number) => void;
  onSaveCart: () => void;
}

const CartModal: React.FC<CartModalProps> = ({ 
  isOpen, 
  onClose, 
  cartItems, 
  onRemoveItem, 
  onCheckout, 
  onClearCart, 
  onUpdateQuantity, 
  onSaveCart 
}) => {
  const totalAmount = cartItems.reduce((sum, item) => sum + (Number(item.price || 0) * item.quantity), 0);
  const itemCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent bg="black" color="white" borderWidth="3px" borderColor="orange.500">
        <ModalHeader color="white">Winkelwagen</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          {cartItems.length === 0 ? (
            <Text color="white">Uw winkelwagen is leeg</Text>
          ) : (
            <VStack spacing={4} align="stretch">
              {cartItems.map((item, index) => (
                <Box key={index} p={3} borderWidth={1} borderColor="white" borderRadius="md" bg="black">
                  <HStack justify="space-between">
                    <VStack align="start" spacing={2} flex={1}>
                      <Text fontWeight="medium" color="white">{item.name || item.naam}</Text>
                      {item.selectedOption && (
                        <Text fontSize="sm" color="gray.300">
                          Optie: {item.selectedOption}
                        </Text>
                      )}
                      <HStack spacing={3}>
                        <NumberInput
                          size="sm"
                          maxW={20}
                          min={1}
                          value={item.quantity}
                          onChange={(value) => onUpdateQuantity(item.product_id, parseInt(value) || 1)}
                        >
                          <NumberInputField bg="white" color="black" />
                          <NumberInputStepper>
                            <NumberIncrementStepper color="black" />
                            <NumberDecrementStepper color="black" />
                          </NumberInputStepper>
                        </NumberInput>
                        <Text fontSize="sm" color="white">
                          x €{item.price ? Number(item.price).toFixed(2) : '0.00'} = €{(item.quantity * Number(item.price || 0)).toFixed(2)}
                        </Text>
                      </HStack>
                    </VStack>
                    <IconButton
                      icon={<DeleteIcon />}
                      size="sm"
                      colorScheme="red"
                      variant="ghost"
                      onClick={() => onRemoveItem(item.product_id)}
                      aria-label="Remove item"
                    />
                  </HStack>
                </Box>
              ))}
              
              <Divider />
              
              <VStack spacing={2}>
                <HStack justify="space-between" width="full">
                  <Text fontSize="sm" color="white">Aantal items:</Text>
                  <Text fontSize="sm" color="white">{itemCount}</Text>
                </HStack>
                <HStack justify="space-between" width="full">
                  <Text fontSize="lg" fontWeight="bold" color="white">Totaal:</Text>
                  <Text fontSize="lg" fontWeight="bold" color="white">€{totalAmount.toFixed(2)}</Text>
                </HStack>
              </VStack>
              
              <VStack spacing={2}>
                <Button
                  bg="orange.500"
                  color="white"
                  _hover={{ bg: "orange.500", opacity: 0.8 }}
                  onClick={onCheckout}
                  width="full"
                  size="lg"
                  leftIcon={<CheckIcon />}
                >
                  Afrekenen
                </Button>
                <Button
                  variant="outline"
                  borderColor="orange.500"
                  color="orange.500"
                  _hover={{ bg: "orange.500", color: "white" }}
                  onClick={onSaveCart}
                  width="full"
                >
                  Winkelwagen bewaren
                </Button>
                <Button
                  variant="outline"
                  onClick={onClearCart}
                  width="full"
                >
                  Winkelwagen legen
                </Button>
              </VStack>
            </VStack>
          )}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default CartModal;
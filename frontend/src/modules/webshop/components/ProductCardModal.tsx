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
import { useTranslation } from 'react-i18next';

interface Product {
  id: string;
  naam: string;
  prijs: number | string;
  groep?: string;
  subgroep?: string;
  opties?: string;
}

interface CartItem {
  product_id: string;
  naam: string;
  price: number | string;
  quantity: number;
  selectedOption: string;
}

interface ProductCardModalProps {
  product: Product | null;
  isOpen: boolean;
  onClose: () => void;
  onAddToCart?: (cartItem: CartItem) => void;
}

const ProductCardModal: React.FC<ProductCardModalProps> = ({ product, isOpen, onClose, onAddToCart }) => {
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [quantity, setQuantity] = useState<number>(1);
  const toast = useToast();
  const { t } = useTranslation('products');
  const { t: tCommon } = useTranslation('common');

  if (!product) return null;

  const options = product.opties && typeof product.opties === 'string' ? product.opties.split(',').map(opt => opt.trim()) : [];

  const handleAddToCart = (): void => {
    if (options.length > 0 && !selectedOption) {
      toast({
        title: t('card.select_option'),
        description: t('card_modal.select_option_desc'),
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    const cartItem: CartItem = {
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
            
            <Text><strong>{t('table.group')}:</strong> {product.groep}</Text>
            <Text><strong>{t('table.subgroup')}:</strong> {product.subgroep}</Text>
            
            {options.length > 0 && (
              <VStack align="stretch">
                <Text fontWeight="bold">{t('card.select_option')}:</Text>
                <Select
                  placeholder={t('card.select_option')}
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
              <Text fontWeight="bold">{t('card.quantity')}:</Text>
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
            {tCommon('buttons.close')}
          </Button>
          <Button colorScheme="orange" onClick={handleAddToCart}>
            {t('card.add_to_cart')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ProductCardModal;
import React, { useCallback, useState } from 'react';
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
  NumberDecrementStepper,
  Collapse,
} from '@chakra-ui/react';
import { DeleteIcon, CheckIcon, ChevronDownIcon, ChevronUpIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import ItemFieldsForm from './ItemFieldsForm';
import { OrderItemField, ItemFieldsEntry } from '../types/unifiedProduct.types';

interface CartItem {
  product_id: string;
  name?: string;
  naam?: string;
  price?: number;
  quantity: number;
  selectedOption?: string;
  variant_id?: string;
  variant_attributes?: Record<string, string>;
  item_fields_data?: ItemFieldsEntry[];
}

/** Product info needed by CartModal to render item fields */
export interface CartProductInfo {
  product_id: string;
  order_item_fields?: OrderItemField[];
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
  /** Product info map for rendering item fields (keyed by product_id) */
  products?: CartProductInfo[];
  /** Called when item_fields_data changes for a cart item */
  onItemFieldsChange?: (productId: string, itemFieldsData: ItemFieldsEntry[]) => void;
}

/**
 * Formats variant_attributes as a readable string (e.g., "Maat: M, Gender: Male").
 */
function formatVariantAttributes(attrs: Record<string, string>): string {
  return Object.entries(attrs)
    .map(([axis, value]) => `${axis}: ${value}`)
    .join(', ');
}

/**
 * Trims item_fields_data to match the new quantity by removing highest-numbered entries.
 * Retains entries 0..newQuantity-1, discards entries from newQuantity onward.
 */
function trimItemFieldsData(
  currentData: ItemFieldsEntry[] | undefined,
  newQuantity: number
): ItemFieldsEntry[] | undefined {
  if (!currentData || currentData.length === 0) return currentData;
  if (newQuantity >= currentData.length) return currentData;
  return currentData.slice(0, newQuantity);
}

const CartModal: React.FC<CartModalProps> = ({
  isOpen,
  onClose,
  cartItems,
  onRemoveItem,
  onCheckout,
  onClearCart,
  onUpdateQuantity,
  onSaveCart,
  products = [],
  onItemFieldsChange,
}) => {
  const { t } = useTranslation('webshop');
  const totalAmount = cartItems.reduce((sum, item) => sum + (Number(item.price || 0) * item.quantity), 0);
  const itemCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);

  // Track which items have their fields section expanded
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});

  const toggleItemFields = useCallback((productId: string) => {
    setExpandedItems(prev => ({ ...prev, [productId]: !prev[productId] }));
  }, []);

  const getProductInfo = useCallback(
    (productId: string): CartProductInfo | undefined => {
      return products.find(p => p.product_id === productId);
    },
    [products]
  );

  const handleQuantityChange = useCallback(
    (productId: string, newQuantity: number) => {
      const item = cartItems.find(i => i.product_id === productId);
      if (!item) return;

      // If decreasing quantity, trim item_fields_data from the end
      if (newQuantity < item.quantity && item.item_fields_data && onItemFieldsChange) {
        const trimmed = trimItemFieldsData(item.item_fields_data, newQuantity);
        if (trimmed) {
          onItemFieldsChange(productId, trimmed);
        }
      }

      onUpdateQuantity(productId, newQuantity);
    },
    [cartItems, onUpdateQuantity, onItemFieldsChange]
  );

  const handleItemFieldsChange = useCallback(
    (productId: string, values: ItemFieldsEntry[]) => {
      if (onItemFieldsChange) {
        onItemFieldsChange(productId, values);
      }
    },
    [onItemFieldsChange]
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent bg="black" color="white" borderWidth="3px" borderColor="orange.500">
        <ModalHeader color="white">{t('cart.title')}</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          {cartItems.length === 0 ? (
            <Text color="white">{t('cart.empty')}</Text>
          ) : (
            <VStack spacing={4} align="stretch">
              {cartItems.map((item, index) => {
                const productInfo = getProductInfo(item.product_id);
                const hasItemFields =
                  productInfo?.order_item_fields && productInfo.order_item_fields.length > 0;
                const isExpanded = expandedItems[item.product_id] || false;

                return (
                  <Box key={index} p={3} borderWidth={1} borderColor="white" borderRadius="md" bg="black">
                    <HStack justify="space-between">
                      <VStack align="start" spacing={2} flex={1}>
                        <Text fontWeight="medium" color="white">{item.name || item.naam}</Text>

                        {/* Display variant_attributes as axis:value pairs */}
                        {item.variant_attributes &&
                          Object.keys(item.variant_attributes).length > 0 && (
                            <Text fontSize="sm" color="gray.300">
                              {formatVariantAttributes(item.variant_attributes)}
                            </Text>
                          )}

                        {/* Fallback: display legacy selectedOption if no variant_attributes */}
                        {!item.variant_attributes && item.selectedOption && (
                          <Text fontSize="sm" color="gray.300">
                            {t('cart.option_label')}: {item.selectedOption}
                          </Text>
                        )}

                        <HStack spacing={3}>
                          <NumberInput
                            size="sm"
                            maxW={20}
                            min={1}
                            value={item.quantity}
                            onChange={(value) => handleQuantityChange(item.product_id, parseInt(value) || 1)}
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

                    {/* Item Fields section for products with order_item_fields */}
                    {hasItemFields && (
                      <Box mt={3}>
                        <Button
                          size="xs"
                          variant="ghost"
                          color="orange.300"
                          onClick={() => toggleItemFields(item.product_id)}
                          rightIcon={isExpanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
                        >
                          {t('cart.item_fields_label', { defaultValue: 'Deelnemersgegevens' })}
                        </Button>
                        <Collapse in={isExpanded} animateOpacity>
                          <Box mt={2} p={2} bg="gray.900" borderRadius="md">
                            <ItemFieldsForm
                              fields={productInfo!.order_item_fields!}
                              quantity={item.quantity}
                              values={item.item_fields_data || []}
                              onChange={(values) => handleItemFieldsChange(item.product_id, values)}
                              validateOnSubmit={false}
                            />
                          </Box>
                        </Collapse>
                      </Box>
                    )}
                  </Box>
                );
              })}

              <Divider />

              <VStack spacing={2}>
                <HStack justify="space-between" width="full">
                  <Text fontSize="sm" color="white">{t('cart.item_total_label')}:</Text>
                  <Text fontSize="sm" color="white">{itemCount}</Text>
                </HStack>
                <HStack justify="space-between" width="full">
                  <Text fontSize="lg" fontWeight="bold" color="white">{t('cart.total_label')}:</Text>
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
                  {t('checkout.title')}
                </Button>
                <Button
                  variant="outline"
                  borderColor="orange.500"
                  color="orange.500"
                  _hover={{ bg: "orange.500", color: "white" }}
                  onClick={onSaveCart}
                  width="full"
                >
                  {t('cart.save')}
                </Button>
                <Button
                  variant="outline"
                  onClick={onClearCart}
                  width="full"
                >
                  {t('cart.clear')}
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

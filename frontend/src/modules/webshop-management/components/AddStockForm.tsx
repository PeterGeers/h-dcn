/**
 * AddStockForm — "Voeg voorraad toe" (Add stock) popover form.
 *
 * A form on each variant for recording inbound stock.
 * Fields: quantity (positive int), purchase_price_per_unit (€), supplier_name, reference (optional).
 * Calls addStock(productId, variantId, data) API.
 * Shows success toast and refreshes variant data.
 *
 * Validates: Requirements 9.3, 9.4
 */

import React, { useState } from 'react';
import {
  Button,
  IconButton,
  Tooltip,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Input,
  NumberInput,
  NumberInputField,
  useDisclosure,
  useToast,
  VStack,
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { addStock } from '../services/adminApi';
import { AddStockRequest } from '../types/admin.types';
import { getValidationMessage } from '../../../utils/validationMessages';

export interface AddStockFormProps {
  productId: string;
  variantId: string;
  variantLabel: string;
  onSuccess: () => void;
  isDisabled?: boolean;
}

export const AddStockForm: React.FC<AddStockFormProps> = ({
  productId,
  variantId,
  variantLabel,
  onSuccess,
  isDisabled = false,
}) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { t } = useTranslation('products');
  const toast = useToast();

  const [quantity, setQuantity] = useState<string>('');
  const [purchasePrice, setPurchasePrice] = useState<string>('');
  const [supplierName, setSupplierName] = useState('');
  const [reference, setReference] = useState('');

  const resetForm = () => {
    setQuantity('');
    setPurchasePrice('');
    setSupplierName('');
    setReference('');
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async () => {
    const qty = parseInt(quantity, 10);
    const price = parseFloat(purchasePrice);

    if (!qty || qty <= 0 || !Number.isInteger(qty) || quantity.trim() !== String(qty)) {
      toast({
        title: t('toast.stock_invalid_quantity'),
        description: t('toast.stock_invalid_quantity_desc'),
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    if (qty > 10000) {
      toast({
        title: t('toast.stock_invalid_quantity'),
        description: t('toast.stock_invalid_quantity_desc'),
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    if (!price || price <= 0) {
      toast({
        title: t('toast.stock_invalid_price'),
        description: t('toast.stock_invalid_price_desc'),
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    if (!supplierName.trim()) {
      toast({
        title: getValidationMessage(t, 'required', { field: t('toast.stock_supplier_label') }),
        description: t('toast.stock_supplier_required_desc'),
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    const data: AddStockRequest = {
      quantity: qty,
      purchase_price_per_unit: price,
      supplier_name: supplierName.trim(),
      ...(reference.trim() ? { reference: reference.trim() } : {}),
    };

    setIsSubmitting(true);
    try {
      await addStock(productId, variantId, data);
      toast({
        title: t('toast.stock_added'),
        description: t('toast.stock_added_desc', { quantity: qty, variant: variantLabel }),
        status: 'success',
        duration: 3000,
      });
      handleClose();
      onSuccess();
    } catch (err: any) {
      toast({
        title: t('toast.stock_error'),
        description: err?.response?.data?.message || err?.message || t('toast.stock_unknown_error'),
        status: 'error',
        duration: 4000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Tooltip label="Voorraad toevoegen" hasArrow>
        <IconButton
          aria-label="Voorraad toevoegen"
          icon={<AddIcon />}
          size="xs"
          colorScheme="green"
          variant="ghost"
          onClick={onOpen}
          isDisabled={isDisabled}
        />
      </Tooltip>

      <Modal isOpen={isOpen} onClose={handleClose} isCentered>
        <ModalOverlay />
        <ModalContent bg="gray.800" borderColor="orange.400" borderWidth="1px">
          <ModalHeader color="white">Voeg voorraad toe</ModalHeader>
          <ModalCloseButton color="white" />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <FormControl isRequired>
                <FormLabel fontSize="sm" color="white">Aantal</FormLabel>
                <NumberInput
                  min={1}
                  max={10000}
                  value={quantity}
                  onChange={(val) => setQuantity(val)}
                >
                  <NumberInputField placeholder="Bijv. 50" bg="gray.700" borderColor="gray.600" color="white" />
                </NumberInput>
              </FormControl>

              <FormControl isRequired>
                <FormLabel fontSize="sm" color="white">Inkoopprijs per stuk (€)</FormLabel>
                <NumberInput
                  min={0.01}
                  step={0.01}
                  precision={2}
                  value={purchasePrice}
                  onChange={(val) => setPurchasePrice(val)}
                >
                  <NumberInputField placeholder="Bijv. 8.50" bg="gray.700" borderColor="gray.600" color="white" />
                </NumberInput>
              </FormControl>

              <FormControl isRequired>
                <FormLabel fontSize="sm" color="white">Leverancier</FormLabel>
                <Input
                  value={supplierName}
                  onChange={(e) => setSupplierName(e.target.value)}
                  placeholder="Naam leverancier"
                  maxLength={100}
                  bg="gray.700" borderColor="gray.600" color="white"
                />
              </FormControl>

              <FormControl>
                <FormLabel fontSize="sm" color="white">Referentie (optioneel)</FormLabel>
                <Input
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  placeholder="Bijv. PO-2024-003"
                  maxLength={255}
                  bg="gray.700" borderColor="gray.600" color="white"
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={handleClose} isDisabled={isSubmitting}>
              Annuleren
            </Button>
            <Button
              colorScheme="orange"
              onClick={handleSubmit}
              isLoading={isSubmitting}
              loadingText="Opslaan..."
            >
              Toevoegen
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
};

export default AddStockForm;

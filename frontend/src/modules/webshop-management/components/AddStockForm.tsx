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
import { addStock } from '../services/adminApi';
import { AddStockRequest } from '../types/admin.types';

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
        title: 'Ongeldig aantal',
        description: 'Voer een geheel getal tussen 1 en 10.000 in.',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    if (qty > 10000) {
      toast({
        title: 'Ongeldig aantal',
        description: 'Voer een geheel getal tussen 1 en 10.000 in.',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    if (!price || price <= 0) {
      toast({
        title: 'Ongeldige inkoopprijs',
        description: 'Voer een bedrag groter dan €0,00 in.',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    if (!supplierName.trim()) {
      toast({
        title: 'Leverancier verplicht',
        description: 'Vul de naam van de leverancier in.',
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
        title: 'Voorraad toegevoegd',
        description: `${qty} stuks toegevoegd aan "${variantLabel}".`,
        status: 'success',
        duration: 3000,
      });
      handleClose();
      onSuccess();
    } catch (err: any) {
      toast({
        title: 'Fout bij toevoegen voorraad',
        description: err?.response?.data?.message || err?.message || 'Onbekende fout',
        status: 'error',
        duration: 4000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Button size="xs" colorScheme="orange" variant="outline" onClick={onOpen} isDisabled={isDisabled}>
        + Voorraad
      </Button>

      <Modal isOpen={isOpen} onClose={handleClose} isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Voeg voorraad toe</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <FormControl isRequired>
                <FormLabel fontSize="sm">Aantal</FormLabel>
                <NumberInput
                  min={1}
                  max={10000}
                  value={quantity}
                  onChange={(val) => setQuantity(val)}
                >
                  <NumberInputField placeholder="Bijv. 50" />
                </NumberInput>
              </FormControl>

              <FormControl isRequired>
                <FormLabel fontSize="sm">Inkoopprijs per stuk (€)</FormLabel>
                <NumberInput
                  min={0.01}
                  precision={2}
                  value={purchasePrice}
                  onChange={(val) => setPurchasePrice(val)}
                >
                  <NumberInputField placeholder="Bijv. 8.50" />
                </NumberInput>
              </FormControl>

              <FormControl isRequired>
                <FormLabel fontSize="sm">Leverancier</FormLabel>
                <Input
                  value={supplierName}
                  onChange={(e) => setSupplierName(e.target.value)}
                  placeholder="Naam leverancier"
                  maxLength={100}
                />
              </FormControl>

              <FormControl>
                <FormLabel fontSize="sm">Referentie (optioneel)</FormLabel>
                <Input
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  placeholder="Bijv. PO-2024-003"
                  maxLength={255}
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

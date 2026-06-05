/**
 * BulkVariantCreator — Modal for generating all attribute combinations.
 *
 * Triggered by a button on a product row. Calls bulkCreateVariants(productId) API.
 * Shows a confirmation dialog explaining it will generate all attribute combinations.
 * Displays success/error toast after completion.
 *
 * Validates: Requirements 3.9
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
  Text,
  useDisclosure,
  useToast,
} from '@chakra-ui/react';
import { bulkCreateVariants } from '../services/adminApi';

export interface BulkVariantCreatorProps {
  productId: string;
  productName: string;
  onSuccess: () => void;
  isDisabled?: boolean;
}

export const BulkVariantCreator: React.FC<BulkVariantCreatorProps> = ({
  productId,
  productName,
  onSuccess,
  isDisabled = false,
}) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const toast = useToast();

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await bulkCreateVariants(productId);
      toast({
        title: 'Varianten aangemaakt',
        description: `Alle attribuutcombinaties zijn gegenereerd voor "${productName}".`,
        status: 'success',
        duration: 4000,
      });
      onClose();
      onSuccess();
    } catch (err: any) {
      toast({
        title: 'Fout bij aanmaken varianten',
        description: err?.response?.data?.message || err?.message || 'Onbekende fout',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Button size="xs" colorScheme="teal" variant="outline" onClick={onOpen} isDisabled={isDisabled}>
        Bulk varianten
      </Button>

      <Modal isOpen={isOpen} onClose={onClose} isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Bulk varianten aanmaken</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Text mb={2}>
              Dit genereert automatisch alle mogelijke attribuutcombinaties
              voor het product:
            </Text>
            <Text fontWeight="bold" mb={4}>
              {productName}
            </Text>
            <Text fontSize="sm" color="gray.400">
              Bestaande varianten worden niet overschreven. Alleen nieuwe
              combinaties worden toegevoegd. Een eventuele Default_Variant
              wordt verwijderd.
            </Text>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose} isDisabled={isSubmitting}>
              Annuleren
            </Button>
            <Button
              colorScheme="teal"
              onClick={handleConfirm}
              isLoading={isSubmitting}
              loadingText="Aanmaken..."
            >
              Genereren
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
};

export default BulkVariantCreator;

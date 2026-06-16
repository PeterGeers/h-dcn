/**
 * AddVariantForm — "Voeg variant toe" modal form.
 *
 * Allows admin to add an individual variant to a product (bottom-up creation).
 * Shows one input per axis from variant_schema with existing values as autocomplete suggestions.
 * Admin can type a new value (e.g. "XS" for Maat axis).
 * Calls createVariant(productId, { variant_attributes: {...} }) on submit.
 *
 * Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
 */

import React, { useState, useCallback } from 'react';
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
  useDisclosure,
  useToast,
  VStack,
  Icon,
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import { createVariant } from '../services/adminApi';

export interface AddVariantFormProps {
  productId: string;
  variantSchema: Record<string, string[]>;
  onSuccess: () => void;
  isDisabled?: boolean;
}

export const AddVariantForm: React.FC<AddVariantFormProps> = ({
  productId,
  variantSchema,
  onSuccess,
  isDisabled = false,
}) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const toast = useToast();

  // State for each axis value, keyed by axis name
  const [axisValues, setAxisValues] = useState<Record<string, string>>({});

  const axes = Object.keys(variantSchema);

  const resetForm = useCallback(() => {
    setAxisValues({});
  }, []);

  const handleOpen = () => {
    resetForm();
    onOpen();
  };

  const handleClose = () => {
    // Don't reset on close — preserve values on error (reset only on success or explicit open)
    onClose();
  };

  const handleAxisChange = (axis: string, value: string) => {
    setAxisValues((prev) => ({ ...prev, [axis]: value }));
  };

  const handleSubmit = async () => {
    // Validate all axes are filled
    const emptyAxes = axes.filter((axis) => !axisValues[axis]?.trim());
    if (emptyAxes.length > 0) {
      toast({
        title: 'Velden verplicht',
        description: `Vul alle variant-eigenschappen in: ${emptyAxes.join(', ')}`,
        status: 'warning',
        duration: 4000,
      });
      return;
    }

    // Build variant_attributes from trimmed values
    const variantAttributes: Record<string, string> = {};
    for (const axis of axes) {
      variantAttributes[axis] = axisValues[axis].trim();
    }

    setIsSubmitting(true);
    try {
      await createVariant(productId, { variant_attributes: variantAttributes });
      toast({
        title: 'Variant aangemaakt',
        description: `Variant "${Object.values(variantAttributes).join(' / ')}" is toegevoegd.`,
        status: 'success',
        duration: 4000,
      });
      resetForm();
      onClose();
      onSuccess();
    } catch (err: any) {
      const status = err?.response?.status;
      const message = err?.response?.data?.message || err?.message || 'Onbekende fout';

      if (status === 409) {
        toast({
          title: 'Variant bestaat al',
          description: message,
          status: 'error',
          duration: 5000,
        });
      } else {
        toast({
          title: 'Fout bij aanmaken variant',
          description: message,
          status: 'error',
          duration: 5000,
        });
      }
      // Keep form open with values preserved (don't reset or close)
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Button
        size="sm"
        variant="outline"
        colorScheme="green"
        leftIcon={<AddIcon />}
        onClick={handleOpen}
        isDisabled={isDisabled}
      >
        Voeg variant toe
      </Button>

      <Modal isOpen={isOpen} onClose={handleClose} isCentered>
        <ModalOverlay />
        <ModalContent bg="gray.800" borderColor="orange.400" borderWidth="1px">
          <ModalHeader color="orange.300">Voeg variant toe</ModalHeader>
          <ModalCloseButton color="white" />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              {axes.map((axis) => {
                const existingValues = variantSchema[axis] || [];
                const datalistId = `datalist-${axis}`;

                return (
                  <FormControl key={axis} isRequired>
                    <FormLabel fontSize="sm" color="white">
                      {axis}
                    </FormLabel>
                    <Input
                      list={datalistId}
                      value={axisValues[axis] || ''}
                      onChange={(e) => handleAxisChange(axis, e.target.value)}
                      placeholder={`Kies of typ ${axis.toLowerCase()}...`}
                      bg="gray.700"
                      color="white"
                      borderColor="gray.600"
                      _hover={{ borderColor: 'orange.400' }}
                      _focus={{ borderColor: 'orange.400', boxShadow: '0 0 0 1px var(--chakra-colors-orange-400)' }}
                    />
                    <datalist id={datalistId}>
                      {existingValues.map((val) => (
                        <option key={val} value={val} />
                      ))}
                    </datalist>
                  </FormControl>
                );
              })}
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button
              variant="ghost"
              mr={3}
              onClick={handleClose}
              isDisabled={isSubmitting}
              color="white"
              _hover={{ bg: 'gray.700' }}
            >
              Annuleren
            </Button>
            <Button
              colorScheme="green"
              onClick={handleSubmit}
              isLoading={isSubmitting}
              loadingText="Opslaan..."
              leftIcon={<Icon as={AddIcon} color="green.400" />}
            >
              Opslaan
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
};

export default AddVariantForm;

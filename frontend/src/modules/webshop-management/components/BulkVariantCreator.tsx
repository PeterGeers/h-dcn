/**
 * BulkVariantCreator — Modal for generating single-axis variants in bulk.
 *
 * The admin supplies one axis (name + a list of values, one per line). When the
 * product already has an axis (derived from existing variant records) the axis
 * name is pre-filled and locked; otherwise it is free text. A live preview shows
 * how many new variants the current input would create. On submit the modal posts
 * { axis_name, values } to bulkCreateVariants and toasts the created/skipped
 * counts from the result.
 *
 * Validates: Requirements 2.3, 3.1, 3.2, 3.3, 3.6, 3.7, 8.1, 8.2, 8.3, 10.1
 */

import React, { useMemo, useState } from 'react';
import {
  Button,
  FormControl,
  FormLabel,
  Input,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Text,
  Textarea,
  VStack,
  useDisclosure,
  useToast,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { bulkCreateVariants } from '../services/adminApi';
import { AdminVariant } from '../types/admin.types';
import { deriveAxesFromVariants } from '../../../utils/variantUtils';
import { VariantRecord } from '../../webshop/types/unifiedProduct.types';
import {
  normalizeValues,
  previewCreateCount,
} from '../../products/utils/variantBulkHelpers';

export interface BulkVariantCreatorProps {
  productId: string;
  productName: string;
  existingVariants: AdminVariant[]; // to derive the locked axis + existing values
  onSuccess: () => void;
  isDisabled?: boolean;
}

export const BulkVariantCreator: React.FC<BulkVariantCreatorProps> = ({
  productId,
  productName,
  existingVariants,
  onSuccess,
  isDisabled = false,
}) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();
  const { t } = useTranslation('products');

  // Derive the axis context from existing variants. deriveAxesFromVariants reads
  // only `variant_attributes` and `active`, both present on AdminVariant, so the
  // cast through unknown is structurally safe.
  const derivedAxes = useMemo(
    () => deriveAxesFromVariants(existingVariants as unknown as VariantRecord[]),
    [existingVariants]
  );

  const axisNames = useMemo(() => Object.keys(derivedAxes), [derivedAxes]);
  const lockedAxis = axisNames.length === 1 ? axisNames[0] : null;
  // Wrapped in useMemo so the array reference is stable across renders;
  // it feeds the previewCount useMemo dependency array below.
  const existingValuesForAxis = useMemo(
    () => (lockedAxis ? derivedAxes[lockedAxis] : []),
    [lockedAxis, derivedAxes]
  );

  const [axisName, setAxisName] = useState('');
  const [rawValues, setRawValues] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // When a locked axis exists its name is fixed; otherwise use the free-text input.
  const effectiveAxisName = lockedAxis ?? axisName;

  // Split on newlines and/or commas so admins can enter values either way.
  const enteredValues = useMemo(() => rawValues.split(/[\n,]/), [rawValues]);

  const previewCount = useMemo(
    () => previewCreateCount(enteredValues, existingValuesForAxis),
    [enteredValues, existingValuesForAxis]
  );

  const normalized = useMemo(() => normalizeValues(enteredValues), [enteredValues]);
  const isAxisEmpty = effectiveAxisName.trim().length === 0;
  const isSubmitDisabled = isAxisEmpty || normalized.length === 0;

  const resetForm = () => {
    setAxisName('');
    setRawValues('');
  };

  const handleOpen = () => {
    resetForm();
    onOpen();
  };

  const handleClose = () => {
    if (isSubmitting) return;
    onClose();
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const result = await bulkCreateVariants(productId, {
        axis_name: effectiveAxisName.trim(),
        values: normalized,
      });

      toast({
        title: t('bulkCreate.toast.successTitle'),
        description: t('bulkCreate.toast.successDesc', {
          created: result.created,
          skipped: result.skipped.length,
        }),
        status: 'success',
        duration: 4000,
        isClosable: true,
      });

      resetForm();
      onClose();
      onSuccess();
    } catch (err: any) {
      const message =
        err?.response?.data?.error ||
        err?.response?.data?.message ||
        err?.message ||
        t('bulkCreate.toast.unknownError');
      toast({
        title: t('bulkCreate.toast.errorTitle'),
        description: message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      // Keep the modal open and preserve entered values on failure.
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Button
        size="xs"
        colorScheme="teal"
        variant="outline"
        onClick={handleOpen}
        isDisabled={isDisabled}
      >
        {t('bulkCreate.triggerButton')}
      </Button>

      <Modal isOpen={isOpen} onClose={handleClose} isCentered closeOnOverlayClick={false}>
        <ModalOverlay />
        <ModalContent bg="gray.800" borderColor="orange.400" borderWidth="1px">
          <ModalHeader color="orange.300">{t('bulkCreate.title')}</ModalHeader>
          <ModalCloseButton isDisabled={isSubmitting} />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <Text fontSize="sm" color="gray.400">
                {t('bulkCreate.description', { productName })}
              </Text>

              <FormControl isRequired>
                <FormLabel fontSize="sm">{t('bulkCreate.axisLabel')}</FormLabel>
                <Input
                  value={effectiveAxisName}
                  onChange={(e) => setAxisName(e.target.value)}
                  isReadOnly={lockedAxis !== null}
                  bg={lockedAxis !== null ? 'gray.700' : undefined}
                  cursor={lockedAxis !== null ? 'default' : 'text'}
                  placeholder={t('bulkCreate.axisPlaceholder')}
                  size="sm"
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel fontSize="sm">{t('bulkCreate.valuesLabel')}</FormLabel>
                <Textarea
                  value={rawValues}
                  onChange={(e) => setRawValues(e.target.value)}
                  placeholder={t('bulkCreate.valuesPlaceholder')}
                  rows={6}
                  size="sm"
                />
              </FormControl>

              <Text fontSize="sm" color="orange.300" fontWeight="medium">
                {t('bulkCreate.preview', { count: previewCount })}
              </Text>

              {isAxisEmpty && (
                <Text fontSize="xs" color="red.300">
                  {t('bulkCreate.axisEmpty')}
                </Text>
              )}
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button
              variant="ghost"
              mr={3}
              onClick={handleClose}
              isDisabled={isSubmitting}
            >
              {t('bulkCreate.cancel')}
            </Button>
            <Button
              colorScheme="orange"
              onClick={handleSubmit}
              isLoading={isSubmitting}
              loadingText={t('bulkCreate.submitting')}
              isDisabled={isSubmitDisabled}
            >
              {t('bulkCreate.submit')}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
};

export default BulkVariantCreator;

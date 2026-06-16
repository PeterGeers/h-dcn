/**
 * VariantEditModal — Modal for editing a single variant's attributes.
 *
 * Opens when a user clicks a variant value tag in VariantSchemaEditor.
 * If the variant record doesn't exist yet, auto-creates it first.
 * Allows editing: prijs (price), allow_oversell, active status.
 * Shows read-only: stock, sold_count, variant_attributes.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  NumberInput,
  NumberInputField,
  Switch,
  HStack,
  VStack,
  Text,
  Badge,
  Spinner,
  useToast,
  Box,
} from '@chakra-ui/react';
import { AdminVariant, UpdateVariantRequest } from '../../webshop-management/types/admin.types';
import { updateVariant, createVariant } from '../../webshop-management/services/adminApi';
import { AddStockForm } from '../../webshop-management/components/AddStockForm';

export interface VariantEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  productId: string;
  /** The axis name and value that was clicked, e.g. { Maat: "S" } */
  clickedAttribute: Record<string, string>;
  /** All current variant records for this product */
  variants: AdminVariant[];
  /** Callback to refresh variants after changes */
  onUpdate: () => Promise<void> | void;
  /** Parent product price (for display when variant has no override) */
  parentPrice?: number;
}

export const VariantEditModal: React.FC<VariantEditModalProps> = ({
  isOpen,
  onClose,
  productId,
  clickedAttribute,
  variants,
  onUpdate,
  parentPrice = 0,
}) => {
  const toast = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [variant, setVariant] = useState<AdminVariant | null>(null);
  const [priceValue, setPriceValue] = useState<string>('');
  const [allowOversell, setAllowOversell] = useState(false);
  const [isActive, setIsActive] = useState(true);

  // Find matching variant from the loaded list
  const findMatchingVariant = useCallback((): AdminVariant | undefined => {
    return variants.find((v) => {
      const attrs = v.variant_attributes;
      if (!attrs) return false;
      // Match: variant must contain all clicked attributes
      return Object.entries(clickedAttribute).every(([k, val]) => attrs[k] === val);
    });
  }, [variants, clickedAttribute]);

  // On open: find or create the variant
  useEffect(() => {
    if (!isOpen) return;

    const existing = findMatchingVariant();
    if (existing) {
      setVariant(existing);
      setPriceValue(existing.prijs != null ? existing.prijs.toString() : '');
      setAllowOversell(existing.allow_oversell ?? false);
      setIsActive(existing.active !== false);
    } else if (variants.length === 0) {
      // Variants haven't loaded yet — wait for them (useEffect below will re-sync)
      setVariant(null);
    } else {
      // Variants loaded but no match — auto-create
      setVariant(null);
      autoCreateVariant();
    }
  }, [isOpen, variants, clickedAttribute]); // eslint-disable-line react-hooks/exhaustive-deps

  const autoCreateVariant = async () => {
    setIsLoading(true);
    try {
      await createVariant(productId, { variant_attributes: clickedAttribute });
      toast({
        title: 'Variant aangemaakt',
        description: `Variant "${Object.values(clickedAttribute).join(' / ')}" is aangemaakt.`,
        status: 'success',
        duration: 3000,
      });
      // Refresh variants so we get the new record
      await onUpdate();
      // After refresh, the useEffect will pick up the new variant
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 409 || status === 400) {
        // Already exists or invalid request — just refresh variants and try to find it
        await onUpdate();
      } else {
        toast({
          title: 'Fout bij aanmaken variant',
          description: err?.response?.data?.message || err?.message || 'Onbekende fout',
          status: 'error',
          duration: 5000,
        });
        onClose();
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Re-sync local state when variants list updates (after auto-create)
  useEffect(() => {
    if (!isOpen) return;
    const existing = findMatchingVariant();
    if (existing && !variant) {
      setVariant(existing);
      setPriceValue(existing.prijs != null ? existing.prijs.toString() : '');
      setAllowOversell(existing.allow_oversell ?? false);
      setIsActive(existing.active !== false);
    }
  }, [variants, isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSave = async () => {
    if (!variant) return;

    const updates: UpdateVariantRequest = {};
    const newPrice = priceValue.trim() === '' ? null : parseFloat(priceValue);
    const oldPrice = variant.prijs ?? null;

    if (newPrice !== oldPrice) {
      if (priceValue.trim() !== '' && (isNaN(newPrice!) || newPrice! < 0)) {
        toast({ title: 'Ongeldige prijs', status: 'warning', duration: 3000 });
        return;
      }
      updates.prijs = newPrice;
    }

    if (allowOversell !== (variant.allow_oversell ?? false)) {
      updates.allow_oversell = allowOversell;
    }

    if (isActive !== (variant.active !== false)) {
      updates.active = isActive;
    }

    if (Object.keys(updates).length === 0) {
      onClose();
      return;
    }

    setIsSaving(true);
    try {
      await updateVariant(variant.parent_id, variant.product_id, updates);
      toast({
        title: 'Variant bijgewerkt',
        status: 'success',
        duration: 3000,
      });
      await onUpdate();
      onClose();
    } catch (err: any) {
      toast({
        title: 'Fout bij opslaan',
        description: err?.response?.data?.message || err?.message || 'Onbekende fout',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const attrLabel = Object.entries(clickedAttribute)
    .map(([k, v]) => `${k}: ${v}`)
    .join(', ');

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered>
      <ModalOverlay />
      <ModalContent bg="gray.800" borderColor="orange.400" borderWidth="1px">
        <ModalHeader color="orange.300">Variant bewerken — {attrLabel}</ModalHeader>
        <ModalCloseButton color="white" />
        <ModalBody>
          {isLoading ? (
            <VStack spacing={4} py={6}>
              <Spinner color="orange.400" size="lg" />
              <Text color="gray.300">Variant wordt aangemaakt...</Text>
            </VStack>
          ) : !variant ? (
            <Text color="gray.400">Variant niet gevonden.</Text>
          ) : (
            <VStack spacing={4} align="stretch">
              {/* Attributes (read-only) */}
              <Box>
                <Text fontSize="sm" fontWeight="bold" color="gray.300" mb={1}>
                  Attributen
                </Text>
                <HStack spacing={2} flexWrap="wrap">
                  {Object.entries(variant.variant_attributes).map(([key, value]) => (
                    <Badge key={key} colorScheme="teal" size="sm">
                      {key}: {value}
                    </Badge>
                  ))}
                </HStack>
              </Box>

              {/* Stock & sold (read-only) */}
              <HStack spacing={6}>
                <Box>
                  <Text fontSize="xs" color="gray.400">Voorraad</Text>
                  <Text color="white" fontWeight="bold">{variant.stock}</Text>
                </Box>
                <Box>
                  <Text fontSize="xs" color="gray.400">Verkocht</Text>
                  <Text color="white" fontWeight="bold">{variant.sold_count}</Text>
                </Box>
                <Box>
                  <AddStockForm
                    productId={productId}
                    variantId={variant.product_id}
                    variantLabel={Object.values(clickedAttribute).join(' / ')}
                    onSuccess={async () => { await onUpdate(); }}
                  />
                </Box>
              </HStack>

              {/* Price (editable) */}
              <FormControl>
                <FormLabel fontSize="sm" color="white">
                  Prijs (leeg = overerft €{parentPrice.toFixed(2)} van product)
                </FormLabel>
                <NumberInput
                  value={priceValue}
                  onChange={(val) => setPriceValue(val)}
                  min={0}
                  max={999999.99}
                  precision={2}
                >
                  <NumberInputField
                    placeholder={`€${parentPrice.toFixed(2)}`}
                    bg="gray.700"
                    color="white"
                    borderColor="gray.600"
                    _hover={{ borderColor: 'orange.400' }}
                  />
                </NumberInput>
              </FormControl>

              {/* Allow oversell toggle */}
              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="variant-oversell" mb="0" fontSize="sm" color="white">
                  Oversell toestaan
                </FormLabel>
                <Switch
                  id="variant-oversell"
                  isChecked={allowOversell}
                  onChange={(e) => setAllowOversell(e.target.checked)}
                  colorScheme="orange"
                />
              </FormControl>

              {/* Active toggle */}
              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="variant-active" mb="0" fontSize="sm" color="white">
                  Actief
                </FormLabel>
                <Switch
                  id="variant-active"
                  isChecked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  colorScheme="green"
                />
              </FormControl>
            </VStack>
          )}
        </ModalBody>
        <ModalFooter>
          <Button
            variant="ghost"
            mr={3}
            onClick={onClose}
            isDisabled={isSaving}
            color="white"
            _hover={{ bg: 'gray.700' }}
          >
            Annuleren
          </Button>
          <Button
            colorScheme="orange"
            onClick={handleSave}
            isLoading={isSaving}
            loadingText="Opslaan..."
            isDisabled={!variant || isLoading}
          >
            Opslaan
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default VariantEditModal;

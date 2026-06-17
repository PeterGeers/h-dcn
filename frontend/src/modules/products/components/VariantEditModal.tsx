/**
 * VariantEditModal — Modal for editing OR creating a single variant.
 *
 * Two modes:
 * - Edit mode (variant prop is populated): Pre-fills form with existing variant data.
 * - Create mode (variant prop is null): Shows axis name/value inputs with three-state logic.
 *
 * The three-state axis input logic for create mode:
 * - Zero axes (no variants exist): free text for axis name + free text for value
 * - Under MAX_AXES: dropdown of existing axes + "Nieuw..." free text option + free text value
 * - At MAX_AXES: dropdown of existing axes only (no free text option) + free text value
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
  Box,
  Input,
  Select,
  useToast,
} from '@chakra-ui/react';
import { AdminVariant, UpdateVariantRequest } from '../../webshop-management/types/admin.types';
import { updateVariant, createVariant } from '../../webshop-management/services/adminApi';
import { AddStockForm } from '../../webshop-management/components/AddStockForm';
import { determineFormMode, validateAxisInput, FormMode } from '../utils/variantFormHelpers';
import { MAX_AXES } from '../../../config/constants';

export interface VariantEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  productId: string;
  /** The variant to edit, or null for create mode */
  variant: AdminVariant | null;
  /** All current variant records for this product (used to derive axes in create mode) */
  existingVariants: AdminVariant[];
  /** Callback after successful create/edit */
  onSuccess: () => void;
  /** Parent product price (for display when variant has no override) */
  parentPrice?: number;
  /** Whether the modal interactions should be disabled */
  isDisabled?: boolean;
}

/** Sentinel value for the "Nieuw..." dropdown option */
const NEW_AXIS_OPTION = '__new__';

export const VariantEditModal: React.FC<VariantEditModalProps> = ({
  isOpen,
  onClose,
  productId,
  variant,
  existingVariants,
  onSuccess,
  parentPrice = 0,
  isDisabled = false,
}) => {
  const toast = useToast();
  const isCreateMode = variant === null;

  // --- Edit mode state ---
  const [isSaving, setIsSaving] = useState(false);
  const [priceValue, setPriceValue] = useState<string>('');
  const [allowOversell, setAllowOversell] = useState(false);
  const [isActive, setIsActive] = useState(true);

  // --- Create mode state ---
  const [axisName, setAxisName] = useState('');
  const [axisValue, setAxisValue] = useState('');
  const [selectedAxis, setSelectedAxis] = useState('');
  const [isNewAxis, setIsNewAxis] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Derive existing axes from existingVariants (used in create mode)
  const existingAxes = useMemo(() => {
    const axisMap: Record<string, Set<string>> = {};
    for (const v of existingVariants) {
      for (const [axis, value] of Object.entries(v.variant_attributes)) {
        if (!axisMap[axis]) axisMap[axis] = new Set();
        axisMap[axis].add(value);
      }
    }
    return axisMap;
  }, [existingVariants]);

  // Determine form mode for create mode
  const formMode: FormMode = useMemo(
    () => determineFormMode(existingVariants),
    [existingVariants]
  );

  const existingAxisNames = useMemo(() => Object.keys(existingAxes), [existingAxes]);

  // Reset state when modal opens/closes or mode changes
  useEffect(() => {
    if (!isOpen) return;

    if (isCreateMode) {
      // Reset create mode fields
      setAxisName('');
      setAxisValue('');
      setSelectedAxis('');
      setIsNewAxis(false);
      setIsSubmitting(false);

      // In zero-axes mode, default to free text (isNewAxis = true)
      if (formMode === 'zero-axes') {
        setIsNewAxis(true);
      }
    } else {
      // Edit mode: pre-fill from variant
      setPriceValue(variant.prijs != null ? variant.prijs.toString() : '');
      setAllowOversell(variant.allow_oversell ?? false);
      setIsActive(variant.active !== false);
      setIsSaving(false);
    }
  }, [isOpen, isCreateMode, variant, formMode]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Create mode handlers ---

  const handleAxisDropdownChange = (value: string) => {
    if (value === NEW_AXIS_OPTION) {
      setIsNewAxis(true);
      setSelectedAxis('');
      setAxisName('');
    } else {
      setIsNewAxis(false);
      setSelectedAxis(value);
      setAxisName(value);
    }
  };

  const handleCreateSubmit = async () => {
    // Determine the final axis name
    const finalAxisName = isNewAxis ? axisName : selectedAxis;

    if (!validateAxisInput(finalAxisName, axisValue)) {
      toast({
        title: 'Velden verplicht',
        description: 'Vul een as-naam en waarde in.',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setIsSubmitting(true);
    try {
      await createVariant(productId, {
        variant_attributes: { [finalAxisName.trim()]: axisValue.trim() },
      });
      toast({
        title: 'Variant aangemaakt',
        description: `Variant "${finalAxisName.trim()}: ${axisValue.trim()}" is aangemaakt.`,
        status: 'success',
        duration: 3000,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 409) {
        toast({
          title: 'Variant bestaat al',
          description: err?.response?.data?.message || 'Er bestaat al een variant met deze attributen.',
          status: 'error',
          duration: 5000,
        });
      } else {
        toast({
          title: 'Fout bij aanmaken',
          description: err?.response?.data?.message || err?.message || 'Onbekende fout',
          status: 'error',
          duration: 5000,
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Edit mode handlers ---

  const handleEditSave = async () => {
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
      onSuccess();
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

  // --- Render ---

  const renderCreateMode = () => (
    <VStack spacing={4} align="stretch">
      {/* Axis Name Input — varies by form mode */}
      <FormControl>
        <FormLabel fontSize="sm" color="white">
          As-naam
        </FormLabel>
        {formMode === 'zero-axes' ? (
          // Free text only
          <Input
            placeholder="Bijv. Maat, Kleur..."
            value={axisName}
            onChange={(e) => setAxisName(e.target.value)}
            bg="gray.700"
            color="white"
            borderColor="gray.600"
            _hover={{ borderColor: 'orange.400' }}
            _focus={{ borderColor: 'orange.400', boxShadow: '0 0 0 1px var(--chakra-colors-orange-400)' }}
            isDisabled={isDisabled}
          />
        ) : formMode === 'under-max' ? (
          // Dropdown with existing axes + "Nieuw..." option
          <VStack spacing={2} align="stretch">
            <Select
              placeholder="Kies een as..."
              value={isNewAxis ? NEW_AXIS_OPTION : selectedAxis}
              onChange={(e) => handleAxisDropdownChange(e.target.value)}
              bg="gray.700"
              color="white"
              borderColor="gray.600"
              _hover={{ borderColor: 'orange.400' }}
              isDisabled={isDisabled}
            >
              {existingAxisNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
              <option value={NEW_AXIS_OPTION}>Nieuw...</option>
            </Select>
            {isNewAxis && (
              <Input
                placeholder="Nieuwe as-naam..."
                value={axisName}
                onChange={(e) => setAxisName(e.target.value)}
                bg="gray.700"
                color="white"
                borderColor="gray.600"
                _hover={{ borderColor: 'orange.400' }}
                _focus={{ borderColor: 'orange.400', boxShadow: '0 0 0 1px var(--chakra-colors-orange-400)' }}
                isDisabled={isDisabled}
              />
            )}
          </VStack>
        ) : (
          // At MAX_AXES: dropdown only, no free text
          <Select
            placeholder="Kies een as..."
            value={selectedAxis}
            onChange={(e) => {
              setSelectedAxis(e.target.value);
              setAxisName(e.target.value);
            }}
            bg="gray.700"
            color="white"
            borderColor="gray.600"
            _hover={{ borderColor: 'orange.400' }}
            isDisabled={isDisabled}
          >
            {existingAxisNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </Select>
        )}
      </FormControl>

      {/* Value Input — always free text */}
      <FormControl>
        <FormLabel fontSize="sm" color="white">
          Waarde
        </FormLabel>
        <Input
          placeholder="Bijv. S, Rood, 42..."
          value={axisValue}
          onChange={(e) => setAxisValue(e.target.value)}
          bg="gray.700"
          color="white"
          borderColor="gray.600"
          _hover={{ borderColor: 'orange.400' }}
          _focus={{ borderColor: 'orange.400', boxShadow: '0 0 0 1px var(--chakra-colors-orange-400)' }}
          isDisabled={isDisabled}
        />
      </FormControl>

      {/* Show existing values hint when an axis is selected */}
      {!isNewAxis && selectedAxis && existingAxes[selectedAxis] && (
        <Box>
          <Text fontSize="xs" color="gray.400" mb={1}>
            Bestaande waarden voor "{selectedAxis}":
          </Text>
          <HStack spacing={1} flexWrap="wrap">
            {Array.from(existingAxes[selectedAxis]).map((val) => (
              <Badge key={val} colorScheme="teal" size="sm">
                {val}
              </Badge>
            ))}
          </HStack>
        </Box>
      )}
    </VStack>
  );

  const renderEditMode = () => {
    if (!variant) {
      return <Text color="gray.400">Variant niet gevonden.</Text>;
    }

    const attrLabel = Object.entries(variant.variant_attributes)
      .map(([k, v]) => `${k}: ${v}`)
      .join(', ');

    return (
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
              variantLabel={Object.values(variant.variant_attributes).join(' / ')}
              onSuccess={async () => { onSuccess(); }}
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
            isDisabled={isDisabled}
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
            isDisabled={isDisabled}
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
            isDisabled={isDisabled}
          />
        </FormControl>
      </VStack>
    );
  };

  const headerTitle = isCreateMode
    ? 'Variant toevoegen'
    : `Variant bewerken — ${Object.entries(variant!.variant_attributes).map(([k, v]) => `${k}: ${v}`).join(', ')}`;

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered>
      <ModalOverlay />
      <ModalContent bg="gray.800" borderColor="orange.400" borderWidth="1px">
        <ModalHeader color="orange.300">{headerTitle}</ModalHeader>
        <ModalCloseButton color="white" />
        <ModalBody>
          {isCreateMode ? renderCreateMode() : renderEditMode()}
        </ModalBody>
        <ModalFooter>
          <Button
            variant="ghost"
            mr={3}
            onClick={onClose}
            isDisabled={isSaving || isSubmitting}
            color="white"
            _hover={{ bg: 'gray.700' }}
          >
            Annuleren
          </Button>
          {isCreateMode ? (
            <Button
              colorScheme="orange"
              onClick={handleCreateSubmit}
              isLoading={isSubmitting}
              loadingText="Aanmaken..."
              isDisabled={isDisabled}
            >
              Aanmaken
            </Button>
          ) : (
            <Button
              colorScheme="orange"
              onClick={handleEditSave}
              isLoading={isSaving}
              loadingText="Opslaan..."
              isDisabled={!variant || isDisabled}
            >
              Opslaan
            </Button>
          )}
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default VariantEditModal;

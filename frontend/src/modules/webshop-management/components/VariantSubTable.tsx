/**
 * VariantSubTable — Displays variant rows in a sub-table under a product.
 *
 * Shows per variant:
 * - Attribute values (e.g., gender=male, size=XL)
 * - Stock count
 * - Sold count
 * - Allow oversell toggle (inline edit)
 * - Price (inline edit, null = inherit parent)
 *
 * Row-click opens variant detail/edit modal (managed by parent).
 * Stock addition, deactivation, and deletion actions live inside the modal.
 *
 * Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.13, 8.1, 8.4
 */

import React, { useState } from 'react';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Switch,
  Badge,
  HStack,
  Text,
  NumberInput,
  NumberInputField,
  IconButton,
  Tooltip,
  Box,
  Spinner,
  useToast,
} from '@chakra-ui/react';
import { CheckIcon, CloseIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { AdminProduct, AdminVariant } from '../types/admin.types';
import { updateVariant } from '../services/adminApi';
import { useAdminPermissions } from '../hooks/useAdminPermissions';
import { formatPriceEuro } from '../../../utils/formatPrice';

export interface VariantSubTableProps {
  product: AdminProduct;
  variants: AdminVariant[];
  /** Callback to trigger variant list re-fetch. May return a Promise for error handling. */
  onUpdate: () => Promise<void> | void;
  /** When true, shows a non-blocking loading indicator over the table. */
  isRefetching?: boolean;
  /** Callback when a variant row is clicked (opens edit modal in parent). */
  onRowClick: (variant: AdminVariant) => void;
}

export const VariantSubTable: React.FC<VariantSubTableProps> = ({
  product,
  variants,
  onUpdate,
  isRefetching = false,
  onRowClick,
}) => {
  const toast = useToast();
  const { t } = useTranslation('products');
  const { canMutate } = useAdminPermissions();
  const disabledTooltip = 'Products_CRUD vereist';
  const [editingPriceId, setEditingPriceId] = useState<string | null>(null);
  const [editPriceValue, setEditPriceValue] = useState<string>('');
  const [togglingOversellId, setTogglingOversellId] = useState<string | null>(null);
  const [internalRefetching, setInternalRefetching] = useState<boolean>(false);

  // Combined loading state: either parent signals or internal re-fetch is in progress
  const showLoadingIndicator = isRefetching || internalRefetching;

  /**
   * Wraps onUpdate() to handle async re-fetch with loading state and error handling.
   * Shows error toast on failure; retains previously displayed data (no state clearing).
   * Validates: Requirements 7.1, 7.2, 7.3, 7.4
   */
  const triggerRefetch = async () => {
    setInternalRefetching(true);
    try {
      await onUpdate();
    } catch (err: any) {
      toast({
        title: t('toast.refresh_error'),
        description: err?.message || t('toast.refresh_error_desc'),
        status: 'error',
        duration: 5000,
      });
    } finally {
      setInternalRefetching(false);
    }
  };

  const handleOversellToggle = async (variant: AdminVariant, newValue: boolean) => {
    setTogglingOversellId(variant.product_id);
    try {
      await updateVariant(variant.parent_id, variant.product_id, {
        allow_oversell: newValue,
      });
      toast({
        title: t('toast.oversell_updated'),
        description: newValue ? t('toast.oversell_enabled') : t('toast.oversell_disabled'),
        status: 'success',
        duration: 5000,
      });
      triggerRefetch();
    } catch (err: any) {
      toast({
        title: t('toast.error'),
        description: err?.message || t('toast.oversell_error'),
        status: 'error',
        duration: 5000,
      });
      // Optimistic revert: refresh list to restore previous state from server
      triggerRefetch();
    } finally {
      setTogglingOversellId(null);
    }
  };

  const startPriceEdit = (variant: AdminVariant) => {
    setEditingPriceId(variant.product_id);
    setEditPriceValue(
      variant.prijs != null ? variant.prijs.toString() : ''
    );
  };

  const cancelPriceEdit = () => {
    setEditingPriceId(null);
    setEditPriceValue('');
  };

  const validatePrice = (value: string): string | null => {
    if (value.trim() === '') return null; // empty is valid (inherit parent)
    const num = parseFloat(value);
    if (isNaN(num) || !/^-?\d*\.?\d*$/.test(value.trim())) {
      return 'Voer een geldig numeriek bedrag in';
    }
    if (num < 0) {
      return 'Prijs mag niet negatief zijn';
    }
    if (num > 999999.99) {
      return 'Prijs mag niet hoger zijn dan €999.999,99';
    }
    // Check max 2 decimal places
    const parts = value.trim().split('.');
    if (parts.length === 2 && parts[1].length > 2) {
      return 'Maximaal 2 decimalen toegestaan';
    }
    return null;
  };

  const savePriceEdit = async (variant: AdminVariant) => {
    const validationError = validatePrice(editPriceValue);
    if (validationError) {
      toast({
        title: t('toast.invalid_price'),
        description: validationError,
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    const newPrice = editPriceValue.trim() === '' ? null : parseFloat(editPriceValue);
    const previousPrice = variant.prijs;

    try {
      await updateVariant(variant.parent_id, variant.product_id, {
        prijs: newPrice,
      });
      toast({
        title: t('toast.price_updated'),
        status: 'success',
        duration: 5000,
      });
      setEditingPriceId(null);
      triggerRefetch();
    } catch (err: any) {
      toast({
        title: t('toast.error'),
        description: err?.message || t('toast.price_update_error'),
        status: 'error',
        duration: 5000,
      });
      // Revert to previous value in the input
      setEditPriceValue(previousPrice != null ? previousPrice.toString() : '');
    }
  };

  return (
    <Box position="relative">
      {/* Non-blocking loading indicator during re-fetch (Req 7.2) */}
      {showLoadingIndicator && (
        <HStack
          position="absolute"
          top={0}
          right={0}
          zIndex={1}
          bg="blackAlpha.600"
          px={2}
          py={1}
          borderRadius="md"
          spacing={2}
        >
          <Spinner size="xs" color="orange.400" />
          <Text fontSize="xs" color="gray.300">Verversen…</Text>
        </HStack>
      )}
      <Box overflowX="auto">
      <Table variant="simple" size="xs" sx={{ 'td': { borderColor: 'gray.600' }, 'th': { borderColor: 'gray.600' } }}>
      <Thead bg="gray.700">
        <Tr>
          <Th color="orange.300" fontSize="xs" borderColor="gray.600">Attributen</Th>
          <Th color="orange.300" fontSize="xs" borderColor="gray.600" isNumeric>Voorraad</Th>
          <Th color="orange.300" fontSize="xs" borderColor="gray.600" isNumeric>Verkocht</Th>
          <Th color="orange.300" fontSize="xs" borderColor="gray.600">Oversell</Th>
          <Th color="orange.300" fontSize="xs" borderColor="gray.600" isNumeric>Prijs</Th>
        </Tr>
      </Thead>
      <Tbody>
        {variants.map((variant) => (
          <Tr
            key={variant.product_id}
            opacity={variant.active === false ? 0.5 : 1}
            onClick={() => onRowClick(variant)}
            _hover={{ bg: 'gray.700', cursor: 'pointer' }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter') onRowClick(variant); }}
          >
            {/* Attribute values */}
            <Td>
              <HStack spacing={1} flexWrap="wrap">
                {Object.entries(variant.variant_attributes || {}).length === 0 ? (
                  <Badge colorScheme="gray" size="sm">Default</Badge>
                ) : (
                  Object.entries(variant.variant_attributes || {}).map(([key, value]) => (
                    <Badge key={key} colorScheme="teal" size="sm">
                      {key}: {value}
                    </Badge>
                  ))
                )}
              </HStack>
            </Td>

            {/* Stock */}
            <Td isNumeric>{variant.stock}</Td>

            {/* Sold count */}
            <Td isNumeric>{variant.sold_count}</Td>

            {/* Allow oversell toggle */}
            <Td onClick={(e) => e.stopPropagation()}>
              <Tooltip label={!canMutate ? disabledTooltip : ''} isDisabled={canMutate} hasArrow>
                <Box display="inline-block">
                  <Switch
                    size="sm"
                    isChecked={variant.allow_oversell}
                    isDisabled={!canMutate || togglingOversellId === variant.product_id}
                    onChange={(e) => handleOversellToggle(variant, e.target.checked)}
                    colorScheme="orange"
                  />
                </Box>
              </Tooltip>
            </Td>

            {/* Price (inline editable) */}
            <Td isNumeric onClick={(e) => e.stopPropagation()}>
              {editingPriceId === variant.product_id ? (
                <HStack spacing={1} justify="flex-end">
                  <NumberInput
                    size="xs"
                    maxW="80px"
                    value={editPriceValue}
                    onChange={(val) => setEditPriceValue(val)}
                    min={0}
                    max={999999.99}
                    step={0.01}
                    precision={2}
                  >
                    <NumberInputField
                      placeholder="€"
                      onKeyDown={(e) => {
                        if (e.key === 'Escape') {
                          cancelPriceEdit();
                        } else if (e.key === 'Enter') {
                          savePriceEdit(variant);
                        }
                      }}
                    />
                  </NumberInput>
                  <IconButton
                    aria-label="Opslaan"
                    icon={<CheckIcon />}
                    size="xs"
                    colorScheme="green"
                    onClick={() => savePriceEdit(variant)}
                  />
                  <IconButton
                    aria-label="Annuleren"
                    icon={<CloseIcon />}
                    size="xs"
                    variant="ghost"
                    onClick={cancelPriceEdit}
                  />
                </HStack>
              ) : (
                <Text
                  cursor={canMutate ? 'pointer' : 'default'}
                  _hover={canMutate ? { color: 'orange.300' } : undefined}
                  onClick={canMutate ? () => startPriceEdit(variant) : undefined}
                  title={canMutate ? 'Klik om prijs te bewerken' : disabledTooltip}
                >
                  {variant.prijs != null
                    ? formatPriceEuro(variant.prijs)
                    : `${formatPriceEuro(product.price)} (ouder)`}
                </Text>
              )}
            </Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
    </Box>
    </Box>
  );
};

export default VariantSubTable;

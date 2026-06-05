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
 * Supports inline editing of allow_oversell and price via updateVariant API.
 *
 * Validates: Requirements 3.1, 3.2, 3.4, 3.8, 3.13
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
  useToast,
} from '@chakra-ui/react';
import { CheckIcon, CloseIcon } from '@chakra-ui/icons';
import { AdminProduct, AdminVariant } from '../types/admin.types';
import { updateVariant } from '../services/adminApi';
import { AddStockForm } from './AddStockForm';
import { useAdminPermissions } from '../hooks/useAdminPermissions';

export interface VariantSubTableProps {
  product: AdminProduct;
  variants: AdminVariant[];
  onUpdate: () => void;
}

export const VariantSubTable: React.FC<VariantSubTableProps> = ({
  product,
  variants,
  onUpdate,
}) => {
  const toast = useToast();
  const { canMutate } = useAdminPermissions();
  const disabledTooltip = 'Products_CRUD vereist';
  const [editingPriceId, setEditingPriceId] = useState<string | null>(null);
  const [editPriceValue, setEditPriceValue] = useState<string>('');

  const handleOversellToggle = async (variant: AdminVariant, newValue: boolean) => {
    try {
      await updateVariant(variant.parent_id, variant.product_id, {
        allow_oversell: newValue,
      });
      toast({
        title: 'Bijgewerkt',
        description: `Oversell ${newValue ? 'ingeschakeld' : 'uitgeschakeld'}`,
        status: 'success',
        duration: 2000,
      });
      onUpdate();
    } catch (err: any) {
      toast({
        title: 'Fout',
        description: err?.message || 'Kon oversell niet bijwerken',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const startPriceEdit = (variant: AdminVariant) => {
    setEditingPriceId(variant.product_id);
    setEditPriceValue(
      variant.price != null ? variant.price.toString() : ''
    );
  };

  const cancelPriceEdit = () => {
    setEditingPriceId(null);
    setEditPriceValue('');
  };

  const savePriceEdit = async (variant: AdminVariant) => {
    const newPrice = editPriceValue.trim() === '' ? null : parseFloat(editPriceValue);
    if (newPrice !== null && (isNaN(newPrice) || newPrice < 0)) {
      toast({
        title: 'Ongeldige prijs',
        description: 'Voer een geldig bedrag in of laat leeg voor ouderprijs',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    try {
      await updateVariant(variant.parent_id, variant.product_id, {
        price: newPrice,
      });
      toast({
        title: 'Prijs bijgewerkt',
        status: 'success',
        duration: 2000,
      });
      setEditingPriceId(null);
      onUpdate();
    } catch (err: any) {
      toast({
        title: 'Fout',
        description: err?.message || 'Kon prijs niet bijwerken',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const formatAttributes = (attrs: Record<string, string>): string => {
    const entries = Object.entries(attrs);
    if (entries.length === 0) return 'Default';
    return entries.map(([k, v]) => `${k}: ${v}`).join(', ');
  };

  return (
    <Table variant="simple" size="xs">
      <Thead>
        <Tr>
          <Th>Attributen</Th>
          <Th isNumeric>Voorraad</Th>
          <Th isNumeric>Verkocht</Th>
          <Th>Oversell</Th>
          <Th isNumeric>Prijs</Th>
          <Th>Acties</Th>
        </Tr>
      </Thead>
      <Tbody>
        {variants.map((variant) => (
          <Tr key={variant.product_id}>
            {/* Attribute values */}
            <Td>
              <HStack spacing={1} flexWrap="wrap">
                {Object.entries(variant.variant_attributes).length === 0 ? (
                  <Badge colorScheme="gray" size="sm">Default</Badge>
                ) : (
                  Object.entries(variant.variant_attributes).map(([key, value]) => (
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
            <Td>
              <Tooltip label={!canMutate ? disabledTooltip : ''} isDisabled={canMutate} hasArrow>
                <Box display="inline-block">
                  <Switch
                    size="sm"
                    isChecked={variant.allow_oversell}
                    isDisabled={!canMutate}
                    onChange={(e) => handleOversellToggle(variant, e.target.checked)}
                    colorScheme="orange"
                  />
                </Box>
              </Tooltip>
            </Td>

            {/* Price (inline editable) */}
            <Td isNumeric>
              {editingPriceId === variant.product_id ? (
                <HStack spacing={1} justify="flex-end">
                  <NumberInput
                    size="xs"
                    maxW="80px"
                    value={editPriceValue}
                    onChange={(val) => setEditPriceValue(val)}
                    min={0}
                    precision={2}
                  >
                    <NumberInputField placeholder="€" />
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
                  {variant.price != null
                    ? `€${variant.price.toFixed(2)}`
                    : `€${product.price.toFixed(2)} (ouder)`}
                </Text>
              )}
            </Td>

            {/* Actions */}
            <Td>
              <AddStockForm
                productId={product.product_id}
                variantId={variant.product_id}
                variantLabel={`${product.name} - ${formatAttributes(variant.variant_attributes)}`}
                onSuccess={onUpdate}
                isDisabled={!canMutate}
              />
            </Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
  );
};

export default VariantSubTable;
